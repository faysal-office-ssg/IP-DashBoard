import os
from contextlib import asynccontextmanager
from datetime import datetime

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.models import Device
from app.monitor import ping_device_once, start_background_monitoring
from app.schemas import DeviceCreate, DeviceOut, DeviceSummary, DeviceUpdate, MonitoringConfig, PingResult

load_dotenv()

APP_TITLE = os.getenv("APP_TITLE", "Office IP Monitor")
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
FRONTEND_ORIGINS = [
    origin.strip()
    for origin in os.getenv("FRONTEND_ORIGINS", "http://localhost:5500,http://127.0.0.1:5500").split(",")
    if origin.strip()
]


def seed_demo_devices(db: Session):
    if db.query(Device).count() > 0:
        return

    demo_devices = [
        {
            "device_name": "Main Router",
            "user_name": "IT Admin",
            "ip_address": "192.168.1.1",
            "location_or_point": "Head Office",
            "notes": "Primary network gateway",
            "is_active": True,
            "status": "unknown",
        },
        {
            "device_name": "Reception PC",
            "user_name": "Reception",
            "ip_address": "192.168.1.12",
            "location_or_point": "Reception Desk",
            "notes": "Shared workstation",
            "is_active": True,
            "status": "unknown",
        },
        {
            "device_name": "Branch Printer",
            "user_name": "Operations",
            "ip_address": "192.168.1.30",
            "location_or_point": "Branch A",
            "notes": "Office printer",
            "is_active": True,
            "status": "unknown",
        },
    ]

    for item in demo_devices:
        db.add(Device(**item))
    db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    with next(get_db()) as db:
        seed_demo_devices(db)
    await start_background_monitoring()
    yield


app = FastAPI(title=APP_TITLE, version=APP_VERSION, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {"status": "ok", "service": APP_TITLE, "timestamp": datetime.utcnow().isoformat()}


@app.get("/api/devices", response_model=list[DeviceOut])
def get_devices(db: Session = Depends(get_db)):
    return db.query(Device).order_by(Device.created_at.desc()).all()


@app.get("/api/devices/{device_id}", response_model=DeviceOut)
def get_device(device_id: int, db: Session = Depends(get_db)):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    return device


@app.post("/api/devices", response_model=DeviceOut, status_code=status.HTTP_201_CREATED)
def create_device(payload: DeviceCreate, db: Session = Depends(get_db)):
    duplicate = db.query(Device).filter(Device.ip_address == payload.ip_address).first()
    if duplicate:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A device with this IP address already exists")

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


@app.put("/api/devices/{device_id}", response_model=DeviceOut)
def update_device(device_id: int, payload: DeviceUpdate, db: Session = Depends(get_db)):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")

    updates = payload.model_dump(exclude_unset=True)
    if "ip_address" in updates and updates["ip_address"] is not None:
        duplicate = db.query(Device).filter(Device.ip_address == updates["ip_address"], Device.id != device_id).first()
        if duplicate:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Another device already uses this IP address")

    for field, value in updates.items():
        setattr(device, field, value)
    device.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(device)
    return device


@app.delete("/api/devices/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_device(device_id: int, db: Session = Depends(get_db)):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    db.delete(device)
    db.commit()
    return None


@app.get("/api/dashboard/summary", response_model=DeviceSummary)
def dashboard_summary(db: Session = Depends(get_db)):
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


@app.post("/api/devices/{device_id}/ping", response_model=PingResult)
async def ping_device(device_id: int, db: Session = Depends(get_db)):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")

    result = await ping_device_once(device_id)
    return PingResult(
        device_id=device_id,
        status=result["status"],
        online=result["online"],
        response_ms=result["response_ms"],
        last_ping_at=result.get("last_ping_at"),
        down_since=result.get("down_since"),
        message=result["message"],
    )


@app.get("/api/monitoring/config", response_model=MonitoringConfig)
def get_monitoring_config():
    return MonitoringConfig(monitor_interval_seconds=int(os.getenv("MONITOR_INTERVAL_SECONDS", "10")))


@app.put("/api/monitoring/config", response_model=MonitoringConfig)
def update_monitoring_config(payload: MonitoringConfig):
    os.environ["MONITOR_INTERVAL_SECONDS"] = str(payload.monitor_interval_seconds)
    import app.monitor as monitor
    monitor.MONITOR_INTERVAL_SECONDS = payload.monitor_interval_seconds
    return payload


@app.get("/")
def root():
    return {"message": "Office IP Monitor API is running"}


@app.on_event("startup")
def startup_event():
    Base.metadata.create_all(bind=engine)
    import app.monitor as monitor
    monitor.MONITOR_INTERVAL_SECONDS = int(os.getenv("MONITOR_INTERVAL_SECONDS", "10"))
