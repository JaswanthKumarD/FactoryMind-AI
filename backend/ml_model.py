"""Machine-learning utilities used by FactoryMind.

The demo creates a small historical-style dataset so the project can run without
IoT hardware. In a real factory, this dataset can be replaced by MES/ERP and
maintenance records.
"""

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import accuracy_score, mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split

BASE_DIR = Path(__file__).resolve().parent
MODEL_DIR = BASE_DIR / "models"
MODEL_DIR.mkdir(exist_ok=True)

FEATURES = [
    "machine_age_years",
    "load_percent",
    "temperature_c",
    "vibration_mm_s",
    "hours_since_maintenance",
    "batch_size",
    "operator_experience_years",
    "tool_wear_percent",
    "material_hardness",
]


def create_demo_dataset(rows=2500, seed=42):
    """Create realistic-looking training data for the local demo."""
    rng = np.random.default_rng(seed)

    machine_age = rng.uniform(0.5, 15, rows)
    load = rng.uniform(30, 100, rows)
    temperature = rng.normal(65, 8, rows) + load * 0.08
    vibration = rng.uniform(0.5, 6.5, rows)
    maintenance_hours = rng.uniform(5, 900, rows)
    batch_size = rng.integers(50, 1000, rows)
    operator_experience = rng.uniform(0.5, 15, rows)
    tool_wear = rng.uniform(0, 100, rows)
    hardness = rng.uniform(120, 260, rows)

    # Cycle time is intentionally influenced by several factory conditions.
    cycle_time = (
        4.5
        + 0.07 * machine_age
        + 0.035 * load
        + 0.18 * vibration
        + 0.004 * maintenance_hours
        + 0.0018 * tool_wear
        + 0.004 * hardness
        + 0.0008 * batch_size
        - 0.025 * operator_experience
        + 0.0015 * (load * vibration)
        + rng.normal(0, 1.8, rows)
    )
    cycle_time = np.maximum(cycle_time, 2)

    # Convert machine stress into a probability and then into a failure label.
    stress_score = (
        -5.8
        + 0.17 * machine_age
        + 0.045 * load
        + 0.52 * vibration
        + 0.0038 * maintenance_hours
        + 0.035 * tool_wear
        + 0.012 * np.maximum(temperature - 70, 0)
    )
    failure_probability = 1 / (1 + np.exp(-stress_score))
    failure = rng.binomial(1, failure_probability)

    features = pd.DataFrame(
        {
            "machine_age_years": machine_age,
            "load_percent": load,
            "temperature_c": temperature,
            "vibration_mm_s": vibration,
            "hours_since_maintenance": maintenance_hours,
            "batch_size": batch_size,
            "operator_experience_years": operator_experience,
            "tool_wear_percent": tool_wear,
            "material_hardness": hardness,
        }
    )
    return features, cycle_time, failure


def train_models():
    """Train both models and save them locally."""
    features, cycle_time, failure = create_demo_dataset()

    x_train, x_test, cycle_train, cycle_test = train_test_split(
        features, cycle_time, test_size=0.2, random_state=42
    )
    cycle_model = RandomForestRegressor(
        n_estimators=220, max_depth=12, random_state=42, n_jobs=-1
    )
    cycle_model.fit(x_train, cycle_train)
    cycle_predictions = cycle_model.predict(x_test)

    x_train, x_test, failure_train, failure_test = train_test_split(
        features, failure, test_size=0.2, random_state=42, stratify=failure
    )
    failure_model = RandomForestClassifier(
        n_estimators=220,
        max_depth=12,
        random_state=42,
        n_jobs=-1,
        class_weight="balanced",
    )
    failure_model.fit(x_train, failure_train)
    failure_predictions = failure_model.predict(x_test)

    joblib.dump(cycle_model, MODEL_DIR / "cycle_time_model.joblib")
    joblib.dump(failure_model, MODEL_DIR / "failure_risk_model.joblib")

    metrics = {
        "cycle_mae_minutes": round(float(mean_absolute_error(cycle_test, cycle_predictions)), 2),
        "cycle_r2": round(float(r2_score(cycle_test, cycle_predictions)), 3),
        "failure_accuracy": round(float(accuracy_score(failure_test, failure_predictions)) * 100, 1),
        "training_rows": len(features),
        "features": FEATURES,
    }
    (MODEL_DIR / "metrics.json").write_text(json.dumps(metrics, indent=2))
    return metrics


def ensure_models():
    """Train the models once if this is the first run."""
    metrics_file = MODEL_DIR / "metrics.json"
    if metrics_file.exists():
        return json.loads(metrics_file.read_text())
    return train_models()


def predict(values):
    """Return cycle-time and failure-risk predictions for one machine state."""
    ensure_models()
    cycle_model = joblib.load(MODEL_DIR / "cycle_time_model.joblib")
    failure_model = joblib.load(MODEL_DIR / "failure_risk_model.joblib")

    row = pd.DataFrame([values], columns=FEATURES)
    predicted_cycle = float(cycle_model.predict(row)[0])
    failure_probability = float(failure_model.predict_proba(row)[0, 1])

    if failure_probability >= 0.65:
        risk_level = "HIGH"
    elif failure_probability >= 0.35:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    return {
        "predicted_cycle_time_minutes": round(predicted_cycle, 2),
        "failure_probability": round(failure_probability * 100, 2),
        "risk_level": risk_level,
        "model": "Random Forest",
        "features_used": FEATURES,
    }
