import os

from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv
from openai import OpenAI
from db import get_connection
import predictor  # loads the trained model + medicine/diet CSVs

load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": ["http://localhost:5173"]}})

client = OpenAI()
MODEL = os.getenv("OPENAI_MODEL", "gpt-6-luna")

def close(cur, conn):
    if cur:
        cur.close()
    if conn:
        conn.close()


# ---------------- Health ----------------
@app.get("/api/health")
def health():
    try:
        conn = get_connection()
        conn.close()
        return jsonify({"ok": True, "database": "connected",
                        "modelLoaded": predictor.is_loaded()})
    except Exception:
        app.logger.exception("Health check failed")
        return jsonify({"ok": False, "database": "connection failed",
                        "modelLoaded": predictor.is_loaded()}), 500


# ---------------- Dashboard ----------------
@app.get("/api/dashboard")
def dashboard():
    conn = cur = None
    try:
        conn = get_connection()
        cur = conn.cursor(dictionary=True)

        cur.execute("SELECT COUNT(*) AS totalChecks FROM symptom_checks")
        checks = cur.fetchone()["totalChecks"]
        cur.execute("SELECT COUNT(*) AS medicineCount FROM medicines")
        meds = cur.fetchone()["medicineCount"]
        cur.execute("SELECT COUNT(*) AS chatCount FROM chat_messages")
        chats = cur.fetchone()["chatCount"]

        cur.execute("""
            SELECT id, symptoms AS title, demo_prediction AS detail, created_at
            FROM symptom_checks ORDER BY created_at DESC LIMIT 5
        """)
        recent = cur.fetchall()

        cur.execute("""
            SELECT DATE(created_at) AS day, COUNT(*) AS count
            FROM symptom_checks
            WHERE created_at >= DATE_SUB(CURDATE(), INTERVAL 6 DAY)
            GROUP BY DATE(created_at) ORDER BY day
        """)
        trends = cur.fetchall()

        for row in recent:
            row["created_at"] = row["created_at"].isoformat() if row["created_at"] else None
        for row in trends:
            row["day"] = row["day"].isoformat() if row["day"] else None

        return jsonify({"totalChecks": checks, "medicineCount": meds,
                        "chatCount": chats, "recent": recent, "trends": trends})
    except Exception:
        app.logger.exception("Dashboard error")
        return jsonify({"error": "Could not load dashboard; check MySQL configuration."}), 500
    finally:
        close(cur, conn)


# ---------------- Medicines ----------------
@app.get("/api/medicines")
def medicines():
    conn = cur = None
    try:
        conn = get_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT id, name, category, description, usage_note AS usageNote
            FROM medicines ORDER BY name
        """)
        return jsonify(cur.fetchall())
    except Exception:
        app.logger.exception("Loading medicines failed")
        return jsonify({"error": "Could not load medicines."}), 500
    finally:
        close(cur, conn)


# ---------------- Diet recommendations ----------------
@app.get("/api/diet-recommendations")
def diets():
    conn = cur = None
    try:
        conn = get_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT id, title, description, category
            FROM diet_recommendations ORDER BY id
        """)
        return jsonify(cur.fetchall())
    except Exception:
        app.logger.exception("Loading diet recommendations failed")
        return jsonify({"error": "Could not load diet recommendations."}), 500
    finally:
        close(cur, conn)


# ---------------- Create symptom check (ML prediction) ----------------
@app.post("/api/symptom-checks")
def create_check():
    data = request.get_json(silent=True) or {}
    symptoms = str(data.get("symptoms", "")).strip()
    duration = str(data.get("duration", "")).strip()

    if len(symptoms) < 3:
        return jsonify({"error": "Please enter your symptoms."}), 400

    if not predictor.is_loaded():
        return jsonify({"error": "Trained model not found. Run train_model.py first."}), 503

    try:
        result = predictor.predict(symptoms)
    except Exception:
        app.logger.exception("Model prediction failed")
        return jsonify({"error": "Could not generate a prediction."}), 500

    if not result["predictions"]:
        return jsonify({
            "error": "I couldn't match those symptoms. Try terms like "
                     "'itching, skin rash, high fever'."
        }), 400

    prediction = result["predictions"][0]["disease"]

    conn = cur = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO symptom_checks (symptoms, duration, demo_prediction) "
            "VALUES (%s, %s, %s)",
            (symptoms, duration or None, prediction),
        )
        conn.commit()

        return jsonify({
            "id": cur.lastrowid,
            "symptoms": symptoms,
            "prediction": prediction,
            "result": result,
            "notice": "Machine learning model output for educational "
                      "demonstration only; not a medical diagnosis.",
        }), 201
    except Exception:
        if conn:
            conn.rollback()
        app.logger.exception("Saving symptom check failed")
        return jsonify({"error": "Could not save check; verify database settings."}), 500
    finally:
        close(cur, conn)


# ---------------- Symptom check history ----------------
@app.get("/api/symptom-checks")
def checks():
    conn = cur = None
    try:
        conn = get_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT id, symptoms, duration,
                   demo_prediction AS demoPrediction, created_at AS createdAt
            FROM symptom_checks ORDER BY created_at DESC LIMIT 20
        """)
        rows = cur.fetchall()
        for row in rows:
            row["createdAt"] = row["createdAt"].isoformat() if row["createdAt"] else None
        return jsonify(rows)
    except Exception:
        app.logger.exception("Loading symptom history failed")
        return jsonify({"error": "Could not load symptom checks."}), 500
    finally:
        close(cur, conn)


# ---------------- Chat ----------------
@app.get("/api/chat")
def get_chat():
    conn = cur = None
    try:
        conn = get_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT id, role, message, created_at AS createdAt
            FROM chat_messages ORDER BY id DESC LIMIT 30
        """)
        rows = cur.fetchall()[::-1]
        for row in rows:
            row["createdAt"] = row["createdAt"].isoformat() if row["createdAt"] else None
        return jsonify(rows)
    except Exception:
        app.logger.exception("Loading chat history failed")
        return jsonify({"error": "Could not load chat."}), 500
    finally:
        close(cur, conn)


@app.post("/api/chat")
def create_chat():
    data = request.get_json(silent=True) or {}
    message = str(data.get("message", "")).strip()

    if not message:
        return jsonify({"error": "Message is required."}), 400

    conn = cur = None

    try:
        # Generate an answer using the OpenAI API
        response = client.responses.create(
            model=MODEL,
            instructions=(
                "You are a Personal Health and Wellness Assistant. "
                "Answer general questions about nutrition, foods, "
                "vitamins, and healthy habits in simple language. "
                "Explain benefits accurately and do not claim that foods "
                "cure diseases. Do not diagnose conditions or prescribe "
                "medicines. For personal medical concerns, recommend "
                "consulting a qualified healthcare professional."
            ),
            input=message
        )

        reply = response.output_text.strip()

        if not reply:
            raise ValueError("The AI returned an empty response.")

        # Save the user question and AI response in MySQL
        conn = get_connection()
        cur = conn.cursor()

        cur.execute(
            "INSERT INTO chat_messages (role, message) VALUES (%s, %s)",
            ("user", message)
        )
        user_id = cur.lastrowid

        cur.execute(
            "INSERT INTO chat_messages (role, message) VALUES (%s, %s)",
            ("assistant", reply)
        )
        assistant_id = cur.lastrowid

        conn.commit()

        return jsonify({
            "user": {
                "id": user_id,
                "role": "user",
                "message": message
            },
            "assistant": {
                "id": assistant_id,
                "role": "assistant",
                "message": reply
            }
        }), 201

    except Exception:
        if conn:
            conn.rollback()

        app.logger.exception("Chat API failed")
        return jsonify({
            "error": "Could not generate a response. Check the backend terminal."
        }), 500

    finally:
        close(cur, conn)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.getenv("FLASK_PORT", "5000")), debug=True)

