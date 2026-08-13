"""
Modelos de datos (tablas de la base de datos).

Relaciones principales:
  User (1) --- (N) Membership
  User (1) --- (N) Payment
  GymClass (1) --- (N) ClassBooking --- (N) User
"""
import enum
from datetime import datetime, date

from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Date, Numeric,
    ForeignKey, Enum as SAEnum
)
from sqlalchemy.orm import relationship

from app.database import Base


class UserRole(str, enum.Enum):
    admin = "admin"
    user = "user"


class MembershipStatus(str, enum.Enum):
    active = "active"
    expired = "expired"
    paused = "paused"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(120), nullable=False)
    email = Column(String(120), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(SAEnum(UserRole), default=UserRole.user, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    memberships = relationship("Membership", back_populates="user", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="user", cascade="all, delete-orphan")
    bookings = relationship("ClassBooking", back_populates="user", cascade="all, delete-orphan")


class Membership(Base):
    __tablename__ = "memberships"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    plan_name = Column(String(80), nullable=False, default="Mensual")
    price = Column(Numeric(10, 2), nullable=False, default=0)
    start_date = Column(Date, nullable=False, default=date.today)
    end_date = Column(Date, nullable=False)
    status = Column(SAEnum(MembershipStatus), default=MembershipStatus.active)

    user = relationship("User", back_populates="memberships")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    membership_id = Column(Integer, ForeignKey("memberships.id"), nullable=True)
    amount = Column(Numeric(10, 2), nullable=False)
    payment_date = Column(DateTime, default=datetime.utcnow)
    method = Column(String(40), default="efectivo")

    user = relationship("User", back_populates="payments")


class GymClass(Base):
    __tablename__ = "gym_classes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(80), nullable=False)
    instructor = Column(String(80), nullable=True)
    day_of_week = Column(String(20), nullable=False)   # ej: "Lunes"
    start_time = Column(String(5), nullable=False)      # ej: "18:00"
    capacity = Column(Integer, nullable=False, default=20)

    bookings = relationship("ClassBooking", back_populates="gym_class", cascade="all, delete-orphan")


class ClassBooking(Base):
    __tablename__ = "class_bookings"

    id = Column(Integer, primary_key=True, index=True)
    class_id = Column(Integer, ForeignKey("gym_classes.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    booked_at = Column(DateTime, default=datetime.utcnow)
    attended = Column(Boolean, default=False)

    gym_class = relationship("GymClass", back_populates="bookings")
    user = relationship("User", back_populates="bookings")
