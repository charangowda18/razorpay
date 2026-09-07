from fastapi import APIRouter, Query
from typing import Optional
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.recovery_engine import get_dashboard_stats, get_merchants_list

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])

_cache = {}
CACHE_TTL = 30

def _get_cached(key, fetch_fn):
    """Return cached data if fresh, otherwise fetch and cache."""
    now = time.time()
    if key in _cache and (now - _cache[key]["time"]) < CACHE_TTL:
        return _cache[key]["data"]
    data = fetch_fn()
    _cache[key] = {"data": data, "time": now}
    return data

@router.get("/dashboard")
def dashboard_stats():
    """
    Get all dashboard statistics in a single call.
    Returns overview metrics, failure breakdowns, bank stats, and trends.
    """
    return _get_cached("dashboard", get_dashboard_stats)

@router.get("/merchants")
def merchants_list():
    """
    Get all merchants with their payment performance metrics.
    """
    return _get_cached("merchants", get_merchants_list)

@router.get("/model-info")
def model_info():
    """
    Get ML model metadata (type, features, importances).
    Useful for the 'AI Model' section of the dashboard.
    """
    try:
        from ml.predict import get_model_info
        return _get_cached("model_info", get_model_info)
    except Exception as e:
        return {
            "model_type": "Not trained yet",
            "error": str(e),
            "hint": "Run train_model.py to train the retry prediction model."
        }
