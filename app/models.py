import enum

from sqlalchemy import Column, Date, DateTime
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)  # Simple password for now
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    subscriptions = relationship("Subscription", back_populates="user")
    invoices = relationship("Invoice", back_populates="user")


class Plan(Base):
    __tablename__ = "plans"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    price = Column(Float, nullable=False)
    description = Column(String)

    subscriptions = relationship("Subscription", back_populates="plan")
    invoices = relationship("Invoice", back_populates="plan")


class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "active"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class Subscription(Base):
    __tablename__ = "subscriptions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(
        Date, nullable=True
    )  # Nullable if it's an ongoing auto-renewing subscription
    status = Column(
        SQLAlchemyEnum(SubscriptionStatus),
        default=SubscriptionStatus.ACTIVE,
        nullable=False,
    )
    next_billing_date = Column(Date, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user = relationship("User", back_populates="subscriptions")
    plan = relationship("Plan", back_populates="subscriptions")
    invoices = relationship("Invoice", back_populates="subscription")


class InvoiceStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"  # If subscription is cancelled before payment


class Invoice(Base):
    __tablename__ = "invoices"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    plan_id = Column(
        Integer, ForeignKey("plans.id"), nullable=False
    )  # Denormalized for easy access
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=False)
    amount = Column(Float, nullable=False)
    issue_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=False)
    status = Column(
        SQLAlchemyEnum(InvoiceStatus), default=InvoiceStatus.PENDING, nullable=False
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    paid_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="invoices")
    plan = relationship("Plan", back_populates="invoices")
    subscription = relationship("Subscription", back_populates="invoices")
