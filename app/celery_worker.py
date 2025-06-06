from datetime import date

from celery import Celery
from celery.schedules import crontab

from . import crud, models, utils
from .config import CELERY_BROKER_URL, CELERY_RESULT_BACKEND
from .database import SessionLocal

celery_app = Celery(
    "tasks",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=["app.celery_worker"],
)


celery_app.conf.timezone = 'UTC'

# used local time for testing 
# celery_app.conf.timezone = "Asia/Kolkata"
# celery_app.conf.enable_utc = False


@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    # Generate invoices daily for subscriptions due for billing
    sender.add_periodic_task(
        crontab(hour=1, minute=0),  # Run daily at 1:00 AM UTC
        generate_renewal_invoices_task.s(),
        name="generate-renewal-invoices-daily",
    )
    # Mark overdue invoices
    sender.add_periodic_task(
        crontab(hour=2, minute=0),  # Run daily at 2:00 AM UTC
        mark_overdue_invoices_task.s(),
        name="mark-overdue-invoices-daily",
    )
    # Send payment reminders
    sender.add_periodic_task(
        crontab(hour=3, minute=0),  # Run daily at 3:00 AM UTC
        send_payment_reminders_task.s(),
        name="send-payment-reminders-daily",
    )


def get_db_session():
    """Helper to get DB session in Celery tasks"""
    return SessionLocal()


@celery_app.task(name="app.celery_worker.generate_initial_invoice_task")
def generate_initial_invoice_task(subscription_id: int):
    """Generates the first invoice for a new subscription."""
    db = get_db_session()
    try:
        subscription = crud.get_subscription(db, subscription_id)
        if not subscription or subscription.status != models.SubscriptionStatus.ACTIVE:
            print(
                f"Subscription {subscription_id} not found or not active for initial invoice."
            )
            return

        # For simplicity, assume first invoice is on start_date
        existing_invoice = (
            db.query(models.Invoice)
            .filter(
                models.Invoice.subscription_id == subscription_id,
                models.Invoice.issue_date == subscription.start_date,
            )
            .first()
        )

        if existing_invoice:
            print(
                f"Initial invoice for subscription {subscription_id} on {subscription.start_date} already exists."
            )
            return

        invoice = crud.create_invoice(
            db, subscription, issue_date=subscription.start_date
        )
        print(
            f"Generated initial invoice {invoice.id} for subscription {subscription.id}"
        )

        # Update next billing date for the subscription
        next_billing = utils.calculate_next_billing_date(subscription.start_date)
        crud.update_subscription_next_billing_date(db, subscription.id, next_billing)
        print(
            f"Updated next billing date for subscription {subscription.id} to {next_billing}"
        )

    finally:
        db.close()


@celery_app.task(name="app.celery_worker.generate_renewal_invoices_task")
def generate_renewal_invoices_task():
    db = get_db_session()
    try:
        today = date.today()
        print(f"CELERY: Running generate_renewal_invoices_task for date: {today}")
        subscriptions_for_renewal = crud.get_subscriptions_for_renewal(db, today)

        for sub in subscriptions_for_renewal:
            print(f"CELERY: Processing subscription ID {sub.id} for user {sub.user_id}")
            # an invoice for this exact date and subscription doesn't already exist
            existing_invoice = (
                db.query(models.Invoice)
                .filter(
                    models.Invoice.subscription_id == sub.id,
                    models.Invoice.issue_date == today,
                )
                .first()
            )
            if existing_invoice:
                print(
                    f"CELERY: Invoice for subscription {sub.id} on {today} already exists. Skipping."
                )
                # Still update next billing date if it matches today to prevent re-processing
                if sub.next_billing_date == today:
                    next_billing = utils.calculate_next_billing_date(today)
                    crud.update_subscription_next_billing_date(db, sub.id, next_billing)
                    print(
                        f"CELERY: Updated next_billing_date for sub {sub.id} to {next_billing} (already invoiced)."
                    )
                continue

            invoice = crud.create_invoice(db, sub, issue_date=today)
            print(
                f"CELERY: Generated renewal invoice {invoice.id} for subscription {sub.id}"
            )

            # Update next billing date for the subscription
            next_billing = utils.calculate_next_billing_date(today)
            crud.update_subscription_next_billing_date(db, sub.id, next_billing)
            print(
                f"CELERY: Updated next billing date for subscription {sub.id} to {next_billing}"
            )

    except Exception as e:
        print(f"CELERY ERROR in generate_renewal_invoices_task: {e}")
    finally:
        db.close()


@celery_app.task(name="app.celery_worker.mark_overdue_invoices_task")
def mark_overdue_invoices_task():
    db = get_db_session()
    try:
        today = date.today()
        print(f"CELERY: Running mark_overdue_invoices_task for date: {today}")
        overdue_invoices = crud.get_pending_invoices_past_due(db, today)

        for invoice in overdue_invoices:
            print(
                f"CELERY: Marking invoice {invoice.id} (due: {invoice.due_date}) as OVERDUE"
            )
            crud.update_invoice_status(db, invoice.id, models.InvoiceStatus.OVERDUE)
            # Optionally, you might want to take action on the subscription here
            # e.g., change subscription status to 'expired' or 'suspended' after X overdue invoices
    except Exception as e:
        print(f"CELERY ERROR in mark_overdue_invoices_task: {e}")
    finally:
        db.close()


@celery_app.task(name="app.celery_worker.send_payment_reminders_task")
def send_payment_reminders_task():
    db = get_db_session()
    try:
        today = date.today()
        print(f"CELERY: Running send_payment_reminders_task for date: {today}")
        # send reminder 3 days before due date, and daily if overdue
        invoices_to_remind = crud.get_unpaid_invoices_for_reminder(db, today)

        for invoice in invoices_to_remind:
            user = crud.get_user(db, invoice.user_id)
            if user:
                print(
                    f"CELERY: Preparing reminder for invoice {invoice.id} (status: {invoice.status}, due: {invoice.due_date}) for user {user.email}"
                )
                utils.mock_send_reminder_email(user.email, invoice.id, invoice.due_date)
    except Exception as e:
        print(f"CELERY ERROR in send_payment_reminders_task: {e}")
    finally:
        db.close()
