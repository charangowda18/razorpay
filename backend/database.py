"""
Database setup and connection management.
Uses SQLite for zero-config simplicity.
"""

import sqlite3
import os
from contextlib import contextmanager

DATABASE_PATH = os.getenv("DATABASE_PATH", "revenue_recovery.db")


def get_db_path():
    """Get the absolute path to the database file."""
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), DATABASE_PATH)


@contextmanager
def get_db_connection():
    """Context manager for database connections with auto-commit and cleanup."""
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row  # Return rows as dictionaries
    conn.execute("PRAGMA journal_mode=WAL")  # Better concurrent read performance
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_database():
    """Initialize the database schema. Safe to call multiple times (uses IF NOT EXISTS)."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Merchants table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS merchants (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                business_type TEXT NOT NULL,
                email TEXT,
                monthly_volume REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Transactions table (core of the system)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id TEXT PRIMARY KEY,
                merchant_id TEXT NOT NULL,
                amount REAL NOT NULL,
                currency TEXT DEFAULT 'INR',
                status TEXT NOT NULL CHECK(status IN ('success', 'failed', 'pending', 'recovered', 'abandoned')),
                failure_reason TEXT,
                failure_code TEXT,
                payment_method TEXT NOT NULL CHECK(payment_method IN ('card', 'upi', 'netbanking', 'wallet')),
                bank_name TEXT,
                card_network TEXT,
                customer_email TEXT,
                customer_phone TEXT,
                retry_eligible INTEGER DEFAULT 1,
                retry_score REAL,
                optimal_retry_time TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (merchant_id) REFERENCES merchants(id)
            )
        """)

        # Retry attempts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS retry_attempts (
                id TEXT PRIMARY KEY,
                transaction_id TEXT NOT NULL,
                attempt_number INTEGER NOT NULL,
                retry_score REAL,
                scheduled_time TIMESTAMP,
                attempted_time TIMESTAMP,
                status TEXT NOT NULL CHECK(status IN ('scheduled', 'attempted', 'success', 'failed', 'cancelled')),
                failure_reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (transaction_id) REFERENCES transactions(id)
            )
        """)

        # Recovery actions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS recovery_actions (
                id TEXT PRIMARY KEY,
                transaction_id TEXT NOT NULL,
                merchant_id TEXT NOT NULL,
                action_type TEXT NOT NULL CHECK(action_type IN ('smart_retry', 'notification', 'alt_payment', 'manual_review', 'payment_link')),
                ai_recommendation TEXT,
                notification_message TEXT,
                status TEXT NOT NULL CHECK(status IN ('pending', 'in_progress', 'completed', 'failed', 'skipped')),
                result TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (transaction_id) REFERENCES transactions(id),
                FOREIGN KEY (merchant_id) REFERENCES merchants(id)
            )
        """)

        # AI insights table (stores LLM-generated analysis)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ai_insights (
                id TEXT PRIMARY KEY,
                merchant_id TEXT,
                insight_type TEXT NOT NULL CHECK(insight_type IN ('failure_analysis', 'trend_alert', 'recovery_strategy', 'merchant_summary')),
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                severity TEXT DEFAULT 'info' CHECK(severity IN ('info', 'warning', 'critical')),
                is_read INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (merchant_id) REFERENCES merchants(id)
            )
        """)

        # Create indexes for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_merchant ON transactions(merchant_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_status ON transactions(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_created ON transactions(created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_retry_attempts_txn ON retry_attempts(transaction_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_recovery_actions_txn ON recovery_actions(transaction_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ai_insights_merchant ON ai_insights(merchant_id)")

        conn.commit()
        print("✅ Database initialized successfully.")


if __name__ == "__main__":
    init_database()
    print(f"Database created at: {get_db_path()}")
