from datetime import datetime

from sqlalchemy.orm import Session

from app.models import Device
from app.schemas import DeviceCreate, DeviceSummary, DeviceUpdate


def get_devices(db: Session):
    return db.query(Device).order_by(Device.created_at.desc()).all()


def get_device_by_id(db: Session, device_id: int):
    return db.query(Device).filter(Device.id == device_id).first()


def create_device(db: Session, payload: DeviceCreate):
    device = Device(
        device_name=payload.device_name,
        user_name=payload.user_name,
        ip_address=payload.ip_address,
        location_or_point=payload.location_or_point,
        notes=payload.notes,
        is_active=payload.is_active,
        status="unknown",
    )
    db.add(device)
    db.commit()
    db.refresh(device)
    return device


def update_device(db: Session, device: Device, payload: DeviceUpdate):
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(device, field, value)
    device.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(device)
    return device


def delete_device(db: Session, device: Device):
    db.delete(device)
    db.commit()
    return True


def get_dashboard_summary(db: Session):
    total_devices = db.query(Device).count()
    online_count = db.query(Device).filter(Device.status == "online").count()
    offline_count = db.query(Device).filter(Device.status == "offline").count()
    unknown_count = db.query(Device).filter(Device.status == "unknown").count()
    return DeviceSummary(
        total_devices=total_devices,
        online_count=online_count,
        offline_count=offline_count,
        unknown_count=unknown_count,
    )
