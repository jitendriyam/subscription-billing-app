from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr

from .models import InvoiceStatus, SubscriptionStatus


# --- User Schemas ---
class UserBase(BaseModel):
    email: EmailStr


class UserCreate(UserBase):
    password: str


class User(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# --- Plan Schemas ---
class PlanBase(BaseModel):
    name: str
    price: float
    description: Optional[str] = None


class PlanCreate(PlanBase):
    pass


class Plan(PlanBase):
    id: int

    class Config:
        from_attributes = True


# --- Subscription Schemas ---
class SubscriptionBase(BaseModel):
    user_id: int
    plan_id: int

class SubscriptionUpdate(BaseModel):
    status: Optional[SubscriptionStatus] = None


class Subscription(SubscriptionBase):
    id: int
    start_date: date
    end_date: Optional[date] = None
    status: SubscriptionStatus
    next_billing_date: Optional[date] = None
    created_at: datetime
    updated_at: datetime
    plan: Plan

    class Config:
        from_attributes = True


# --- Invoice Schemas ---
class InvoiceBase(BaseModel):
    user_id: int
    plan_id: int
    subscription_id: int
    amount: float
    issue_date: date
    due_date: date
    status: InvoiceStatus


class InvoiceCreate(InvoiceBase):
    pass


class Invoice(InvoiceBase):
    id: int
    created_at: datetime
    paid_at: Optional[datetime] = None
    plan: Plan 

    class Config:
        from_attributes = True


# --- API Request/Response Specific ---
class SubscribeRequest(BaseModel):
    plan_id: int


class UserSubscriptionResponse(BaseModel):
    user: User
    subscriptions: List[Subscription]


class UserInvoiceResponse(BaseModel):
    user: User
    invoices: List[Invoice]
