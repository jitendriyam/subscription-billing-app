import logging 

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from typing import List

from . import crud, models, schemas, utils
from .database import engine, create_db_and_tables, get_db
from .config import PLANS_DATA, landing_page_html_content
from .celery_worker import generate_initial_invoice_task

# ---- Logging Setup ----
logging.basicConfig(level=logging.INFO) 
logger = logging.getLogger(__name__)

# ---- Create tables on startup ----
logger.info("Setting up database tables...")
create_db_and_tables()

app = FastAPI(
    title="Subscription Billing API",
    description="A backend system for managing user subscriptions and automated billing.",
    version="0.1.0"
)

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def root_landing_page():
    logger.info("Landing page accessed.")
    return HTMLResponse(content=landing_page_html_content, status_code=200)

@app.post("/seed-plans/", tags=["Admin"], status_code=status.HTTP_201_CREATED)
def seed_plans(db: Session = Depends(get_db)):
    logger.info("Seeding plans...")
    existing_plans_count = db.query(models.Plan).count()
    if existing_plans_count > 0:
        created_count = 0
        for plan_data in PLANS_DATA:
            if not crud.get_plan_by_name(db, plan_data["name"]):
                crud.create_plan(db=db, plan=schemas.PlanCreate(**plan_data))
                created_count +=1
        if created_count > 0:
            logger.info(f"{created_count} new plans added.")
            return {"message": f"{created_count} new plans seeded successfully."}
        logger.info("No new plans to seed.")
        return {"message": "Plans already exist or no new plans to seed."}

    for plan_data in PLANS_DATA:
        crud.create_plan(db=db, plan=schemas.PlanCreate(**plan_data))
    logger.info("All predefined plans seeded.")
    return {"message": "Predefined plans seeded successfully."}

@app.post("/users/", response_model=schemas.User, status_code=status.HTTP_201_CREATED, tags=["Users"])
def create_user_endpoint(user: schemas.UserCreate, db: Session = Depends(get_db)):
    logger.info(f"Creating user with email: {user.email}")
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        logger.warning("Email already registered.")
        raise HTTPException(status_code=400, detail="Email already registered")
    return crud.create_user(db=db, user=user)

@app.get("/users/{user_id}/", response_model=schemas.User, tags=["Users"])
def read_user(user_id: int, db: Session = Depends(get_db)):
    logger.info(f"Fetching user with ID: {user_id}")
    db_user = crud.get_user(db, user_id=user_id)
    if db_user is None:
        logger.warning(f"User with ID {user_id} not found.")
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@app.get("/plans/", response_model=List[schemas.Plan], tags=["Plans"])
def read_plans(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    logger.info("Getting plans list...")
    return crud.get_plans(db, skip=skip, limit=limit)

@app.post("/users/{user_id}/subscribe/", response_model=schemas.Subscription, tags=["Subscriptions"])
def user_subscribe_to_plan(user_id: int, subscription_request: schemas.SubscribeRequest, db: Session = Depends(get_db)):
    logger.info(f"User {user_id} subscribing to plan {subscription_request.plan_id}")
    user = crud.get_user(db, user_id)
    if not user:
        logger.warning("User not found.")
        raise HTTPException(status_code=404, detail="User not found")

    plan = crud.get_plan(db, subscription_request.plan_id)
    if not plan:
        logger.warning("Plan not found.")
        raise HTTPException(status_code=404, detail="Plan not found")

    active_subscription = crud.get_active_user_subscription_for_plan(db, user_id, subscription_request.plan_id)
    if active_subscription:
        logger.info("User already subscribed to this plan.")
        raise HTTPException(status_code=400, detail="User already has an active subscription to this plan.")

    new_subscription = crud.create_subscription(db, user_id=user_id, plan_id=subscription_request.plan_id)
    if not new_subscription:
        logger.error("Failed to create subscription.")
        raise HTTPException(status_code=500, detail="Could not create subscription")

    logger.info(f"Subscription created with ID {new_subscription.id}, triggering invoice task...")
    generate_initial_invoice_task.delay(new_subscription.id)

    return new_subscription

@app.put("/subscriptions/{subscription_id}/cancel/", response_model=schemas.Subscription, tags=["Subscriptions"])
def cancel_subscription_endpoint(subscription_id: int, db: Session = Depends(get_db)):
    logger.info(f"Cancelling subscription {subscription_id}")
    subscription = crud.get_subscription(db, subscription_id)
    if not subscription:
        logger.warning("Subscription not found.")
        raise HTTPException(status_code=404, detail="Subscription not found")
    if subscription.status == models.SubscriptionStatus.CANCELLED:
        logger.info("Subscription already cancelled.")
        raise HTTPException(status_code=400, detail="Subscription is already cancelled")

    updated_subscription = crud.update_subscription_status(db, subscription_id, models.SubscriptionStatus.CANCELLED)
    return updated_subscription

@app.get("/users/{user_id}/subscriptions/", response_model=List[schemas.Subscription], tags=["Subscriptions"])
def get_user_subscriptions_endpoint(user_id: int, db: Session = Depends(get_db)):
    logger.info(f"Getting subscriptions for user {user_id}")
    user = crud.get_user(db, user_id)
    if not user:
        logger.warning("User not found.")
        raise HTTPException(status_code=404, detail="User not found")
    return crud.get_user_subscriptions(db, user_id=user_id)

@app.get("/users/{user_id}/invoices/", response_model=List[schemas.Invoice], tags=["Invoices"])
def get_user_invoices_endpoint(user_id: int, db: Session = Depends(get_db)):
    logger.info(f"Fetching invoices for user {user_id}")
    user = crud.get_user(db, user_id)
    if not user:
        logger.warning("User not found.")
        raise HTTPException(status_code=404, detail="User not found")
    return crud.get_user_invoices(db, user_id=user_id)

@app.get("/invoices/{invoice_id}/", response_model=schemas.Invoice, tags=["Invoices"])
def get_invoice_endpoint(invoice_id: int, db: Session = Depends(get_db)):
    logger.info(f"Getting invoice with ID {invoice_id}")
    invoice = crud.get_invoice(db, invoice_id)
    if not invoice:
        logger.warning("Invoice not found.")
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice

@app.post("/invoices/{invoice_id}/pay/", response_model=schemas.Invoice, tags=["Invoices"])
def pay_invoice_endpoint(invoice_id: int, db: Session = Depends(get_db)):
    logger.info(f"Paying invoice {invoice_id}")
    invoice = crud.get_invoice(db, invoice_id)
    if not invoice:
        logger.warning("Invoice not found.")
        raise HTTPException(status_code=404, detail="Invoice not found")
    if invoice.status == models.InvoiceStatus.PAID:
        logger.info("Invoice already paid.")
        raise HTTPException(status_code=400, detail="Invoice already paid")

    user = crud.get_user(db, invoice.user_id)
    if not user:
        logger.error("User linked to invoice not found.")
        raise HTTPException(status_code=404, detail="User associated with invoice not found")

    payment_successful = utils.mock_stripe_charge(user_id=user.id, invoice_id=invoice.id, amount=invoice.amount)

    if payment_successful:
        logger.info("Payment successful, updating invoice status.")
        return crud.update_invoice_status(db, invoice.id, models.InvoiceStatus.PAID)
    else:
        logger.error("Mock Stripe payment failed.")
        raise HTTPException(status_code=500, detail="Mock Stripe payment failed")
