"""SQLAlchemy ORM models — smart home operations database schema.

7 tables simulating a real operations data platform with millions of rows:
- regions (3K): geographic hierarchy
- device_types (50): product categories
- users (1M): smart home end users
- devices (5M): IoT devices
- device_events (30M): event logs
- voice_commands (10M): user voice interactions
- service_orders (500K): maintenance tickets
"""

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, Index, Text
)
from sqlalchemy.orm import DeclarativeBase, relationship
from datetime import datetime


class Base(DeclarativeBase):
    pass


class Region(Base):
    __tablename__ = "regions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    province = Column(String(32), nullable=False, index=True)
    city = Column(String(64), nullable=False, index=True)
    district = Column(String(64))

    devices = relationship("Device", back_populates="region")


class DeviceType(Base):
    __tablename__ = "device_types"

    id = Column(Integer, primary_key=True, autoincrement=True)
    type_name = Column(String(64), nullable=False, unique=True)  # light, lock, thermostat, camera, speaker
    category = Column(String(32), nullable=False)  # security, comfort, entertainment, appliance

    devices = relationship("Device", back_populates="device_type")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), nullable=False)
    phone = Column(String(20))
    registered_at = Column(DateTime, default=datetime.utcnow, index=True)
    status = Column(String(16), default="active")  # active / inactive / deleted

    devices = relationship("Device", back_populates="owner")


class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_name = Column(String(128), nullable=False)
    device_type_id = Column(Integer, ForeignKey("device_types.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    region_id = Column(Integer, ForeignKey("regions.id"), nullable=False, index=True)
    status = Column(String(16), default="online", index=True)  # online / offline / error
    firmware_version = Column(String(32))
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    device_type = relationship("DeviceType", back_populates="devices")
    owner = relationship("User", back_populates="devices")
    region = relationship("Region", back_populates="devices")
    events = relationship("DeviceEvent", back_populates="device")
    voice_commands = relationship("VoiceCommand", back_populates="device")
    service_orders = relationship("ServiceOrder", back_populates="device")

    __table_args__ = (
        Index("idx_device_user_status", "user_id", "status"),
    )


class DeviceEvent(Base):
    __tablename__ = "device_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False, index=True)
    event_type = Column(String(32), nullable=False, index=True)  # power_on, power_off, alert, fw_update, error
    event_detail = Column(Text)
    occurred_at = Column(DateTime, default=datetime.utcnow, index=True)

    device = relationship("Device", back_populates="events")

    __table_args__ = (
        Index("idx_event_device_time", "device_id", "occurred_at"),
        Index("idx_event_type_time", "event_type", "occurred_at"),
    )


class VoiceCommand(Base):
    __tablename__ = "voice_commands"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False, index=True)
    command_text = Column(Text, nullable=False)
    intent = Column(String(64), index=True)  # search_movie, query_weather, control_device, chat
    response_text = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    device = relationship("Device", back_populates="voice_commands")

    __table_args__ = (
        Index("idx_voice_device_time", "device_id", "created_at"),
        Index("idx_voice_intent_time", "intent", "created_at"),
    )


class ServiceOrder(Base):
    __tablename__ = "service_orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False, index=True)
    order_type = Column(String(32), nullable=False)  # repair, install, maintain, complaint
    priority = Column(String(16), default="normal")  # low, normal, high, urgent
    status = Column(String(16), default="pending", index=True)  # pending, processing, done, cancelled
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    resolved_at = Column(DateTime)

    device = relationship("Device", back_populates="service_orders")

    __table_args__ = (
        Index("idx_order_status_time", "status", "created_at"),
    )
