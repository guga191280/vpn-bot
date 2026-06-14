from sqlalchemy import Column, Integer, BigInteger, String, DateTime, Boolean, Float, Text
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String(100))
    full_name = Column(String(200))
    created_at = Column(DateTime, default=datetime.utcnow)
    is_banned = Column(Boolean, default=False)

class Subscription(Base):
    __tablename__ = "subscriptions"
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, nullable=False)
    xui_client_id = Column(String(100))
    vpn_key = Column(Text)
    plan = Column(String(50))
    traffic_limit_gb = Column(Float, default=0)
    starts_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
    is_active = Column(Boolean, default=True)
    notified_expiry = Column(Boolean, default=False)

class Payment(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, nullable=False)
    amount = Column(Float)
    plan = Column(String(50))
    label = Column(String(200), unique=True)
    status = Column(String(50), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    paid_at = Column(DateTime)

class Tariff(Base):
    __tablename__ = "tariffs"
    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    slug = Column(String(50), unique=True)
    price = Column(Float)
    days = Column(Integer)
    traffic_gb = Column(Float, default=0)
    is_active = Column(Boolean, default=True)
