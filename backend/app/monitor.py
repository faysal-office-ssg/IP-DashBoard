import asyncio
import os
import platform
import re
import subprocess
from datetime import datetime

from app.database import SessionLocal
from app.models import Device


MONITOR_INTERVAL_SECONDS = int(os.getenv("MONITOR_INTERVAL_SECONDS", "10"))


def get_monitor_interval_seconds():
    return int(os.getenv("MONITOR_INTERVAL_SECONDS", str(MONITOR_INTERVAL_SECONDS)))


def get_ping_command(ip_address: str):
    system = platform.system().lower()
    if system == "windows":
        return ["ping", "-n", "1", "-w", "1500", ip_address]
    if system == "linux":
        return ["ping", "-c", "1", "-W", "1", ip_address]
    return ["ping", "-c", "1", ip_address]


def extract_ping_response_ms(output: str):
    if not output:
        return None

    patterns = [
        r"time[<= ]+(\d+(?:\.\d+)?)\s*ms",
        r"rtt\s+min/avg/max.*?=\s*\d+(?:\.\d+)?/\s*(\d+(?:\.\d+)?)/\d+(?:\.\d+)?/\d+(?:\.\d+)?\s*ms",
        r"avg\s*=\s*(\d+(?:\.\d+)?)\s*ms",
    ]

    for pattern in patterns:
        match = re.search(pattern, output, re.IGNORECASE)
        if match:
            try:
                return int(float(match.group(1)))
            except (TypeError, ValueError):
                continue
    return None


def ping_ip(ip_address: str):
    if not re.fullmatch(r"[0-9a-fA-F:.]+", ip_address.strip()):
        return False, None, "network label cannot be pinged"

    command = get_ping_command(ip_address)
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=4,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False, None, "ping command unavailable"

    output = (result.stdout or "") + (result.stderr or "")
    success = result.returncode == 0
    response_ms = extract_ping_response_ms(output)

    return success, response_ms, output.strip() or ("ping succeeded" if success else "ping failed")


def ping_device_once(device_id: int):
    db = SessionLocal()
    try:
        device = db.query(Device).filter(Device.id == device_id).first()
        if not device:
            return {"device_id": device_id, "status": "unknown", "online": False, "message": "device not found"}

        if not device.is_active:
            device.status = "unknown"
            device.updated_at = datetime.utcnow()
            db.commit()
            return {
                "device_id": device.id,
                "status": "unknown",
                "online": False,
                "response_ms": None,
                "last_ping_at": device.last_ping_at,
                "down_since": device.down_since,
                "message": "device disabled from monitoring",
            }

        online, response_ms, message = ping_ip(device.ip_address)
        now = datetime.utcnow()
        device.last_ping_at = now
        device.last_response_ms = response_ms

        if message == "network label cannot be pinged":
            device.status = "unknown"
            device.down_since = None
        elif online:
            device.status = "online"
            device.down_since = None
        else:
            device.status = "offline"
            if device.down_since is None:
                device.down_since = now

        device.updated_at = now
        db.commit()
        db.refresh(device)
        return {
            "device_id": device.id,
            "status": device.status,
            "online": online,
            "response_ms": response_ms,
            "last_ping_at": device.last_ping_at,
            "down_since": device.down_since,
            "message": message,
        }
    finally:
        db.close()


async def monitor_active_devices():
    while True:
        await asyncio.sleep(get_monitor_interval_seconds())
        db = SessionLocal()
        try:
            devices = db.query(Device).filter(Device.is_active.is_(True)).all()
            semaphore = asyncio.Semaphore(20)

            async def check_device(device):
                async with semaphore:
                    return await asyncio.to_thread(ping_ip, device.ip_address)

            results = await asyncio.gather(*(check_device(device) for device in devices))
            now = datetime.utcnow()
            for device, (online, response_ms, message) in zip(devices, results):
                device.last_ping_at = now
                device.last_response_ms = response_ms

                if message == "network label cannot be pinged":
                    device.status = "unknown"
                    device.down_since = None
                elif online:
                    device.status = "online"
                    device.down_since = None
                else:
                    device.status = "offline"
                    if device.down_since is None:
                        device.down_since = now

                device.updated_at = now
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()


async def start_background_monitoring():
    if getattr(start_background_monitoring, "running", False):
        return
    start_background_monitoring.running = True
    asyncio.create_task(monitor_active_devices())
