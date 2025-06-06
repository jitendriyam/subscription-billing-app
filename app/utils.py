import logging
import random
from datetime import date, datetime, timedelta

from dateutil.relativedelta import relativedelta
from passlib.context import CryptContext

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def calculate_next_billing_date(current_date: date, months: int = 1) -> date:
    """Calculates the next billing date, typically one month from current."""
    return current_date + relativedelta(months=months)


def calculate_due_date(issue_date: date, days: int = 15) -> date:
    """Calculates due date, typically 15 days from issue date."""
    return issue_date + timedelta(days=days)


def mock_send_reminder_email(email: str, invoice_id: int, due_date: date):
    timestamp = datetime.now().isoformat()
    logger.info(f"[{timestamp}] 📧 Sending mock reminder email")
    logger.info(f"  → To: {email}")
    logger.info(f"  → Subject: Payment Reminder - Invoice #{invoice_id}")
    logger.info(f"  → Body: Invoice #{invoice_id} is due on {due_date}.")
    logger.info("  ✔ Reminder email simulated successfully.")


def mock_stripe_charge(user_id: int, invoice_id: int, amount: float) -> bool:
    timestamp = datetime.now().isoformat()
    logger.info(f"[{timestamp}] 💳 Mock Stripe charge started")
    logger.info(f"  → Charging User ID: {user_id}")
    logger.info(f"  → Invoice ID: {invoice_id}")
    logger.info(f"  → Amount: ${amount:.2f}")

    success = random.random() < 0.9
    if success:
        logger.info("  ✔ Payment authorized and captured successfully.")
    else:
        logger.warning(
            "  ❌ Payment failed due to mock insufficient funds or network error."
        )
    return success
