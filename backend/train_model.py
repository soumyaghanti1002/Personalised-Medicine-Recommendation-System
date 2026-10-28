"""Train a RandomForest on the Kaggle Medicine Recommendation dataset.

Put the CSV files in backend/data/ :
  Training.csv, medications.csv, diets.csv, precautions_df.csv, description.csv
Run:  python train_model.py
"""
import json
import os

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
MODEL_DIR = os.path.join(os.path.dirname(__file__), "model")
os.makedirs(MODEL_DIR, exist_ok=True)

df = pd.read_csv(os.path.join(DATA_DIR, "Training.csv"))
df = df.loc[:, ~df.columns.str.startswith("Unnamed")]  # drop junk index columns
df = df.drop_duplicates()

symptom_cols = [c for c in df.columns if c != "prognosis"]
X = df[symptom_cols].values
le = LabelEncoder()
y = le.fit_transform(df["prognosis"])

# stratify only if every disease has at least 2 unique rows left after de-duplication
can_stratify = pd.Series(y).value_counts().min() >= 2
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y if can_stratify else None
)

clf = RandomForestClassifier(n_estimators=300, random_state=42, n_jobs=-1)
clf.fit(X_train, y_train)

pred = clf.predict(X_test)
print("Test accuracy:", round(accuracy_score(y_test, pred), 4))
print(classification_report(y_test, pred, target_names=le.classes_, zero_division=0))

# retrain on everything for the saved model
clf.fit(X, y)

joblib.dump(clf, os.path.join(MODEL_DIR, "rf_model.joblib"))
joblib.dump(le, os.path.join(MODEL_DIR, "label_encoder.joblib"))
with open(os.path.join(MODEL_DIR, "symptoms.json"), "w") as f:
    json.dump(symptom_cols, f)

print("Saved model to", MODEL_DIR)
