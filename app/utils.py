import random
from datetime import date, datetime, timedelta

from dateutil.relativedelta import relativedelta
from passlib.context import CryptContext

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
    print(f"[{timestamp}] 📧 [MOCK EMAIL SERVICE]")
    print(f"  → To: {email}")
    print(f"  → Subject: Payment Reminder - Invoice #{invoice_id}")
    print(
        f"  → Body: This is a friendly reminder that your invoice #{invoice_id} is due on {due_date}."
    )
    print("  ✔ Reminder email simulated successfully.\n")


def mock_stripe_charge(user_id: int, invoice_id: int, amount: float) -> bool:
    timestamp = datetime.now().isoformat()
    print(f"[{timestamp}] 💳 [MOCK STRIPE PAYMENT GATEWAY]")
    print(f"  → Charging User ID: {user_id}")
    print(f"  → Invoice ID: {invoice_id}")
    print(f"  → Amount: ${amount:.2f}")

    # Simulate a 90% success rate
    success = random.random() < 0.9
    if success:
        print("  ✔ Payment authorized and captured successfully.\n")
    else:
        print("  ❌ Payment failed due to mock insufficient funds or network error.\n")
    return success
