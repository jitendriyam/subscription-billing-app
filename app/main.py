from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from typing import List

from . import crud, models, schemas, utils
from .database import engine, create_db_and_tables, get_db
from .config import PLANS_DATA, landing_page_html_content
from .celery_worker import generate_initial_invoice_task # Import the task

# Create database tables on startup
create_db_and_tables()

app = FastAPI(
    title="Subscription Billing API",
    description="A backend system for managing user subscriptions and automated billing.",
    version="0.1.0"
    )

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def root_landing_page():
    
    return HTMLResponse(content=landing_page_html_content, status_code=200)


# --- Helper Endpoint to Seed Plans (run once) ---
@app.post("/seed-plans/", tags=["Admin"], status_code=status.HTTP_201_CREATED)
def seed_plans(db: Session = Depends(get_db)):
    existing_plans_count = db.query(models.Plan).count()
    if existing_plans_count > 0:
        # Check if plans with these names already exist to avoid duplicates
        created_count = 0
        for plan_data in PLANS_DATA:
            if not crud.get_plan_by_name(db, plan_data["name"]):
                crud.create_plan(db=db, plan=schemas.PlanCreate(**plan_data))
                created_count +=1
        if created_count > 0:
             return {"message": f"{created_count} new plans seeded successfully."}
        return {"message": "Plans already exist or no new plans to seed."}

    for plan_data in PLANS_DATA:
        crud.create_plan(db=db, plan=schemas.PlanCreate(**plan_data))
    return {"message": "Predefined plans seeded successfully."}

# --- User Endpoints ---
@app.post("/users/", response_model=schemas.User, status_code=status.HTTP_201_CREATED, tags=["Users"])
def create_user_endpoint(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return crud.create_user(db=db, user=user)

@app.get("/users/{user_id}/", response_model=schemas.User, tags=["Users"])
def read_user(user_id: int, db: Session = Depends(get_db)):
    db_user = crud.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

# --- Plan Endpoints ---
@app.get("/plans/", response_model=List[schemas.Plan], tags=["Plans"])
def read_plans(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    plans = crud.get_plans(db, skip=skip, limit=limit)
    return plans

# --- Subscription Endpoints ---
@app.post("/users/{user_id}/subscribe/", response_model=schemas.Subscription, tags=["Subscriptions"])
def user_subscribe_to_plan(
    user_id: int, 
    subscription_request: schemas.SubscribeRequest, 
    db: Session = Depends(get_db)
):
    user = crud.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    plan = crud.get_plan(db, subscription_request.plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    # Check if user already has an active subscription to this plan
    active_subscription = crud.get_active_user_subscription_for_plan(db, user_id, subscription_request.plan_id)
    if active_subscription:
        raise HTTPException(status_code=400, detail="User already has an active subscription to this plan.")

    # Create new subscription
    new_subscription = crud.create_subscription(db, user_id=user_id, plan_id=subscription_request.plan_id)
    if not new_subscription: # Should not happen if user and plan checks pass
         raise HTTPException(status_code=500, detail="Could not create subscription")

    # Trigger Celery task to generate the initial invoice
    generate_initial_invoice_task.delay(new_subscription.id)
    
    return new_subscription

@app.put("/subscriptions/{subscription_id}/cancel/", response_model=schemas.Subscription, tags=["Subscriptions"])
def cancel_subscription_endpoint(subscription_id: int, db: Session = Depends(get_db)):
    subscription = crud.get_subscription(db, subscription_id)
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")
    if subscription.status == models.SubscriptionStatus.CANCELLED:
        raise HTTPException(status_code=400, detail="Subscription is already cancelled")

    updated_subscription = crud.update_subscription_status(db, subscription_id, models.SubscriptionStatus.CANCELLED)
    return updated_subscription

@app.get("/users/{user_id}/subscriptions/", response_model=List[schemas.Subscription], tags=["Subscriptions"])
def get_user_subscriptions_endpoint(user_id: int, db: Session = Depends(get_db)):
    user = crud.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return crud.get_user_subscriptions(db, user_id=user_id)

# --- Invoice Endpoints ---
@app.get("/users/{user_id}/invoices/", response_model=List[schemas.Invoice], tags=["Invoices"])
def get_user_invoices_endpoint(user_id: int, db: Session = Depends(get_db)):
    user = crud.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return crud.get_user_invoices(db, user_id=user_id)

@app.get("/invoices/{invoice_id}/", response_model=schemas.Invoice, tags=["Invoices"])
def get_invoice_endpoint(invoice_id: int, db: Session = Depends(get_db)):
    invoice = crud.get_invoice(db, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice

@app.post("/invoices/{invoice_id}/pay/", response_model=schemas.Invoice, tags=["Invoices"])
def pay_invoice_endpoint(invoice_id: int, db: Session = Depends(get_db)):
    invoice = crud.get_invoice(db, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if invoice.status == models.InvoiceStatus.PAID:
        raise HTTPException(status_code=400, detail="Invoice already paid")

    # MOCK Stripe payment
    user = crud.get_user(db, invoice.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User associated with invoice not found")

    payment_successful = utils.mock_stripe_charge(user_id=user.id, invoice_id=invoice.id, amount=invoice.amount)

    if payment_successful:
        updated_invoice = crud.update_invoice_status(db, invoice.id, models.InvoiceStatus.PAID)
        return updated_invoice
    else:
        raise HTTPException(status_code=500, detail="Mock Stripe payment failed")
