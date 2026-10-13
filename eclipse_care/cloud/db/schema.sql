-- Eclipse Care: HIPAA-Compliant TimescaleDB Schema
-- Strict segmentation of PHI and Telemetry.

CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ==========================================
-- SCHEMA: PHI (Protected Health Information)
-- ==========================================
CREATE SCHEMA IF NOT EXISTS phi;

CREATE TABLE phi.facilities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    address TEXT,
    timezone VARCHAR(50) DEFAULT 'UTC',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE phi.patients (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    facility_id UUID REFERENCES phi.facilities(id),
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    dob DATE,
    room_number VARCHAR(50),
    wearable_mac_address VARCHAR(50) UNIQUE, -- Maps telemetry to patient
    baseline_hr_bpm INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE phi.caregivers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    facility_id UUID REFERENCES phi.facilities(id),
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    phone_number VARCHAR(20),
    shift_start TIME,
    shift_end TIME,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Physical Edge Gateways mapped to Facility Zones
CREATE TABLE phi.gateways (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    facility_id UUID REFERENCES phi.facilities(id),
    mac_address VARCHAR(50) UNIQUE NOT NULL,
    location_name VARCHAR(100) NOT NULL, -- e.g., "Front Exit", "Garden Door"
    is_exit BOOLEAN DEFAULT FALSE,       -- Flags for Elopement Detection
    created_at TIMESTAMPTZ DEFAULT NOW()
);


-- ==========================================
-- SCHEMA: TELEMETRY (High Volume, No direct PHI)
-- ==========================================
CREATE SCHEMA IF NOT EXISTS telemetry;

-- Real-Time Location (RSSI Proximity) Hypertables
CREATE TABLE telemetry.location_rssi (
    time TIMESTAMPTZ NOT NULL,
    device_id VARCHAR(50) NOT NULL,
    gateway_id VARCHAR(50) NOT NULL,
    rssi INTEGER NOT NULL
);
SELECT create_hypertable('telemetry.location_rssi', 'time');
CREATE INDEX ix_device_time_loc ON telemetry.location_rssi (device_id, time DESC);

-- Heart Rate Hypertables
CREATE TABLE telemetry.heart_rate (
    time TIMESTAMPTZ NOT NULL,
    device_id VARCHAR(50) NOT NULL, -- FK to phi.patients.wearable_mac_address (handled at app level)
    gateway_id VARCHAR(50) NOT NULL,
    bpm INTEGER NOT NULL,
    confidence INTEGER
);

-- Convert to TimescaleDB Hypertable partitioned by time
SELECT create_hypertable('telemetry.heart_rate', 'time');
-- Create an index for quick device lookups over time ranges
CREATE INDEX ix_device_time_hr ON telemetry.heart_rate (device_id, time DESC);


-- IMU Activity Hypertables (Aggregated, not raw 50Hz to save space)
CREATE TABLE telemetry.activity_summary (
    time TIMESTAMPTZ NOT NULL,
    device_id VARCHAR(50) NOT NULL,
    gateway_id VARCHAR(50) NOT NULL,
    avg_movement_g DOUBLE PRECISION,
    is_worn BOOLEAN DEFAULT TRUE
);
SELECT create_hypertable('telemetry.activity_summary', 'time');
CREATE INDEX ix_device_time_act ON telemetry.activity_summary (device_id, time DESC);


-- ==========================================
-- SCHEMA: ALERTS (Incident Tracking)
-- ==========================================
CREATE SCHEMA IF NOT EXISTS incidents;

CREATE TABLE incidents.alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    time TIMESTAMPTZ NOT NULL,
    device_id VARCHAR(50) NOT NULL,
    alert_type VARCHAR(50) NOT NULL, -- e.g., FALL_DETECTED, HR_ANOMALY
    severity VARCHAR(20) NOT NULL,   -- e.g., warning, critical, emergency
    message TEXT,
    
    -- LLM Hybrid Rule Engine Fields
    llm_suppressed BOOLEAN DEFAULT FALSE,
    llm_reasoning TEXT,
    
    status VARCHAR(20) DEFAULT 'new', -- new, acknowledged, resolved
    acknowledged_by UUID REFERENCES phi.caregivers(id),
    acknowledged_at TIMESTAMPTZ
);
-- Optional: partition alerts if volume gets high, but usually standard table is fine.
CREATE INDEX ix_alerts_time ON incidents.alerts (time DESC);
CREATE INDEX ix_alerts_device ON incidents.alerts (device_id, time DESC);


-- ==========================================
-- SCHEMA: AUDIT (HIPAA Compliance)
-- ==========================================
CREATE SCHEMA IF NOT EXISTS audit;

CREATE TABLE audit.access_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    time TIMESTAMPTZ DEFAULT NOW(),
    user_id UUID NOT NULL, -- The caregiver or API client
    action VARCHAR(100) NOT NULL, -- e.g., VIEW_PATIENT_RECORD, ACKNOWLEDGE_ALERT
    resource_type VARCHAR(50),
    resource_id UUID,
    ip_address VARCHAR(50)
);
CREATE INDEX ix_audit_time ON audit.access_logs (time DESC);


-- ==========================================
-- SCHEMA: CLINICAL (Care Management)
-- ==========================================
CREATE SCHEMA IF NOT EXISTS clinical;

-- Sleep Quality Summaries (nightly from Edge Gateway)
CREATE TABLE clinical.sleep_summaries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id VARCHAR(50) NOT NULL,
    night_date DATE NOT NULL,
    total_sleep_min DOUBLE PRECISION,
    deep_sleep_min DOUBLE PRECISION,
    disturbance_count INTEGER,
    sleep_efficiency_pct DOUBLE PRECISION,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX ix_sleep_device_date ON clinical.sleep_summaries (device_id, night_date DESC);

-- ADL Daily Summaries (from Edge Gateway)
CREATE TABLE clinical.adl_summaries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id VARCHAR(50) NOT NULL,
    summary_date DATE NOT NULL,
    resting_min DOUBLE PRECISION DEFAULT 0,
    walking_min DOUBLE PRECISION DEFAULT 0,
    eating_min DOUBLE PRECISION DEFAULT 0,
    bathing_min DOUBLE PRECISION DEFAULT 0,
    sleeping_min DOUBLE PRECISION DEFAULT 0,
    active_min DOUBLE PRECISION DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX ix_adl_device_date ON clinical.adl_summaries (device_id, summary_date DESC);

-- SBAR Shift Handoff Records
CREATE TABLE clinical.shift_handoffs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    facility_id UUID REFERENCES phi.facilities(id),
    outgoing_nurse_id UUID REFERENCES phi.caregivers(id),
    incoming_nurse_id UUID REFERENCES phi.caregivers(id),
    shift_start TIMESTAMPTZ NOT NULL,
    shift_end TIMESTAMPTZ NOT NULL,
    handoff_data JSONB NOT NULL,       -- Full SBAR structured data
    general_notes TEXT,
    submitted_at TIMESTAMPTZ DEFAULT NOW()
);

-- eMAR Medication Schedules
CREATE TABLE clinical.medication_schedules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID REFERENCES phi.patients(id),
    medication_name VARCHAR(255) NOT NULL,
    dosage VARCHAR(50) NOT NULL,
    route VARCHAR(20) DEFAULT 'PO',
    frequency VARCHAR(20) NOT NULL,    -- QD, BID, TID, QHS, PRN
    scheduled_times TEXT[],            -- e.g., {'08:00', '20:00'}
    special_instructions TEXT,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- eMAR Dose Administration Records
CREATE TABLE clinical.dose_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    schedule_id UUID REFERENCES clinical.medication_schedules(id),
    patient_id UUID REFERENCES phi.patients(id),
    scheduled_time TIME NOT NULL,
    dose_date DATE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending, given, refused, held, missed
    administered_by UUID REFERENCES phi.caregivers(id),
    administered_at TIMESTAMPTZ,
    hold_reason TEXT,
    refuse_reason TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX ix_dose_patient_date ON clinical.dose_records (patient_id, dose_date DESC);

