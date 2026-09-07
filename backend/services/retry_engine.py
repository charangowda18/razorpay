import os
import sys
import uuid
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import settings
from database import get_db_connection

try:
    from ml.predict import predict_retry_success
    _ml_available = True
except Exception:
    _ml_available = False

NON_RETRYABLE_FAILURES = {
    "card_expired",
    "invalid_card_number",
    "fraud_suspected",
}

ALT_PAYMENT_CANDIDATES = {
    "card_declined": "upi",
    "netbanking_unavailable": "upi",
    "authentication_failed": "upi",
    "daily_limit_exceeded": "wallet",
}

RETRY_WINDOWS = {
    "insufficient_funds": [4, 24, 72],
    "bank_server_down": [1, 3, 6],
    "network_timeout": [0.5, 1, 3],
    "card_declined": [24, 48, 96],
    "authentication_failed": [2, 12, 24],
    "daily_limit_exceeded": [24, 48],
}

def evaluate_transaction(transaction: dict) -> dict:
    """
    Evaluate a failed transaction and decide on the retry strategy.

    Args:
        transaction: dict with transaction details

    Returns:
        dict with retry decision and strategy
    """
    failure_reason = transaction.get("failure_reason", "unknown")
    retry_count = transaction.get("retry_count", 0)
    amount = transaction.get("amount", 0)

    if failure_reason in NON_RETRYABLE_FAILURES:
        return {
            "should_retry": False,
            "reason": f"Non-retryable failure: {failure_reason}",
            "recommended_action": "payment_link" if failure_reason == "card_expired" else "manual_review",
            "retry_score": 0.0,
            "confidence": "high",
            "alternative_method": None,
        }

    if retry_count >= settings.MAX_RETRY_ATTEMPTS:
        return {
            "should_retry": False,
            "reason": f"Maximum retry attempts ({settings.MAX_RETRY_ATTEMPTS}) reached",
            "recommended_action": "notification",
            "retry_score": 0.0,
            "confidence": "high",
            "alternative_method": ALT_PAYMENT_CANDIDATES.get(failure_reason),
        }

    if _ml_available:
        try:
            prediction = predict_retry_success(transaction)
            retry_score = prediction["retry_score"]
            confidence = prediction["confidence"]
            recommended_action = prediction["recommended_action"]
            optimal_retry_hour = prediction["optimal_retry_hour"]
        except Exception as e:
            print(f"⚠️  ML prediction failed: {e}, falling back to rules")
            retry_score = _rule_based_score(transaction)
            confidence = "medium"
            recommended_action = "smart_retry" if retry_score > 0.5 else "notification"
            optimal_retry_hour = 10
    else:
        retry_score = _rule_based_score(transaction)
        confidence = "medium"
        recommended_action = "smart_retry" if retry_score > 0.5 else "notification"
        optimal_retry_hour = 10

    retry_windows = RETRY_WINDOWS.get(failure_reason, [2, 12, 24])
    next_window_index = min(retry_count, len(retry_windows) - 1)
    hours_until_retry = retry_windows[next_window_index]

    now = datetime.now()
    optimal_retry_time = now + timedelta(hours=hours_until_retry)

    if hours_until_retry >= 4:
        optimal_retry_time = optimal_retry_time.replace(
            hour=optimal_retry_hour, minute=0, second=0
        )
        if optimal_retry_time < now:
            optimal_retry_time += timedelta(days=1)

    should_retry = retry_score >= settings.MEDIUM_CONFIDENCE_THRESHOLD

    return {
        "should_retry": should_retry,
        "retry_score": retry_score,
        "confidence": confidence,
        "recommended_action": recommended_action,
        "optimal_retry_time": optimal_retry_time.isoformat(),
        "hours_until_retry": hours_until_retry,
        "attempt_number": retry_count + 1,
        "failure_reason": failure_reason,
        "alternative_method": ALT_PAYMENT_CANDIDATES.get(failure_reason),
        "reason": _get_human_readable_reason(retry_score, failure_reason, confidence),
    }

def schedule_retry(transaction_id: str, evaluation: dict) -> dict:
    """
    Schedule a retry attempt in the database based on the evaluation.

    Args:
        transaction_id: The transaction to retry
        evaluation: Result from evaluate_transaction()

    Returns:
        dict with the scheduled retry details
    """
    if not evaluation.get("should_retry"):
        return {"scheduled": False, "reason": evaluation.get("reason", "Not eligible for retry")}

    retry_id = f"retry_{uuid.uuid4().hex[:12]}"

    with get_db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO retry_attempts
            (id, transaction_id, attempt_number, retry_score, scheduled_time, status, created_at)
            VALUES (?, ?, ?, ?, ?, 'scheduled', ?)
        """, (
            retry_id,
            transaction_id,
            evaluation["attempt_number"],
            evaluation["retry_score"],
            evaluation["optimal_retry_time"],
            datetime.now().isoformat()
        ))

        cursor.execute("""
            UPDATE transactions
            SET retry_score = ?, optimal_retry_time = ?, updated_at = ?
            WHERE id = ?
        """, (
            evaluation["retry_score"],
            evaluation["optimal_retry_time"],
            datetime.now().isoformat(),
            transaction_id
        ))

        conn.commit()

    return {
        "scheduled": True,
        "retry_id": retry_id,
        "transaction_id": transaction_id,
        "scheduled_time": evaluation["optimal_retry_time"],
        "retry_score": evaluation["retry_score"],
        "attempt_number": evaluation["attempt_number"],
    }

def simulate_retry_execution(transaction_id: str, retry_id: str) -> dict:
    """
    Simulate executing a retry (for demo purposes).
    In production, this would call the actual payment gateway.

    Uses the retry_score to probabilistically determine success.
    """
    import random

    with get_db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT retry_score FROM retry_attempts WHERE id = ?", (retry_id,))
        retry = cursor.fetchone()
        if not retry:
            return {"success": False, "error": "Retry not found"}

        retry_score = retry["retry_score"]

        success = random.random() < retry_score

        cursor.execute("""
            UPDATE retry_attempts
            SET status = ?, attempted_time = ?
            WHERE id = ?
        """, (
            "success" if success else "failed",
            datetime.now().isoformat(),
            retry_id
        ))

        if success:
            cursor.execute("""
                UPDATE transactions
                SET status = 'recovered', updated_at = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), transaction_id))

        conn.commit()

    return {
        "success": success,
        "transaction_id": transaction_id,
        "retry_id": retry_id,
        "new_status": "recovered" if success else "failed",
        "retry_score": retry_score,
    }

def _rule_based_score(transaction: dict) -> float:
    """Fallback scoring when ML model is not available."""
    failure_reason = transaction.get("failure_reason", "unknown")
    retry_count = transaction.get("retry_count", 0)

    base_scores = {
        "network_timeout": 0.80,
        "bank_server_down": 0.72,
        "daily_limit_exceeded": 0.55,
        "insufficient_funds": 0.45,
        "authentication_failed": 0.35,
        "card_declined": 0.15,
        "card_expired": 0.02,
        "invalid_card_number": 0.01,
        "fraud_suspected": 0.05,
    }

    score = base_scores.get(failure_reason, 0.30)

    score *= (0.85 ** retry_count)

    return round(min(max(score, 0.0), 1.0), 4)

def _get_human_readable_reason(score: float, failure_reason: str, confidence: str) -> str:
    """Generate a human-readable explanation of the retry decision."""
    if score >= 0.7:
        return f"High chance of recovery ({score:.0%}). {failure_reason.replace('_', ' ').title()} failures often resolve with a well-timed retry."
    elif score >= 0.4:
        return f"Moderate recovery chance ({score:.0%}). Consider notifying the customer and suggesting an alternative payment method."
    else:
        return f"Low recovery chance ({score:.0%}). This {failure_reason.replace('_', ' ')} failure is unlikely to resolve with retries alone."
