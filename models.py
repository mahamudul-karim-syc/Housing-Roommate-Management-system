from database import Base
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Float
from datetime import datetime


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True)
    username = Column(String, unique=True)
    firstname = Column(String)
    lastname = Column(String)
    hashpassword = Column(String)
    phone = Column(String)
    role = Column(String)# user  / admin
    is_active = Column(Boolean, default=True)
  

class Room(Base):
    __tablename__ = "rooms"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    category = Column(String) # single / shared / family
    description = Column(String)
    rent = Column(Float, default=0.0)
    address = Column(String)
    room_size = Column(String, nullable=True)
    total_seats = Column(Integer, default=1)
    available_seats = Column(Integer, default=1)
    cover_image = Column(String, nullable=True)
    admin_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.now)


class Reservation(Base):
    __tablename__ = "reservations"
    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    reservation_date = Column(DateTime, default=datetime.now)
    status = Column(String) # pending / approved / rejected / cancelled


class RentPayment(Base):
    __tablename__ = "rent_payments"

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    amount = Column(Float, nullable=False)
    payment_date = Column(DateTime, default=datetime.now)
    payment_method = Column(String)# cash / bkash / nagad / bank
    status = Column(String, default="paid")# paid / pending / failed
    transaction_id = Column(String, nullable=True)


class Roommate_Requests(Base):
    __tablename__ = "roommate_requests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    preferred_location = Column(String)
    budget_min = Column(Float, default=0.0)
    budget_max = Column(Float, default=0.0)
    preferred_category = Column(String)# single / shared / family
    description = Column(String)
    status = Column(String)# active / matched / closed
    created_at = Column(DateTime, default=datetime.now)


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    rating = Column(Integer)# 1 - 5
    comment = Column(String)
    created_at = Column(DateTime, default=datetime.now)
    