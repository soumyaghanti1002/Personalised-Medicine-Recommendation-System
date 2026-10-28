"""Prediction helper for the Flask app.

Loads the trained RandomForest (from train_model.py) and the lookup CSVs,
turns free-text symptoms into the model's feature vector, and returns the
top predicted diseases together with medications, diets and precautions.
"""
import ast
import difflib
import json
import logging
import os
import re

import joblib
import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE, "data")
MODEL_DIR = os.path.join(BASE, "model")

_model = None
_le = None
SYMPTOMS = []
SYM_INDEX = {}
_lookups = {}
_loaded = False


def _read(name):
    df = pd.read_csv(os.path.join(DATA_DIR, name))
    df = df.loc[:, ~df.columns.str.startswith("Unnamed")]
    df.columns = [c.strip() for c in df.columns]
    return df


def _load():
    global _model, _le, SYMPTOMS, SYM_INDEX, _lookups, _loaded
    try:
        _model = joblib.load(os.path.join(MODEL_DIR, "rf_model.joblib"))
        _le = joblib.load(os.path.join(MODEL_DIR, "label_encoder.joblib"))
        with open(os.path.join(MODEL_DIR, "symptoms.json")) as f:
            SYMPTOMS = json.load(f)
        SYM_INDEX = {s: i for i, s in enumerate(SYMPTOMS)}
        _lookups = {
            "desc": _read("description.csv"),
            "med": _read("medications.csv"),
            "diet": _read("diets.csv"),
            "prec": _read("precautions_df.csv"),
        }
        _loaded = True
        log.info("ML model and lookup tables loaded (%d symptoms).", len(SYMPTOMS))
    except Exception:
        _loaded = False
        log.exception("Could not load model/data. Run train_model.py and check backend/data/.")


_load()


def is_loaded():
    return _loaded


def _words(text):
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).split()


def match_symptoms(text):
    """Map free text ("skin rash, fever and itching") to model feature names."""
    feature_phrase = {f: " ".join(_words(f)) for f in SYMPTOMS}
    feature_words = {f: set(_words(f)) for f in SYMPTOMS}

    phrases = [p.strip() for p in re.split(r"[,;\n]+|\band\b", text.lower()) if p.strip()]
    matched, unmatched = set(), []

    for ph in phrases:
        words = _words(ph)
        if not words:
            continue
        norm = " ".join(words)

        hits = {f for f, p in feature_phrase.items() if p == norm}          # exact
        if not hits:                                                       # "fever" -> high_fever, mild_fever
            hits = {f for f, ws in feature_words.items() if set(words) <= ws}
            if len(hits) > 4:                                              # too vague, e.g. just "pain"
                hits = set()
        if not hits:                                                       # typos
            close = difflib.get_close_matches(norm, list(feature_phrase.values()), n=1, cutoff=0.8)
            if close:
                hits = {f for f, p in feature_phrase.items() if p == close[0]}

        if hits:
            matched |= hits
        else:
            unmatched.append(ph)

    return sorted(matched), unmatched


def _parse_list(value):
    try:
        out = ast.literal_eval(str(value))
        return [str(v) for v in out] if isinstance(out, (list, tuple)) else [str(out)]
    except (ValueError, SyntaxError):
        return [str(value)]


def _info(disease):
    d = _lookups["desc"]
    m = _lookups["med"]
    di = _lookups["diet"]
    p = _lookups["prec"]

    d = d[d["Disease"] == disease]
    m = m[m["Disease"] == disease]
    di = di[di["Disease"] == disease]
    p = p[p["Disease"] == disease]

    precautions = []
    if not p.empty:
        precautions = [str(v) for k, v in p.iloc[0].items()
                       if k.startswith("Precaution") and pd.notna(v)]
    return {
        "description": d.iloc[0]["Description"] if not d.empty else "",
        "medications": _parse_list(m.iloc[0]["Medication"]) if not m.empty else [],
        "diets": _parse_list(di.iloc[0]["Diet"]) if not di.empty else [],
        "precautions": precautions,
    }


def predict(text, top_n=3):
    if not _loaded:
        raise RuntimeError("Model not loaded")

    matched, unmatched = match_symptoms(text)
    if not matched:
        return {"matched": [], "unmatched": unmatched, "predictions": []}

    x = np.zeros((1, len(SYMPTOMS)))
    for f in matched:
        x[0, SYM_INDEX[f]] = 1

    proba = _model.predict_proba(x)[0]
    predictions = []
    for idx in np.argsort(proba)[::-1][:top_n]:
        disease = _le.inverse_transform([idx])[0]
        predictions.append({
            "disease": disease,
            "confidence": round(float(proba[idx]) * 100, 1),
            **_info(disease),
        })

    return {
        "matched": [m.replace("_", " ") for m in matched],
        "unmatched": unmatched,
        "predictions": predictions,
    }
