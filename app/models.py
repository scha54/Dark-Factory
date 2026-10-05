from datetime import datetime
import uuid
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class Restaurant(Base):
    __tablename__ = "restaurants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    cuisine = Column(String(50), nullable=False, index=True)
    city = Column(String(50), nullable=False, index=True)
    address = Column(String(200), nullable=False)
    phone = Column(String(20), nullable=False)
    description = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    tables = relationship("Table", back_populates="restaurant", cascade="all, delete-orphan")
    time_slots = relationship("TimeSlot", back_populates="restaurant", cascade="all, delete-orphan")
    reservations = relationship("Reservation", back_populates="restaurant", cascade="all, delete-orphan")


class Table(Base):
    __tablename__ = "tables"

    id = Column(Integer, primary_key=True, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=False)
    table_number = Column(Integer, nullable=False)
    capacity = Column(Integer, nullable=False, index=True)
    location_type = Column(String(50), default="indoor")  # indoor, outdoor, window, patio

    restaurant = relationship("Restaurant", back_populates="tables")
    reservations = relationship("Reservation", back_populates="table")


class TimeSlot(Base):
    __tablename__ = "time_slots"

    id = Column(Integer, primary_key=True, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=False)
    slot_time = Column(String(10), nullable=False)  # e.g., "18:00", "19:30"

    restaurant = relationship("Restaurant", back_populates="time_slots")


class Reservation(Base):
    __tablename__ = "reservations"

    id = Column(Integer, primary_key=True, index=True)
    booking_reference = Column(
        String(36), unique=True, nullable=False, index=True, default=lambda: str(uuid.uuid4())[:8].upper()
    )
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=False)
    table_id = Column(Integer, ForeignKey("tables.id"), nullable=False)
    customer_name = Column(String(100), nullable=False)
    customer_email = Column(String(100), nullable=False)
    customer_phone = Column(String(20), nullable=False)
    guests = Column(Integer, nullable=False)
    date = Column(String(10), nullable=False, index=True)  # YYYY-MM-DD
    time_slot = Column(String(10), nullable=False, index=True)  # HH:MM
    status = Column(String(20), nullable=False, default="CONFIRMED")  # CONFIRMED, CANCELLED
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    restaurant = relationship("Restaurant", back_populates="reservations")
    table = relationship("Table", back_populates="reservations")

    __table_args__ = (
        # Unique constraint to enforce zero double-booking for the same active reservation slot
        UniqueConstraint("table_id", "date", "time_slot", "status", name="uix_table_date_slot_status"),
    )
