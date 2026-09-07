from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from typing import Optional
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.recovery_engine import get_failed_transactions

router = APIRouter(prefix="/api/transactions", tags=["Transactions"])

@router.get("/failed")
def list_failed_transactions(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    failure_reason: Optional[str] = None,
    bank_name: Optional[str] = None,
    payment_method: Optional[str] = None,
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
):
    """
    Get a paginated list of failed/recovered transactions.
    Supports filtering by failure_reason, bank_name, and payment_method.
    """
    return get_failed_transactions(
        limit=limit,
        offset=offset,
        failure_reason=failure_reason,
        bank_name=bank_name,
        payment_method=payment_method,
        sort_by=sort_by,
        sort_order=sort_order,
    )

@router.get("/{transaction_id}")
def get_transaction(transaction_id: str):
    """Get a single transaction by ID with retry history."""
    from database import get_db_connection

    with get_db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM transactions WHERE id = ?", (transaction_id,))
        txn = cursor.fetchone()
        if not txn:
            raise HTTPException(status_code=404, detail="Transaction not found")

        cursor.execute(
            "SELECT * FROM retry_attempts WHERE transaction_id = ? ORDER BY attempt_number",
            (transaction_id,)
        )
        retries = [dict(row) for row in cursor.fetchall()]

        cursor.execute(
            "SELECT * FROM recovery_actions WHERE transaction_id = ? ORDER BY created_at DESC",
            (transaction_id,)
        )
        actions = [dict(row) for row in cursor.fetchall()]

    return {
        "transaction": dict(txn),
        "retry_history": retries,
        "recovery_actions": actions,
    }
