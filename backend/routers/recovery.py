from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.recovery_engine import (
    evaluate_and_score_transaction,
    trigger_recovery,
    execute_retry,
    batch_evaluate,
    get_ai_insights,
)

router = APIRouter(prefix="/api/recovery", tags=["Recovery"])

_cache = {}
CACHE_TTL = 30

@router.get("/evaluate/{transaction_id}")
def evaluate_transaction_endpoint(transaction_id: str):
    """
    Evaluate a failed transaction using the AI retry scoring model.
    Returns the retry score, confidence, and recommended action.
    """
    result = evaluate_and_score_transaction(transaction_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result

@router.post("/trigger/{transaction_id}")
def trigger_recovery_endpoint(transaction_id: str):
    """
    Trigger the full recovery flow for a transaction:
    1. AI evaluation
    2. Smart retry scheduling
    3. LLM recovery strategy generation
    """
    result = trigger_recovery(transaction_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result

@router.post("/execute-retry/{transaction_id}/{retry_id}")
def execute_retry_endpoint(transaction_id: str, retry_id: str):
    """
    Execute a scheduled retry attempt (simulated for demo).
    """
    return execute_retry(transaction_id, retry_id)

@router.get("/opportunities")
def get_recovery_opportunities(limit: int = Query(20, ge=1, le=100)):
    """
    Get the top recovery opportunities ranked by AI retry score.
    These are the failed transactions most likely to be recovered.
    """
    cache_key = f"opportunities_{limit}"
    now = time.time()
    if cache_key in _cache and (now - _cache[cache_key]["time"]) < CACHE_TTL:
        return _cache[cache_key]["data"]
    data = batch_evaluate(limit=limit)
    _cache[cache_key] = {"data": data, "time": now}
    return data

@router.get("/insights")
def get_insights(merchant_id: Optional[str] = None):
    """
    Get AI-generated insights about payment failure patterns.
    Uses Gemini LLM to analyze failures and provide recommendations.
    """
    return get_ai_insights(merchant_id=merchant_id)
