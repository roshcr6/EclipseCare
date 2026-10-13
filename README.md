# EclipseCare — Customizable Wearable Technology for Elderly Care

> **Design Thinking and Engineering — Team 2**
>
> An edge-first wearable monitoring platform designed to adapt wearable technology for elderly care environments.

---

## 📌 Project Overview

**EclipseCare** is a software platform that explores how wearable technology can be made more adaptable for elderly users in care environments such as nursing homes and assisted living facilities.

The project originated from a real-world observation: existing consumer wearables (like WHOOP) offer limited customization for users with specific health monitoring needs — particularly elderly individuals. EclipseCare proposes a software layer that bridges off-the-shelf wearable hardware with customizable monitoring, alerting, and reporting features tailored for care settings.

---

## 👥 Team Members

| Name | Role |
|---|---|
| **Roshith Robert** | Idea Initiation & Initial Software Prototype |
| **Zakiel Chungath** | Feature Enhancement & Further Development |
| **Sanjay Varghese** | Testing & Evaluation |
| **Riyan Raz** | Project Proposal & Presentation |

---

## 🗂️ Repository Structure

```
EclipseCare/
│
├── eclipse_care/              # Core backend platform (Python)
│   ├── gateway/               # Edge device software (Raspberry Pi)
│   │   ├── ble/               # BLE scanner & protocol decoder
│   │   ├── edge/              # Edge processing: fall detection, vital alerts
│   │   ├── store/             # Local SQLite storage (offline-first)
│   │   ├── sync/              # Cloud synchronisation (MQTT + REST)
│   │   ├── config/            # Gateway configuration
│   │   └── main.py            # Gateway entry point
│   │
│   ├── cloud/                 # Cloud server (FastAPI + TimescaleDB)
│   │   ├── api/               # REST API for dashboard & hospital integration
│   │   ├── db/                # Database schema & migrations
│   │   └── main.py            # Cloud server entry point
│   │
│   ├── dashboard/             # Admin web dashboard (HTML/CSS/JS)
│   ├── tests/                 # Simulation & unit tests
│   ├── requirements.txt       # Python dependencies
│   └── README.md              # Platform-specific documentation
│
├── eclipse-prototype/         # Frontend UI prototype (React + Vite)
│   ├── src/                   # React components and application logic
│   ├── public/                # Static assets
│   ├── index.html             # Entry point
│   └── package.json           # Node.js dependencies
│
└── README.md                  # This file
```

---

## 🏗️ System Architecture

```
[Wearable Band] --BLE--> [Gateway (Raspberry Pi)] --MQTT/HTTPS--> [Cloud Server] --> [Admin Dashboard]
                                |                                        |
                          Edge Processing                          Alert Engine
                          Fall Detection                          Hospital FHIR
                          Vital Alerts                            Family Notify
                          Local SQLite                            TimescaleDB
```

**Key design decisions:**

1. **Gateway-first**: All critical processing happens at the edge. Cloud is used for persistence and the dashboard only.
2. **Offline-first**: The gateway stores data locally in SQLite and syncs when internet is available.
3. **Alert at the edge**: Fall detection and vital alerts trigger immediately on the gateway — no cloud round-trip required.
4. **No phone dependency**: Data flows directly from Wearable → Gateway → Cloud → Web Dashboard.
5. **Adaptable software layer**: The platform is designed to be customizable for different care settings and monitoring requirements.

---

## ⚙️ Getting Started

### Backend (Python Gateway + Cloud)

```bash
# 1. Clone the repository
git clone https://github.com/roshcr6/EclipseCare.git
cd EclipseCare

# 2. Install Python dependencies
pip install -r eclipse_care/requirements.txt

# 3. Run the gateway (on Raspberry Pi or local machine)
cd eclipse_care
python -m gateway.main

# 4. Run the cloud server
docker-compose -f eclipse_care/docker-compose.yml up -d

# 5. Open the dashboard
open http://localhost:8080
```

### Frontend Prototype (React + Vite)

```bash
cd eclipse-prototype
npm install
npm run dev
```

---

## 🧪 Testing

Test files are located in `eclipse_care/tests/`:

```bash
cd eclipse_care
python -m pytest tests/
```

---

## 📄 Report

The individual contribution report (`Team_2_Personal_Project_Contribution_Report.docx`) is included in this repository and documents the personal contributions of each team member, the origin of the project idea, and the design thinking process applied throughout the project.

---

## 📚 Subject

**Design Thinking and Engineering** — Team 2

---

## ⚠️ Disclaimer

This project uses BLE protocol knowledge for educational purposes. All implementation code is original work developed for this academic project.
# EclipseCare
