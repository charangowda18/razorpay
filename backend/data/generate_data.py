"""
Synthetic Payment Data Generator
Generates realistic failed and successful payment transactions for training and demo.

Design decisions:
- 70% success / 30% failure ratio (realistic for Indian payment ecosystem)
- Failure reasons weighted by real-world frequency
- Time patterns simulate real payment behavior (more transactions during business hours)
- Bank distribution matches Indian market share
"""

import uuid
import random
import sqlite3
import os
import sys
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import init_database, get_db_connection

# ============================================================
# CONFIGURATION — Realistic Indian payment ecosystem data
# ============================================================

MERCHANTS = [
    {"name": "FreshBasket Groceries", "business_type": "grocery", "email": "ops@freshbasket.in"},
    {"name": "UrbanStyle Fashion", "business_type": "fashion", "email": "payments@urbanstyle.in"},
    {"name": "TechZone Electronics", "business_type": "electronics", "email": "finance@techzone.in"},
    {"name": "QuickBite Food Delivery", "business_type": "food_delivery", "email": "support@quickbite.in"},
    {"name": "EduLearn Online", "business_type": "edtech", "email": "billing@edulearn.in"},
    {"name": "FitLife Subscription", "business_type": "health_fitness", "email": "accounts@fitlife.in"},
    {"name": "BookWorm Store", "business_type": "retail", "email": "orders@bookworm.in"},
    {"name": "CloudSoft SaaS", "business_type": "saas", "email": "billing@cloudsoft.in"},
    {"name": "TravelEasy Bookings", "business_type": "travel", "email": "payments@traveleasy.in"},
    {"name": "MediCare Pharmacy", "business_type": "healthcare", "email": "billing@medicare.in"},
]

# Failure reasons with realistic weights and retry-friendliness
FAILURE_REASONS = {
    "insufficient_funds": {"weight": 0.25, "retry_success_rate": 0.45, "code": "ERR_INSUFFICIENT_FUNDS"},
    "bank_server_down": {"weight": 0.18, "retry_success_rate": 0.72, "code": "ERR_BANK_SERVER"},
    "network_timeout": {"weight": 0.15, "retry_success_rate": 0.80, "code": "ERR_NETWORK_TIMEOUT"},
    "card_declined": {"weight": 0.12, "retry_success_rate": 0.15, "code": "ERR_CARD_DECLINED"},
    "authentication_failed": {"weight": 0.10, "retry_success_rate": 0.35, "code": "ERR_AUTH_FAILED"},
    "card_expired": {"weight": 0.07, "retry_success_rate": 0.02, "code": "ERR_CARD_EXPIRED"},
    "daily_limit_exceeded": {"weight": 0.06, "retry_success_rate": 0.55, "code": "ERR_DAILY_LIMIT"},
    "invalid_card_number": {"weight": 0.04, "retry_success_rate": 0.01, "code": "ERR_INVALID_CARD"},
    "fraud_suspected": {"weight": 0.03, "retry_success_rate": 0.05, "code": "ERR_FRAUD_SUSPECTED"},
}

PAYMENT_METHODS = {
    "upi": 0.42,        # UPI dominates in India
    "card": 0.28,       # Credit/Debit cards
    "netbanking": 0.18, # Net banking
    "wallet": 0.12,     # Digital wallets
}

BANKS = {
    "SBI": 0.22, "HDFC": 0.18, "ICICI": 0.15, "Axis": 0.10,
    "Kotak": 0.08, "PNB": 0.07, "BOB": 0.06, "Yes Bank": 0.05,
    "IndusInd": 0.05, "IDFC First": 0.04,
}

CARD_NETWORKS = ["Visa", "Mastercard", "RuPay", "Amex"]
CARD_NETWORK_WEIGHTS = [0.35, 0.30, 0.30, 0.05]

# Amount ranges by business type
AMOUNT_RANGES = {
    "grocery": (150, 5000),
    "fashion": (500, 15000),
    "electronics": (2000, 80000),
    "food_delivery": (100, 2000),
    "edtech": (500, 25000),
    "health_fitness": (300, 5000),
    "retail": (200, 3000),
    "saas": (500, 50000),
    "travel": (2000, 100000),
    "healthcare": (200, 10000),
}


def weighted_choice(options_dict):
    """Select a random item based on weights."""
    items = list(options_dict.keys())
    weights = [options_dict[k] if isinstance(options_dict[k], (int, float)) else options_dict[k]["weight"] for k in items]
    return random.choices(items, weights=weights, k=1)[0]


def generate_email():
    """Generate a random customer email."""
    providers = ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "protonmail.com"]
    names = ["rahul", "priya", "amit", "sneha", "vikram", "ananya", "rohit", "divya",
             "arjun", "meera", "karthik", "pooja", "suresh", "neha", "rajesh",
             "swati", "deepak", "kavita", "mohan", "ritu"]
    return f"{random.choice(names)}{random.randint(10, 999)}@{random.choice(providers)}"


def generate_phone():
    """Generate a random Indian phone number."""
    return f"+91{random.randint(7000000000, 9999999999)}"


def generate_transaction_time(days_back=90):
    """
    Generate a realistic transaction timestamp.
    More transactions during business hours (10 AM - 9 PM) and on weekdays.
    """
    now = datetime.now()
    day_offset = random.randint(0, days_back)
    base_date = now - timedelta(days=day_offset)

    # Weighted hour distribution — peak during 10 AM - 9 PM
    hour_weights = [
        1, 1, 0.5, 0.5, 0.5, 1,     # 12 AM - 5 AM (low)
        2, 3, 5, 7, 8, 9,             # 6 AM - 11 AM (rising)
        10, 9, 8, 7, 6, 7,            # 12 PM - 5 PM (afternoon)
        8, 9, 10, 8, 5, 3,            # 6 PM - 11 PM (evening peak then drop)
    ]
    hour = random.choices(range(24), weights=hour_weights, k=1)[0]
    minute = random.randint(0, 59)
    second = random.randint(0, 59)

    return base_date.replace(hour=hour, minute=minute, second=second)


def should_transaction_fail(payment_method, bank, hour, amount):
    """
    Determine if a transaction should fail based on realistic patterns.
    Returns (should_fail, failure_reason) or (False, None).

    IMPORTANT: Failure reasons are payment-method-aware.
    Card-specific failures (card_expired, card_declined, invalid_card_number)
    only apply to card payments. UPI/netbanking/wallet get relevant failures.
    """
    # Base failure rate: 30%
    base_failure_rate = 0.30

    # Adjust by payment method
    method_adjustment = {
        "upi": -0.05,       # UPI is more reliable
        "card": 0.02,
        "netbanking": 0.05, # Netbanking has more issues
        "wallet": -0.03,
    }

    # Adjust by bank (some banks are less reliable)
    bank_adjustment = {
        "SBI": 0.03, "PNB": 0.05, "BOB": 0.04, "Yes Bank": 0.06,
    }

    # Adjust by time (late night has more failures)
    time_adjustment = 0.08 if hour < 6 or hour > 22 else 0

    # Adjust by amount (higher amounts fail more)
    amount_adjustment = 0.05 if amount > 20000 else 0

    final_rate = (
        base_failure_rate
        + method_adjustment.get(payment_method, 0)
        + bank_adjustment.get(bank, 0)
        + time_adjustment
        + amount_adjustment
    )

    if random.random() < final_rate:
        # Payment-method-aware failure reasons
        failure_reason = _get_failure_reason_for_method(payment_method)
        return True, failure_reason
    return False, None


# Failure reasons mapped to valid payment methods
METHOD_FAILURE_REASONS = {
    "card": {
        "insufficient_funds": 0.22,
        "bank_server_down": 0.15,
        "network_timeout": 0.12,
        "card_declined": 0.18,
        "authentication_failed": 0.10,
        "card_expired": 0.10,
        "daily_limit_exceeded": 0.05,
        "invalid_card_number": 0.05,
        "fraud_suspected": 0.03,
    },
    "upi": {
        "insufficient_funds": 0.30,
        "bank_server_down": 0.25,
        "network_timeout": 0.20,
        "authentication_failed": 0.12,
        "daily_limit_exceeded": 0.08,
        "fraud_suspected": 0.05,
    },
    "netbanking": {
        "insufficient_funds": 0.22,
        "bank_server_down": 0.30,
        "network_timeout": 0.22,
        "authentication_failed": 0.15,
        "daily_limit_exceeded": 0.08,
        "fraud_suspected": 0.03,
    },
    "wallet": {
        "insufficient_funds": 0.40,
        "network_timeout": 0.25,
        "authentication_failed": 0.15,
        "daily_limit_exceeded": 0.12,
        "fraud_suspected": 0.08,
    },
}


def _get_failure_reason_for_method(payment_method):
    """Pick a failure reason that's valid for the given payment method."""
    reasons = METHOD_FAILURE_REASONS.get(payment_method, METHOD_FAILURE_REASONS["card"])
    return weighted_choice(reasons)


def determine_recovery_status(failure_reason, created_at):
    """
    For failed transactions, determine if they were eventually recovered.
    Older failures are more likely to have been retried.
    """
    days_ago = (datetime.now() - created_at).days
    base_recovery = FAILURE_REASONS[failure_reason]["retry_success_rate"]

    # Older transactions had more time to be recovered
    time_bonus = min(0.15, days_ago * 0.002)
    recovery_rate = base_recovery + time_bonus

    if random.random() < recovery_rate:
        return "recovered"
    return "failed"


def generate_data(num_transactions=1500):
    """Generate synthetic payment data and populate the database."""

    print("🔄 Initializing database...")
    init_database()

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # ---- Generate Merchants ----
        print("🏪 Generating merchants...")
        merchant_ids = []
        for merchant in MERCHANTS:
            mid = f"merch_{uuid.uuid4().hex[:12]}"
            merchant_ids.append({"id": mid, "business_type": merchant["business_type"]})
            cursor.execute(
                "INSERT OR IGNORE INTO merchants (id, name, business_type, email, monthly_volume) VALUES (?, ?, ?, ?, ?)",
                (mid, merchant["name"], merchant["business_type"], merchant["email"],
                 random.uniform(500000, 10000000))
            )
        print(f"   ✅ {len(MERCHANTS)} merchants created")

        # ---- Generate Transactions ----
        print(f"💳 Generating {num_transactions} transactions...")
        success_count = 0
        failed_count = 0
        recovered_count = 0

        for i in range(num_transactions):
            txn_id = f"txn_{uuid.uuid4().hex[:16]}"
            merchant = random.choice(merchant_ids)
            merchant_id = merchant["id"]
            business_type = merchant["business_type"]

            # Generate realistic amount based on business type
            amount_range = AMOUNT_RANGES.get(business_type, (100, 10000))
            amount = round(random.uniform(*amount_range), 2)

            payment_method = weighted_choice(PAYMENT_METHODS)
            bank = weighted_choice(BANKS)
            card_network = random.choices(CARD_NETWORKS, weights=CARD_NETWORK_WEIGHTS, k=1)[0] if payment_method == "card" else None
            created_at = generate_transaction_time(days_back=90)
            customer_email = generate_email()
            customer_phone = generate_phone()

            # Determine if the transaction fails
            should_fail, failure_reason = should_transaction_fail(
                payment_method, bank, created_at.hour, amount
            )

            if should_fail:
                # Check if it was eventually recovered
                status = determine_recovery_status(failure_reason, created_at)
                failure_code = FAILURE_REASONS[failure_reason]["code"]

                if status == "recovered":
                    recovered_count += 1
                else:
                    failed_count += 1

                retry_eligible = 1 if failure_reason not in ("card_expired", "invalid_card_number", "fraud_suspected") else 0
            else:
                status = "success"
                failure_reason = None
                failure_code = None
                retry_eligible = 0
                success_count += 1

            cursor.execute("""
                INSERT INTO transactions
                (id, merchant_id, amount, currency, status, failure_reason, failure_code,
                 payment_method, bank_name, card_network, customer_email, customer_phone,
                 retry_eligible, created_at, updated_at)
                VALUES (?, ?, ?, 'INR', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                txn_id, merchant_id, amount, status, failure_reason, failure_code,
                payment_method, bank, card_network, customer_email, customer_phone,
                retry_eligible, created_at.isoformat(), created_at.isoformat()
            ))

            # For recovered/failed transactions, generate retry attempts
            if should_fail and failure_reason not in ("card_expired", "invalid_card_number", "fraud_suspected"):
                num_retries = random.randint(1, 4)
                for attempt in range(1, num_retries + 1):
                    retry_id = f"retry_{uuid.uuid4().hex[:12]}"
                    retry_time = created_at + timedelta(
                        hours=random.randint(1, 48),
                        minutes=random.randint(0, 59)
                    )
                    retry_score = round(random.uniform(0.1, 0.95), 3)

                    # Last attempt matches the final status
                    if attempt == num_retries:
                        retry_status = "success" if status == "recovered" else "failed"
                    else:
                        retry_status = "failed"

                    cursor.execute("""
                        INSERT INTO retry_attempts
                        (id, transaction_id, attempt_number, retry_score, scheduled_time,
                         attempted_time, status, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        retry_id, txn_id, attempt, retry_score,
                        retry_time.isoformat(), retry_time.isoformat(),
                        retry_status, retry_time.isoformat()
                    ))

            # Progress indicator
            if (i + 1) % 500 == 0:
                print(f"   ... {i + 1}/{num_transactions} transactions generated")

        conn.commit()

        # ---- Summary ----
        print("\n" + "=" * 50)
        print("📊 DATA GENERATION SUMMARY")
        print("=" * 50)
        print(f"   Total transactions: {num_transactions}")
        print(f"   ✅ Successful:      {success_count} ({100*success_count/num_transactions:.1f}%)")
        print(f"   ❌ Failed:          {failed_count} ({100*failed_count/num_transactions:.1f}%)")
        print(f"   🔄 Recovered:       {recovered_count} ({100*recovered_count/num_transactions:.1f}%)")
        print(f"   📈 Recovery rate:   {100*recovered_count/(failed_count+recovered_count):.1f}% of failures recovered")

        # Revenue summary
        cursor.execute("SELECT SUM(amount) FROM transactions WHERE status = 'failed'")
        failed_revenue = cursor.fetchone()[0] or 0
        cursor.execute("SELECT SUM(amount) FROM transactions WHERE status = 'recovered'")
        recovered_revenue = cursor.fetchone()[0] or 0
        cursor.execute("SELECT SUM(amount) FROM transactions WHERE status = 'success'")
        success_revenue = cursor.fetchone()[0] or 0

        print(f"\n💰 REVENUE SUMMARY")
        print(f"   Successful revenue: ₹{success_revenue:,.2f}")
        print(f"   Failed revenue:     ₹{failed_revenue:,.2f}")
        print(f"   Recovered revenue:  ₹{recovered_revenue:,.2f}")
        print(f"   Still lost:         ₹{failed_revenue:,.2f}")
        print(f"   Recovery potential:  ₹{failed_revenue * 0.6:,.2f} (estimated)")


if __name__ == "__main__":
    generate_data(1500)
    print("\n✅ Synthetic data generation complete!")
