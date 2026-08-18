from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.sql import func

from app.database import Base


class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    device_name = Column(String(255), nullable=False)
    user_name = Column(String(255), nullable=False)
    ip_address = Column(String(64), nullable=False, index=True)
    location_or_point = Column(String(255), nullable=False)
    notes = Column(String(1000), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    status = Column(String(20), default="unknown", nullable=False)
    last_ping_at = Column(DateTime, nullable=True)
    last_response_ms = Column(Integer, nullable=True)
    down_since = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        server_default=func.now(),
        nullable=False,
    )
