import logging
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from . import models, schemas, utils

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# --- User CRUD ---
def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()


def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = utils.get_password_hash(user.password)
    db_user = models.User(email=user.email, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


# --- Plan CRUD ---
def get_plan(db: Session, plan_id: int):
    return db.query(models.Plan).filter(models.Plan.id == plan_id).first()


def get_plan_by_name(db: Session, name: str):
    return db.query(models.Plan).filter(models.Plan.name == name).first()


def get_plans(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Plan).offset(skip).limit(limit).all()


def create_plan(db: Session, plan: schemas.PlanCreate):
    db_plan = models.Plan(**plan.model_dump())
    db.add(db_plan)
    db.commit()
    db.refresh(db_plan)
    return db_plan


# --- Subscription CRUD ---
def get_subscription(db: Session, subscription_id: int):
    return (
        db.query(models.Subscription)
        .filter(models.Subscription.id == subscription_id)
        .first()
    )


def get_user_subscriptions(db: Session, user_id: int):
    return (
        db.query(models.Subscription)
        .filter(models.Subscription.user_id == user_id)
        .all()
    )


def get_active_user_subscription_for_plan(db: Session, user_id: int, plan_id: int):
    return (
        db.query(models.Subscription)
        .filter(
            models.Subscription.user_id == user_id,
            models.Subscription.plan_id == plan_id,
            models.Subscription.status == models.SubscriptionStatus.ACTIVE,
        )
        .first()
    )


def get_subscriptions_for_renewal(db: Session, billing_date: date):
    return (
        db.query(models.Subscription)
        .filter(
            models.Subscription.status == models.SubscriptionStatus.ACTIVE,
            models.Subscription.next_billing_date == billing_date,
        )
        .all()
    )


def create_subscription(db: Session, user_id: int, plan_id: int):
    today = date.today()
    plan = get_plan(db, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail=f"Plan ID '{plan_id}' not found.")

    db_subscription = models.Subscription(
        user_id=user_id,
        plan_id=plan_id,
        start_date=today,
        status=models.SubscriptionStatus.ACTIVE,
        next_billing_date=today,  # First invoice will be generated for today
    )
    db.add(db_subscription)
    db.commit()
    db.refresh(db_subscription)
    return db_subscription


def update_subscription_status(
    db: Session, subscription_id: int, status: models.SubscriptionStatus
):
    db_subscription = get_subscription(db, subscription_id)
    if db_subscription:
        db_subscription.status = status
        if status == models.SubscriptionStatus.CANCELLED:
            db_subscription.end_date = date.today()
            db_subscription.next_billing_date = None  # Stop future billing
        db.commit()
        db.refresh(db_subscription)
    return db_subscription


def update_subscription_next_billing_date(
    db: Session, subscription_id: int, next_billing_date: date
):
    db_subscription = get_subscription(db, subscription_id)
    if db_subscription:
        db_subscription.next_billing_date = next_billing_date
        db.commit()
        db.refresh(db_subscription)
    return db_subscription


# --- Invoice CRUD ---
def get_invoice(db: Session, invoice_id: int):
    return db.query(models.Invoice).filter(models.Invoice.id == invoice_id).first()


def get_user_invoices(db: Session, user_id: int):
    return (
        db.query(models.Invoice)
        .filter(models.Invoice.user_id == user_id)
        .order_by(models.Invoice.issue_date.desc())
        .all()
    )


def get_pending_invoices_past_due(db: Session, current_date: date):
    return (
        db.query(models.Invoice)
        .filter(
            models.Invoice.status == models.InvoiceStatus.PENDING,
            models.Invoice.due_date < current_date,
        )
        .all()
    )


def get_unpaid_invoices_for_reminder(db: Session, reminder_date: date):
    """Remind for invoices PENDING and due in 3 days OR already OVERDUE"""
    return (
        db.query(models.Invoice)
        .filter(
            (models.Invoice.status == models.InvoiceStatus.PENDING)
            & (models.Invoice.due_date == reminder_date + timedelta(days=3))
            | (models.Invoice.status == models.InvoiceStatus.OVERDUE)
        )
        .all()
    )


def create_invoice(db: Session, subscription: models.Subscription, issue_date: date):
    plan = subscription.plan
    if not plan:
        plan = get_plan(db, subscription.plan_id)

    due_date = utils.calculate_due_date(issue_date)

    db_invoice = models.Invoice(
        user_id=subscription.user_id,
        plan_id=subscription.plan_id,
        subscription_id=subscription.id,
        amount=plan.price,
        issue_date=issue_date,
        due_date=due_date,
        status=models.InvoiceStatus.PENDING,
    )
    db.add(db_invoice)
    db.commit()
    db.refresh(db_invoice)
    return db_invoice


def update_invoice_status(
    db: Session,
    invoice_id: int,
    status: models.InvoiceStatus,
    paid_at: Optional[datetime] = None,
):
    db_invoice = get_invoice(db, invoice_id)
    if db_invoice:
        db_invoice.status = status
        if status == models.InvoiceStatus.PAID:
            db_invoice.paid_at = paid_at if paid_at else datetime.utcnow()
        db.commit()
        db.refresh(db_invoice)
    return db_invoice
