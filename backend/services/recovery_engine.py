import os
import sys
import uuid
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_db_connection
from services.retry_engine import evaluate_transaction, schedule_retry, simulate_retry_execution
from services.ai_agent import (
    analyze_failure_patterns,
    generate_recovery_strategy,
    generate_merchant_summary,
    generate_trend_alert,
    is_available as is_ai_available,
)

def get_dashboard_stats() -> dict:
    """
    Get aggregated statistics for the main dashboard.
    Returns all the numbers needed for the overview cards and charts.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success_count,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_count,
                SUM(CASE WHEN status = 'recovered' THEN 1 ELSE 0 END) as recovered_count,
                SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending_count,
                SUM(amount) as total_amount,
                SUM(CASE WHEN status = 'success' THEN amount ELSE 0 END) as success_amount,
                SUM(CASE WHEN status = 'failed' THEN amount ELSE 0 END) as failed_amount,
                SUM(CASE WHEN status = 'recovered' THEN amount ELSE 0 END) as recovered_amount
            FROM transactions
        """)
        stats = dict(cursor.fetchone())

        cursor.execute("""
            SELECT failure_reason, COUNT(*) as count, SUM(amount) as total_amount
            FROM transactions
            WHERE status IN ('failed', 'recovered')
            AND failure_reason IS NOT NULL
            GROUP BY failure_reason
            ORDER BY count DESC
        """)
        failure_breakdown = [dict(row) for row in cursor.fetchall()]

        cursor.execute("""
            SELECT
                bank_name,
                COUNT(*) as total,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                SUM(CASE WHEN status = 'recovered' THEN 1 ELSE 0 END) as recovered,
                ROUND(100.0 * SUM(CASE WHEN status IN ('failed', 'recovered') THEN 1 ELSE 0 END) / COUNT(*), 1) as failure_rate
            FROM transactions
            GROUP BY bank_name
            ORDER BY failure_rate DESC
        """)
        bank_stats = [dict(row) for row in cursor.fetchall()]

        cursor.execute("""
            SELECT
                payment_method,
                COUNT(*) as total,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                SUM(CASE WHEN status = 'recovered' THEN 1 ELSE 0 END) as recovered,
                ROUND(100.0 * SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) / COUNT(*), 1) as success_rate
            FROM transactions
            GROUP BY payment_method
            ORDER BY total DESC
        """)
        method_stats = [dict(row) for row in cursor.fetchall()]

        cursor.execute("""
            SELECT
                DATE(created_at) as date,
                COUNT(*) as total,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                SUM(CASE WHEN status = 'recovered' THEN 1 ELSE 0 END) as recovered,
                SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success,
                SUM(CASE WHEN status = 'failed' THEN amount ELSE 0 END) as failed_amount,
                SUM(CASE WHEN status = 'recovered' THEN amount ELSE 0 END) as recovered_amount
            FROM transactions
            WHERE created_at >= DATE('now', '-30 days')
            GROUP BY DATE(created_at)
            ORDER BY date
        """)
        daily_trend = [dict(row) for row in cursor.fetchall()]

        cursor.execute("""
            SELECT
                CAST(strftime('%H', created_at) AS INTEGER) as hour,
                COUNT(*) as total,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                SUM(CASE WHEN status = 'recovered' THEN 1 ELSE 0 END) as recovered
            FROM transactions
            GROUP BY hour
            ORDER BY hour
        """)
        hourly_pattern = [dict(row) for row in cursor.fetchall()]

        total_failures = (stats["failed_count"] or 0) + (stats["recovered_count"] or 0)
        recovery_rate = round(
            100 * (stats["recovered_count"] or 0) / total_failures, 1
        ) if total_failures > 0 else 0

        return {
            "overview": {
                "total_transactions": stats["total"],
                "success_count": stats["success_count"],
                "failed_count": stats["failed_count"],
                "recovered_count": stats["recovered_count"],
                "pending_count": stats["pending_count"],
                "total_amount": round(stats["total_amount"] or 0, 2),
                "success_amount": round(stats["success_amount"] or 0, 2),
                "failed_amount": round(stats["failed_amount"] or 0, 2),
                "recovered_amount": round(stats["recovered_amount"] or 0, 2),
                "recovery_rate": recovery_rate,
                "potential_recovery": round((stats["failed_amount"] or 0) * 0.6, 2),
            },
            "failure_breakdown": failure_breakdown,
            "bank_stats": bank_stats,
            "method_stats": method_stats,
            "daily_trend": daily_trend,
            "hourly_pattern": hourly_pattern,
        }

def get_failed_transactions(
    limit: int = 50,
    offset: int = 0,
    failure_reason: str = None,
    bank_name: str = None,
    payment_method: str = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
) -> dict:
    """Get failed transactions with optional filters."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        where_clauses = ["status IN ('failed', 'recovered')"]
        params = []

        if failure_reason:
            where_clauses.append("failure_reason = ?")
            params.append(failure_reason)
        if bank_name:
            where_clauses.append("bank_name = ?")
            params.append(bank_name)
        if payment_method:
            where_clauses.append("payment_method = ?")
            params.append(payment_method)

        where_str = " AND ".join(where_clauses)

        allowed_sorts = {"created_at", "amount", "retry_score", "failure_reason", "status"}
        if sort_by not in allowed_sorts:
            sort_by = "created_at"
        sort_order = "DESC" if sort_order.lower() == "desc" else "ASC"

        cursor.execute(f"SELECT COUNT(*) FROM transactions WHERE {where_str}", params)
        total = cursor.fetchone()[0]

        cursor.execute(f"""
            SELECT t.*,
                   (SELECT COUNT(*) FROM retry_attempts r WHERE r.transaction_id = t.id) as retry_count
            FROM transactions t
            WHERE {where_str}
            ORDER BY {sort_by} {sort_order}
            LIMIT ? OFFSET ?
        """, params + [limit, offset])

        transactions = [dict(row) for row in cursor.fetchall()]

    return {
        "transactions": transactions,
        "total": total,
        "limit": limit,
        "offset": offset,
    }

def evaluate_and_score_transaction(transaction_id: str) -> dict:
    """
    Evaluate a specific transaction and return the AI-powered retry recommendation.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT t.*,
                   (SELECT COUNT(*) FROM retry_attempts r WHERE r.transaction_id = t.id) as retry_count
            FROM transactions t
            WHERE t.id = ?
        """, (transaction_id,))
        row = cursor.fetchone()

        if not row:
            return {"error": f"Transaction {transaction_id} not found"}

        transaction = dict(row)

    evaluation = evaluate_transaction(transaction)
    return {
        "transaction_id": transaction_id,
        "transaction": transaction,
        "evaluation": evaluation,
    }

def trigger_recovery(transaction_id: str) -> dict:
    """
    Trigger the full recovery flow for a transaction:
    1. Evaluate with ML model
    2. Schedule retry if recommended
    3. Generate AI recovery strategy
    """
    eval_result = evaluate_and_score_transaction(transaction_id)
    if "error" in eval_result:
        return eval_result

    transaction = eval_result["transaction"]
    evaluation = eval_result["evaluation"]

    retry_result = None
    if evaluation.get("should_retry"):
        retry_result = schedule_retry(transaction_id, evaluation)

    ai_strategy = None
    if is_ai_available():
        try:
            ai_strategy = generate_recovery_strategy(transaction)
        except Exception as e:
            ai_strategy = {"error": str(e)}

    action_id = f"action_{uuid.uuid4().hex[:12]}"
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO recovery_actions
            (id, transaction_id, merchant_id, action_type, ai_recommendation, status, created_at)
            VALUES (?, ?, ?, ?, ?, 'pending', ?)
        """, (
            action_id,
            transaction_id,
            transaction["merchant_id"],
            evaluation.get("recommended_action", "manual_review"),
            str(ai_strategy) if ai_strategy else None,
            datetime.now().isoformat()
        ))
        conn.commit()

    return {
        "transaction_id": transaction_id,
        "evaluation": evaluation,
        "retry_scheduled": retry_result,
        "ai_strategy": ai_strategy,
        "action_id": action_id,
    }

def execute_retry(transaction_id: str, retry_id: str) -> dict:
    """Execute a scheduled retry (simulation)."""
    return simulate_retry_execution(transaction_id, retry_id)

def batch_evaluate(limit: int = 20) -> dict:
    """
    Evaluate multiple failed transactions and return ranked recommendations.
    Useful for the dashboard to show "top recovery opportunities."
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()

        fetch_limit = limit * 3
        cursor.execute("""
            SELECT t.*,
                   (SELECT COUNT(*) FROM retry_attempts r WHERE r.transaction_id = t.id) as retry_count
            FROM transactions t
            WHERE t.status = 'failed'
            AND t.retry_eligible = 1
            ORDER BY t.amount DESC
            LIMIT ?
        """, (fetch_limit,))

        transactions = [dict(row) for row in cursor.fetchall()]

    from ml.predict import batch_predict
    predictions = batch_predict(transactions)

    results = []
    for i, txn in enumerate(transactions):
        pred = predictions[i]
        retry_score = pred["retry_score"]
        
        failure_reason = txn["failure_reason"]
        if retry_score >= 0.7:
            reason = f"High chance of recovery ({retry_score:.0%}). {failure_reason.replace('_', ' ').title()} failures often resolve with a well-timed retry."
        elif retry_score >= 0.4:
            reason = f"Moderate recovery chance ({retry_score:.0%}). Consider notifying the customer and suggesting an alternative payment method."
        else:
            reason = f"Low recovery chance ({retry_score:.0%}). This {failure_reason.replace('_', ' ')} failure is unlikely to resolve with retries alone."

        results.append({
            "transaction_id": txn["id"],
            "amount": txn["amount"],
            "failure_reason": failure_reason,
            "bank_name": txn["bank_name"],
            "payment_method": txn["payment_method"],
            "created_at": txn["created_at"],
            "retry_score": retry_score,
            "expected_recovery_value": round(txn["amount"] * retry_score, 2),
            "confidence": pred["confidence"],
            "recommended_action": pred["recommended_action"],
            "reason": reason,
        })

    results.sort(key=lambda x: x["expected_recovery_value"], reverse=True)

    results = results[:limit]

    total_recoverable = sum(r["expected_recovery_value"] for r in results)

    return {
        "opportunities": results,
        "total_evaluated": len(results),
        "total_recoverable_amount": round(total_recoverable, 2),
    }

def get_ai_insights(merchant_id: str = None) -> dict:
    """
    Get AI-generated insights about payment failures.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()

        if merchant_id:
            cursor.execute("""
                SELECT * FROM transactions
                WHERE status = 'failed' AND merchant_id = ?
                ORDER BY created_at DESC LIMIT 100
            """, (merchant_id,))
        else:
            cursor.execute("""
                SELECT * FROM transactions
                WHERE status = 'failed'
                ORDER BY created_at DESC LIMIT 100
            """)

        transactions = [dict(row) for row in cursor.fetchall()]

    if not transactions:
        return {"insights": "No failed transactions found for analysis."}

    analysis = analyze_failure_patterns(transactions)

    insight_id = f"insight_{uuid.uuid4().hex[:12]}"
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO ai_insights
            (id, merchant_id, insight_type, title, content, severity, created_at)
            VALUES (?, ?, 'failure_analysis', ?, ?, ?, ?)
        """, (
            insight_id,
            merchant_id,
            analysis.get("summary", "Payment Failure Analysis")[:200],
            str(analysis),
            "warning" if analysis.get("risk_score", 5) >= 7 else "info",
            datetime.now().isoformat()
        ))
        conn.commit()

    return {
        "insight_id": insight_id,
        "analysis": analysis,
        "ai_available": is_ai_available(),
        "transactions_analyzed": len(transactions),
    }

def get_merchants_list() -> list:
    """Get all merchants with their performance stats."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                m.id,
                m.name,
                m.business_type,
                m.email,
                COUNT(t.id) as total_transactions,
                SUM(CASE WHEN t.status = 'success' THEN 1 ELSE 0 END) as success_count,
                SUM(CASE WHEN t.status = 'failed' THEN 1 ELSE 0 END) as failed_count,
                SUM(CASE WHEN t.status = 'recovered' THEN 1 ELSE 0 END) as recovered_count,
                SUM(t.amount) as total_revenue,
                SUM(CASE WHEN t.status = 'failed' THEN t.amount ELSE 0 END) as failed_amount,
                SUM(CASE WHEN t.status = 'recovered' THEN t.amount ELSE 0 END) as recovered_amount
            FROM merchants m
            LEFT JOIN transactions t ON m.id = t.merchant_id
            GROUP BY m.id
            ORDER BY total_revenue DESC
        """)

        return [dict(row) for row in cursor.fetchall()]
