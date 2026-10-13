# Eclipse Care — Elderly Monitoring Platform

> Gateway-first elderly care monitoring for nursing homes, assisted living, and long-term care facilities.

## Architecture

```
[Wearable Band] --BLE--> [Gateway (Raspberry Pi)] --MQTT/HTTPS--> [Cloud Server] --> [Admin Dashboard]
                                |                                        |
                          Edge Processing                          Alert Engine
                          Fall Detection                         Hospital FHIR
                          Vital Alerts                          Family Notify
                          Local SQLite                           TimescaleDB
```

## Project Structure

```
eclipse_care/
├── gateway/              # Runs on Raspberry Pi / edge device
│   ├── ble/              # BLE scanner + protocol decoder
│   ├── edge/             # Edge processing (vitals, falls, alerts)
│   ├── store/            # Local SQLite storage (offline-first)
│   ├── sync/             # Cloud uploader (MQTT + REST)
│   ├── config/           # Gateway configuration
│   └── main.py           # Gateway entry point
│
├── cloud/                # Cloud server (FastAPI + TimescaleDB)
│   ├── api/              # REST API for dashboard + hospital
│   ├── alerts/           # Alert engine + notification dispatch
│   ├── db/               # Database schema + migrations
│   ├── export/           # Data export (CSV, PDF, FHIR, HL7)
│   ├── hospital/         # Hospital integration (FHIR)
│   └── main.py           # Cloud server entry point
│
├── dashboard/            # Admin web dashboard
│   ├── index.html
│   ├── css/
│   └── js/
│
├── references/           # WHOOP BLE protocol reference (read-only)
│   └── whoop_protocol.json
│
├── docker-compose.yml    # Full stack deployment
├── requirements.txt      # Python dependencies
└── README.md
```

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run gateway (on Raspberry Pi)
python -m gateway.main

# 3. Run cloud server
docker-compose up -d

# 4. Open dashboard
open http://localhost:8080
```

## Key Design Decisions

1. **Gateway-first**: All processing happens at the edge. Cloud is for persistence + dashboard.
2. **Offline-first**: Gateway stores data locally in SQLite. Syncs when internet is available.
3. **Alert at the edge**: Fall detection and vital alerts trigger IMMEDIATELY on the gateway — no cloud round-trip.
4. **No iOS app**: Wearable → Gateway → Cloud → Web Dashboard. No phone needed.
5. **WHOOP as reference only**: BLE protocol knowledge from WHOOP reverse engineering. All code is original.
