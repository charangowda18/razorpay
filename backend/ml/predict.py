import os
import joblib
import pandas as pd
import numpy as np
from datetime import datetime

_model = None
_feature_columns = None

def _load_model():
    """Lazy-load the trained model and feature columns."""
    global _model, _feature_columns

    if _model is not None:
        return

    model_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(model_dir, "retry_model.pkl")
    columns_path = os.path.join(model_dir, "feature_columns.pkl")

    if not os.path.exists(model_path):
        raise FileNotFoundError(
            f"Model not found at {model_path}. Run train_model.py first."
        )

    _model = joblib.load(model_path)
    _feature_columns = joblib.load(columns_path)

def predict_retry_success(transaction: dict) -> dict:
    """
    Predict the probability of a retry succeeding for a given transaction.

    Args:
        transaction: dict with keys:
            - failure_reason (str)
            - payment_method (str)
            - bank_name (str)
            - amount (float)
            - created_at (str, ISO format)
            - retry_count (int, optional)

    Returns:
        dict with:
            - retry_score (float): Probability of retry success (0.0 - 1.0)
            - confidence (str): "high", "medium", or "low"
            - recommended_action (str): What to do next
            - optimal_retry_hour (int): Best hour to retry
            - feature_contributions (dict): Top factors influencing this prediction
    """
    _load_model()

    created_at = datetime.fromisoformat(transaction.get("created_at", datetime.now().isoformat()))

    features = {
        "hour_of_day": created_at.hour,
        "day_of_week": created_at.weekday(),
        "is_weekend": 1 if created_at.weekday() >= 5 else 0,
        "retry_count": transaction.get("retry_count", 0),
    }

    failure_reason = transaction.get("failure_reason", "unknown")
    payment_method = transaction.get("payment_method", "card")
    bank_name = transaction.get("bank_name", "SBI")

    amount = transaction.get("amount", 1000)
    if amount <= 500:
        amount_bucket = "micro"
    elif amount <= 2000:
        amount_bucket = "small"
    elif amount <= 10000:
        amount_bucket = "medium"
    elif amount <= 50000:
        amount_bucket = "large"
    else:
        amount_bucket = "enterprise"

    row = {}
    for col in _feature_columns:
        if col in features:
            row[col] = features[col]
        elif col == f"failure_reason_{failure_reason}":
            row[col] = 1
        elif col == f"payment_method_{payment_method}":
            row[col] = 1
        elif col == f"bank_name_{bank_name}":
            row[col] = 1
        elif col == f"amount_bucket_{amount_bucket}":
            row[col] = 1
        elif col.startswith(("failure_reason_", "payment_method_", "bank_name_", "amount_bucket_")):
            row[col] = 0
        else:
            row[col] = 0

    df = pd.DataFrame([row], columns=_feature_columns)

    proba = _model.predict_proba(df)[0]
    ml_score = float(proba[1])

    domain_scores = {
        "network_timeout": 0.88,
        "bank_server_down": 0.82,
        "daily_limit_exceeded": 0.58,
        "insufficient_funds": 0.50,
        "authentication_failed": 0.35,
        "card_declined": 0.18,
        "card_expired": 0.02,
        "invalid_card_number": 0.01,
        "fraud_suspected": 0.03,
    }
    domain_score = domain_scores.get(failure_reason, 0.30)

    retry_count = transaction.get("retry_count", 0)
    domain_score *= (0.85 ** retry_count)

    retry_score = round(0.3 * ml_score + 0.7 * domain_score, 4)

    if retry_score >= 0.7:
        confidence = "high"
        recommended_action = "smart_retry"
    elif retry_score >= 0.4:
        confidence = "medium"
        recommended_action = "notification"
    else:
        confidence = "low"
        recommended_action = "manual_review"

    if failure_reason in ("card_expired", "invalid_card_number", "fraud_suspected"):
        confidence = "low"
        recommended_action = "payment_link" if failure_reason == "card_expired" else "manual_review"

    optimal_hours = {
        "insufficient_funds": 10,
        "bank_server_down": 14,
        "network_timeout": 11,
        "daily_limit_exceeded": 9,
        "authentication_failed": 12,
    }
    optimal_retry_hour = optimal_hours.get(failure_reason, 10)

    feature_importances = dict(zip(_feature_columns, _model.feature_importances_))
    active_features = {k: v for k, v in feature_importances.items() if row.get(k, 0) != 0 or k in features}
    top_contributions = dict(sorted(active_features.items(), key=lambda x: x[1], reverse=True)[:5])

    return {
        "retry_score": retry_score,
        "confidence": confidence,
        "recommended_action": recommended_action,
        "optimal_retry_hour": optimal_retry_hour,
        "feature_contributions": top_contributions,
    }

def batch_predict(transactions: list) -> list:
    """Predict retry success for multiple transactions at once."""
    _load_model()
    if not transactions:
        return []

    rows = []
    for txn in transactions:
        created_at = datetime.fromisoformat(txn.get("created_at", datetime.now().isoformat()))
        features = {
            "hour_of_day": created_at.hour,
            "day_of_week": created_at.weekday(),
            "is_weekend": 1 if created_at.weekday() >= 5 else 0,
            "retry_count": txn.get("retry_count", 0),
        }
        
        failure_reason = txn.get("failure_reason", "unknown")
        payment_method = txn.get("payment_method", "card")
        bank_name = txn.get("bank_name", "SBI")
        
        amount = txn.get("amount", 1000)
        if amount <= 500:
            amount_bucket = "micro"
        elif amount <= 2000:
            amount_bucket = "small"
        elif amount <= 10000:
            amount_bucket = "medium"
        elif amount <= 50000:
            amount_bucket = "large"
        else:
            amount_bucket = "enterprise"

        row = {}
        for col in _feature_columns:
            if col in features:
                row[col] = features[col]
            elif col == f"failure_reason_{failure_reason}":
                row[col] = 1
            elif col == f"payment_method_{payment_method}":
                row[col] = 1
            elif col == f"bank_name_{bank_name}":
                row[col] = 1
            elif col == f"amount_bucket_{amount_bucket}":
                row[col] = 1
            else:
                row[col] = 0
        rows.append(row)

    df = pd.DataFrame(rows, columns=_feature_columns)
    probas = _model.predict_proba(df)
    
    results = []
    for i, txn in enumerate(transactions):
        ml_score = float(probas[i][1])
        failure_reason = txn.get("failure_reason", "unknown")
        retry_count = txn.get("retry_count", 0)

        domain_scores = {
            "network_timeout": 0.88,
            "bank_server_down": 0.82,
            "daily_limit_exceeded": 0.58,
            "insufficient_funds": 0.50,
            "authentication_failed": 0.35,
            "card_declined": 0.18,
            "card_expired": 0.02,
            "invalid_card_number": 0.01,
            "fraud_suspected": 0.03,
        }
        domain_score = domain_scores.get(failure_reason, 0.30)
        domain_score *= (0.85 ** retry_count)

        retry_score = round(0.3 * ml_score + 0.7 * domain_score, 4)

        if retry_score >= 0.7:
            confidence = "high"
            recommended_action = "smart_retry"
        elif retry_score >= 0.4:
            confidence = "medium"
            recommended_action = "notification"
        else:
            confidence = "low"
            recommended_action = "manual_review"

        if failure_reason in ("card_expired", "invalid_card_number", "fraud_suspected"):
            confidence = "low"
            recommended_action = "payment_link" if failure_reason == "card_expired" else "manual_review"

        optimal_hours = {
            "insufficient_funds": 10,
            "bank_server_down": 14,
            "network_timeout": 11,
            "daily_limit_exceeded": 9,
            "authentication_failed": 12,
        }
        optimal_retry_hour = optimal_hours.get(failure_reason, 10)

        results.append({
            "retry_score": retry_score,
            "confidence": confidence,
            "recommended_action": recommended_action,
            "optimal_retry_hour": optimal_retry_hour,
        })
    return results

def get_model_info() -> dict:
    """Return model metadata for the dashboard."""
    _load_model()

    importances = dict(zip(_feature_columns, _model.feature_importances_))
    top_features = dict(sorted(importances.items(), key=lambda x: x[1], reverse=True)[:10])

    return {
        "model_type": "Random Forest",
        "n_estimators": _model.n_estimators,
        "max_depth": _model.max_depth,
        "feature_count": len(_feature_columns),
        "top_features": top_features,
    }
