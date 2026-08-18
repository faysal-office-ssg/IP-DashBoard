# Office IP Monitor

Office IP Monitor is a local network device monitoring dashboard for offices with multiple branches or work points. It allows you to track whether each device/IP is online, show recent response times, and quickly take action on devices that go offline.

## Prerequisites

- Python 3.10+
- Windows 10/11 or a Unix-like environment for local development
- A local browser
- Internet access is not required for basic local network monitoring

## Important network note

ICMP ping may be blocked on some devices or network policies even when the internet or LAN is working normally. This means a device can appear offline even when the service is reachable on the network. The project is designed so future TCP checks such as port 80 or 443 can be added easily without changing the dashboard design.

## Project structure

- office-ip-monitor/
  - backend/
  - frontend/
  - README.md

## Installation steps

1. Open a terminal in the project folder.
2. Go into the backend folder.
3. Create a virtual environment if you want a clean setup.
4. Install the backend dependencies.

Example:

```bash
cd office-ip-monitor/backend
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Backend start command

From the backend folder:

```bash
uvicorn app.main:app --reload --port 8000
```

On Windows PowerShell, it is also fine to run:

```powershell
cd office-ip-monitor/backend
.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
```

The API documentation is available at:

- http://localhost:8000/docs

## Frontend start command

From the project root or the frontend folder:

```bash
cd office-ip-monitor/frontend
python -m http.server 5500
```

Then open:

- http://localhost:5500

## How to add devices

1. Open the dashboard.
2. Click the Add Device button.
3. Fill in:
   - device name
   - user name
   - IP address
   - location or point
   - optional notes
   - enable/disable monitoring
4. Save the device.
5. The backend will start monitoring active devices automatically every 10 seconds.

## API overview

Core endpoints:

- GET /api/devices
- GET /api/devices/{id}
- POST /api/devices
- PUT /api/devices/{id}
- DELETE /api/devices/{id}
- GET /api/dashboard/summary
- POST /api/devices/{id}/ping
- GET /api/monitoring/config
- PUT /api/monitoring/config

Swagger UI is available at /docs for interactive testing.

## Database location

The SQLite database is created in the backend folder as:

- office-ip-monitor/backend/office_ip_monitor.db

## Windows-specific ping notes

On Windows, ping is usually available through the built-in `ping` command. Some environments or security policies block ICMP packets, which may cause devices to appear as offline even when they are responding to other network services or traffic. If you need broader health checks, a future improvement is to add TCP connectivity checks against ports like 80 or 443.

## Demo data

If the database is empty, the app creates a few demo devices automatically so the dashboard is usable right away.
