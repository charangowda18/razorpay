"""
Retry Prediction Model — Training Script

Trains a Random Forest classifier to predict the probability of a payment retry succeeding.

Why Random Forest?
- Interpretable: Feature importances tell us WHAT matters most
- Handles mixed feature types (categorical + numerical)
- Robust to outliers (payment amounts vary wildly)
- No feature scaling needed
- Easy to explain in interviews: "It builds many decision trees and takes a majority vote"

Features used:
- failure_reason (categorical) — strongest predictor
- payment_method (categorical) — UPI vs Card have different retry profiles
- bank_name (categorical) — some banks recover faster
- hour_of_day (numerical) — salary credits happen at specific times
- day_of_week (numerical) — weekday vs weekend patterns
- amount_bucket (categorical) — small amounts recover more easily
- previous_attempts (numerical) — diminishing returns after 3-4 retries
"""

import os
import sys
import sqlite3
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
from sklearn.preprocessing import LabelEncoder

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_db_connection


def load_training_data():
    """Load failed/recovered transactions from the database as training data."""
    with get_db_connection() as conn:
        query = """
            SELECT
                t.id,
                t.failure_reason,
                t.payment_method,
                t.bank_name,
                t.amount,
                t.status,
                t.created_at,
                COALESCE(
                    (SELECT COUNT(*) FROM retry_attempts r WHERE r.transaction_id = t.id),
                    0
                ) as retry_count
            FROM transactions t
            WHERE t.status IN ('failed', 'recovered')
            AND t.failure_reason IS NOT NULL
        """
        df = pd.read_sql_query(query, conn)

    if df.empty:
        raise ValueError("No training data found. Run generate_data.py first.")

    return df


def engineer_features(df):
    """
    Feature engineering — transform raw data into ML-ready features.

    Key decisions:
    - Use hour and day_of_week as numbers (they have natural ordering)
    - Bucket amounts into categories (reduces noise from exact amounts)
    - One-hot encode categorical features
    """
    # Parse timestamp
    df["created_at"] = pd.to_datetime(df["created_at"])
    df["hour_of_day"] = df["created_at"].dt.hour
    df["day_of_week"] = df["created_at"].dt.dayofweek  # 0=Monday, 6=Sunday
    df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)

    # Amount bucketing
    df["amount_bucket"] = pd.cut(
        df["amount"],
        bins=[0, 500, 2000, 10000, 50000, float("inf")],
        labels=["micro", "small", "medium", "large", "enterprise"]
    )

    # Target variable: 1 = recovered (retry succeeded), 0 = still failed
    df["target"] = (df["status"] == "recovered").astype(int)

    # Select feature columns
    feature_cols = [
        "failure_reason", "payment_method", "bank_name",
        "hour_of_day", "day_of_week", "is_weekend",
        "amount_bucket", "retry_count"
    ]

    return df, feature_cols


def train_model():
    """Train and save the retry prediction model."""
    print("📥 Loading training data...")
    df = load_training_data()
    print(f"   Loaded {len(df)} samples ({df['status'].value_counts().to_dict()})")

    print("🔧 Engineering features...")
    df, feature_cols = engineer_features(df)

    # One-hot encode categorical features
    categorical_cols = ["failure_reason", "payment_method", "bank_name", "amount_bucket"]
    df_encoded = pd.get_dummies(df[feature_cols], columns=categorical_cols, drop_first=False)

    X = df_encoded
    y = df["target"]

    # Split data: 80% train, 20% test
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    print(f"   Training set: {len(X_train)} samples")
    print(f"   Test set:     {len(X_test)} samples")

    # Train Random Forest
    print("🌲 Training Random Forest model...")
    model = RandomForestClassifier(
        n_estimators=100,       # 100 trees (good balance of accuracy and speed)
        max_depth=10,           # Prevent overfitting
        min_samples_split=10,   # Need at least 10 samples to split
        min_samples_leaf=5,     # Need at least 5 samples per leaf
        random_state=42,
        n_jobs=-1,              # Use all CPU cores
        class_weight="balanced" # Handle class imbalance
    )
    model.fit(X_train, y_train)

    # Evaluate
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)

    print(f"\n📊 MODEL PERFORMANCE")
    print(f"   Accuracy: {accuracy:.3f} ({accuracy*100:.1f}%)")
    print(f"\n   Classification Report:")
    print(classification_report(y_test, y_pred, target_names=["Will Fail", "Will Recover"]))

    # Feature importances (THIS is what you show in the interview!)
    importances = pd.Series(model.feature_importances_, index=X_train.columns)
    importances = importances.sort_values(ascending=False).head(15)

    print("🏆 TOP 15 FEATURE IMPORTANCES:")
    print("   (These tell us WHAT matters most for predicting retry success)")
    for feature, importance in importances.items():
        bar = "█" * int(importance * 100)
        print(f"   {feature:40s} {importance:.4f} {bar}")

    # Save model and feature columns
    model_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(model_dir, "retry_model.pkl")
    columns_path = os.path.join(model_dir, "feature_columns.pkl")

    joblib.dump(model, model_path)
    joblib.dump(list(X_train.columns), columns_path)

    print(f"\n💾 Model saved to: {model_path}")
    print(f"💾 Feature columns saved to: {columns_path}")

    return model, list(X_train.columns)


if __name__ == "__main__":
    train_model()
    print("\n✅ Model training complete!")
