import os
import sys
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import settings

try:
    import google.generativeai as genai

    if settings.GEMINI_API_KEY:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        _gemini_model = genai.GenerativeModel(settings.GEMINI_MODEL)
        _gemini_available = True
    else:
        _gemini_available = False
        _gemini_model = None
except Exception as e:
    print(f"⚠️ Gemini Initialization Error: {e}")
    _gemini_available = False
    _gemini_model = None

def _call_gemini(prompt: str) -> str:
    """
    Call Gemini API with error handling and fallback.
    Returns the text response or a fallback message if the API is unavailable.
    """
    if not _gemini_available:
        return _generate_fallback_response(prompt)

    try:
        response = _gemini_model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"⚠️  Gemini API error: {e}")
        return _generate_fallback_response(prompt)

def _generate_fallback_response(prompt: str) -> str:
    """Generate a basic rule-based response when Gemini is unavailable."""
    return json.dumps({
        "summary": "AI analysis is temporarily unavailable. Using rule-based fallback.",
        "recommendations": [
            "Review failure patterns in the dashboard",
            "Focus on high-value failed transactions first",
            "Schedule retries during business hours for best success rates",
            "Consider sending payment update links for expired card failures"
        ],
        "note": "Connect Gemini API key for detailed AI-powered insights."
    })

def analyze_failure_patterns(transactions_data: list) -> dict:
    """
    Analyze a batch of failed transactions and identify patterns.

    Args:
        transactions_data: List of dicts with transaction details

    Returns:
        dict with analysis results
    """
    if not transactions_data:
        return {"summary": "No failed transactions to analyze.", "patterns": [], "recommendations": []}

    total = len(transactions_data)
    failure_counts = {}
    bank_counts = {}
    method_counts = {}
    total_amount = 0

    for txn in transactions_data:
        reason = txn.get("failure_reason", "unknown")
        bank = txn.get("bank_name", "unknown")
        method = txn.get("payment_method", "unknown")
        amount = txn.get("amount", 0)

        failure_counts[reason] = failure_counts.get(reason, 0) + 1
        bank_counts[bank] = bank_counts.get(bank, 0) + 1
        method_counts[method] = method_counts.get(method, 0) + 1
        total_amount += amount

    prompt = f"""You are an AI payment analytics expert for an Indian payment gateway (like Razorpay).
Analyze the following payment failure data and provide actionable insights.

FAILURE DATA SUMMARY:
- Total failed transactions: {total}
- Total amount at risk: ₹{total_amount:,.2f}

Failure Reasons:
{json.dumps(failure_counts, indent=2)}

Banks Involved:
{json.dumps(bank_counts, indent=2)}

Payment Methods:
{json.dumps(method_counts, indent=2)}

Provide your analysis in the following JSON format (respond ONLY with valid JSON, no markdown):
{{
    "summary": "A 2-3 sentence executive summary of the failure patterns",
    "patterns": [
        {{
            "pattern": "Description of the pattern found",
            "severity": "high/medium/low",
            "affected_transactions": <number>,
            "potential_recovery": "estimated recovery amount"
        }}
    ],
    "recommendations": [
        "Actionable recommendation 1",
        "Actionable recommendation 2",
        "Actionable recommendation 3"
    ],
    "risk_score": <1-10 integer>,
    "estimated_recoverable_percentage": <0-100>
}}"""

    response = _call_gemini(prompt)

    try:
        result = json.loads(response)
    except json.JSONDecodeError:
        if "```json" in response:
            json_str = response.split("```json")[1].split("```")[0].strip()
            try:
                result = json.loads(json_str)
            except json.JSONDecodeError:
                result = {"summary": response, "patterns": [], "recommendations": []}
        elif "```" in response:
            json_str = response.split("```")[1].split("```")[0].strip()
            try:
                result = json.loads(json_str)
            except json.JSONDecodeError:
                result = {"summary": response, "patterns": [], "recommendations": []}
        else:
            result = {"summary": response, "patterns": [], "recommendations": []}

    return result

def generate_recovery_strategy(transaction: dict) -> dict:
    """
    Generate a personalized recovery strategy for a single failed transaction.

    Args:
        transaction: dict with transaction details

    Returns:
        dict with recovery strategy
    """
    prompt = f"""You are an AI payment recovery specialist for an Indian payment gateway.
A merchant has a failed payment that needs recovery. Generate a recovery strategy.

FAILED TRANSACTION DETAILS:
- Amount: ₹{transaction.get('amount', 0):,.2f}
- Payment Method: {transaction.get('payment_method', 'unknown')}
- Bank: {transaction.get('bank_name', 'unknown')}
- Failure Reason: {transaction.get('failure_reason', 'unknown')}
- Failure Code: {transaction.get('failure_code', 'unknown')}
- Customer Email: {transaction.get('customer_email', 'N/A')}
- Time of Failure: {transaction.get('created_at', 'unknown')}

Provide your strategy in the following JSON format (respond ONLY with valid JSON, no markdown):
{{
    "strategy_summary": "Brief summary of the recommended recovery approach",
    "primary_action": "smart_retry / notification / alt_payment / payment_link / manual_review",
    "steps": [
        {{
            "step": 1,
            "action": "Description of what to do",
            "timing": "When to do it",
            "expected_success_rate": "estimated percentage"
        }}
    ],
    "customer_message": "A personalized, friendly message to send to the customer (if applicable)",
    "alternative_payment_suggestion": "Suggest an alternative payment method",
    "urgency": "high / medium / low",
    "reasoning": "Why this strategy was chosen based on the failure reason"
}}"""

    response = _call_gemini(prompt)

    try:
        result = json.loads(response)
    except json.JSONDecodeError:
        if "```json" in response:
            json_str = response.split("```json")[1].split("```")[0].strip()
            try:
                result = json.loads(json_str)
            except json.JSONDecodeError:
                result = {"strategy_summary": response, "primary_action": "manual_review", "steps": []}
        elif "```" in response:
            json_str = response.split("```")[1].split("```")[0].strip()
            try:
                result = json.loads(json_str)
            except json.JSONDecodeError:
                result = {"strategy_summary": response, "primary_action": "manual_review", "steps": []}
        else:
            result = {"strategy_summary": response, "primary_action": "manual_review", "steps": []}

    return result

def generate_merchant_summary(merchant_data: dict) -> dict:
    """
    Generate an overall health summary for a merchant's payment performance.

    Args:
        merchant_data: dict with merchant stats

    Returns:
        dict with merchant health summary
    """
    prompt = f"""You are an AI payment analytics advisor for an Indian payment gateway.
Generate a concise health summary for this merchant's payment performance.

MERCHANT DATA:
- Merchant: {merchant_data.get('name', 'Unknown')}
- Business Type: {merchant_data.get('business_type', 'Unknown')}
- Total Transactions: {merchant_data.get('total_transactions', 0)}
- Success Rate: {merchant_data.get('success_rate', 0):.1f}%
- Total Revenue: ₹{merchant_data.get('total_revenue', 0):,.2f}
- Failed Amount: ₹{merchant_data.get('failed_amount', 0):,.2f}
- Recovered Amount: ₹{merchant_data.get('recovered_amount', 0):,.2f}
- Top Failure Reason: {merchant_data.get('top_failure_reason', 'unknown')}
- Most Problematic Bank: {merchant_data.get('problematic_bank', 'unknown')}

Provide your summary in the following JSON format (respond ONLY with valid JSON, no markdown):
{{
    "health_score": <1-100>,
    "health_status": "excellent / good / needs_attention / critical",
    "summary": "2-3 sentence health summary",
    "key_metrics": [
        {{"metric": "name", "value": "value", "trend": "up/down/stable"}}
    ],
    "top_recommendations": [
        "Recommendation 1",
        "Recommendation 2",
        "Recommendation 3"
    ],
    "revenue_opportunity": "How much additional revenue could be recovered with optimization"
}}"""

    response = _call_gemini(prompt)

    try:
        result = json.loads(response)
    except json.JSONDecodeError:
        if "```json" in response:
            json_str = response.split("```json")[1].split("```")[0].strip()
            try:
                result = json.loads(json_str)
            except json.JSONDecodeError:
                result = {"summary": response, "health_score": 50, "health_status": "needs_attention"}
        elif "```" in response:
            json_str = response.split("```")[1].split("```")[0].strip()
            try:
                result = json.loads(json_str)
            except json.JSONDecodeError:
                result = {"summary": response, "health_score": 50, "health_status": "needs_attention"}
        else:
            result = {"summary": response, "health_score": 50, "health_status": "needs_attention"}

    return result

def generate_trend_alert(trend_data: dict) -> dict:
    """
    Generate an AI-powered alert about unusual trends in payment failures.
    """
    prompt = f"""You are an AI monitoring system for a payment gateway.
Analyze this trend data and generate an alert if something unusual is happening.

TREND DATA:
{json.dumps(trend_data, indent=2)}

Respond in JSON format (respond ONLY with valid JSON, no markdown):
{{
    "alert_title": "Brief alert title",
    "alert_severity": "info / warning / critical",
    "description": "What's happening and why it matters",
    "root_cause_hypothesis": "Possible explanation for the trend",
    "recommended_actions": ["Action 1", "Action 2"],
    "affected_revenue": "Estimated revenue impact"
}}"""

    response = _call_gemini(prompt)

    try:
        result = json.loads(response)
    except json.JSONDecodeError:
        if "```json" in response:
            json_str = response.split("```json")[1].split("```")[0].strip()
            try:
                result = json.loads(json_str)
            except json.JSONDecodeError:
                result = {"alert_title": "Trend Analysis", "description": response}
        elif "```" in response:
            json_str = response.split("```")[1].split("```")[0].strip()
            try:
                result = json.loads(json_str)
            except json.JSONDecodeError:
                result = {"alert_title": "Trend Analysis", "description": response}
        else:
            result = {"alert_title": "Trend Analysis", "description": response}

    return result

def is_available() -> bool:
    """Check if the Gemini API is configured and available."""
    return _gemini_available
