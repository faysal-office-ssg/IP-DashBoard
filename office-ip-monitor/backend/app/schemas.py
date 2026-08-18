from __future__ import annotations

from datetime import datetime
from ipaddress import ip_address
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

DeviceStatus = Literal["online", "offline", "unknown"]


class DeviceBase(BaseModel):
    device_name: str = Field(..., min_length=1, max_length=255)
    user_name: str = Field(..., min_length=1, max_length=255)
    ip_address: str = Field(..., min_length=7, max_length=64)
    location_or_point: str = Field(..., min_length=1, max_length=255)
    notes: Optional[str] = Field(default=None, max_length=1000)
    is_active: bool = True

    @field_validator("device_name", "user_name", "location_or_point")
    @classmethod
    def clean_string(cls, value: str) -> str:
        return value.strip()

    @field_validator("ip_address")
    @classmethod
    def validate_ip(cls, value: str) -> str:
        try:
            parsed = ip_address(value.strip())
        except ValueError as exc:
            raise ValueError("Invalid IP address format") from exc
        return str(parsed)


class DeviceCreate(DeviceBase):
    pass


class DeviceUpdate(BaseModel):
    device_name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    user_name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    ip_address: Optional[str] = Field(default=None, min_length=7, max_length=64)
    location_or_point: Optional[str] = Field(default=None, min_length=1, max_length=255)
    notes: Optional[str] = Field(default=None, max_length=1000)
    is_active: Optional[bool] = None
    status: Optional[DeviceStatus] = None
    last_ping_at: Optional[datetime] = None
    last_response_ms: Optional[int] = None
    down_since: Optional[datetime] = None

    @field_validator("device_name", "user_name", "location_or_point")
    @classmethod
    def clean_string(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()

    @field_validator("ip_address")
    @classmethod
    def validate_ip(cls, value: str | None) -> str | None:
        if value is None:
            return None
        try:
            parsed = ip_address(value.strip())
        except ValueError as exc:
            raise ValueError("Invalid IP address format") from exc
        return str(parsed)


class DeviceOut(DeviceBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: DeviceStatus = "unknown"
    last_ping_at: Optional[datetime] = None
    last_response_ms: Optional[int] = None
    down_since: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class DeviceSummary(BaseModel):
    total_devices: int
    online_count: int
    offline_count: int
    unknown_count: int


class MonitoringConfig(BaseModel):
    monitor_interval_seconds: int = Field(default=10, ge=5, le=300)


class PingResult(BaseModel):
    device_id: int
    status: DeviceStatus
    online: bool
    response_ms: Optional[int] = None
    last_ping_at: Optional[datetime] = None
    down_since: Optional[datetime] = None
    message: str
