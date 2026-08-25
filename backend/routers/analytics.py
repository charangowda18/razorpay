"""
Analytics Router — Dashboard data endpoints.
"""

from fastapi import APIRouter, Query
from typing import Optional
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.recovery_engine import get_dashboard_stats, get_merchants_list

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


@router.get("/dashboard")
def dashboard_stats():
    """
    Get all dashboard statistics in a single call.
    Returns overview metrics, failure breakdowns, bank stats, and trends.
    """
    return get_dashboard_stats()


@router.get("/merchants")
def merchants_list():
    """
    Get all merchants with their payment performance metrics.
    """
    return get_merchants_list()


@router.get("/model-info")
def model_info():
    """
    Get ML model metadata (type, features, importances).
    Useful for the 'AI Model' section of the dashboard.
    """
    try:
        from ml.predict import get_model_info
        return get_model_info()
    except Exception as e:
        return {
            "model_type": "Not trained yet",
            "error": str(e),
            "hint": "Run train_model.py to train the retry prediction model."
        }
