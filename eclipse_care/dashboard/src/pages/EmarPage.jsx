import React, { useState } from 'react';
import './EmarPage.css';
import {
  Pill, Clock, CheckCircle2, XCircle, PauseCircle,
  AlertTriangle, User, ChevronDown, ChevronRight, Info
} from 'lucide-react';

/* ─── Mock Data (mirrors backend API shape) ─────────────────────── */

const PATIENTS = [
  { id: 'PAT_VANCE', name: 'Eleanor Vance', room: '102' },
  { id: 'PAT_FINCH', name: 'Harold Finch', room: '204' },
];

const MOCK_DOSES = [
  {
    id: 'DOSE_001',
    schedule_id: 'MED_001',
    patient_id: 'PAT_VANCE',
    medication_name: 'Lisinopril',
    dosage: '10mg',
    route: 'PO',
    scheduled_time: '08:00',
    status: 'given',
    administered_by: 'RN Sarah Chen',
    administered_at: '2026-07-01T08:05:00',
    special_instructions: 'Monitor BP before administering',
    notes: 'BP 128/82 pre-admin',
  },
  {
    id: 'DOSE_002',
    schedule_id: 'MED_002',
    patient_id: 'PAT_FINCH',
    medication_name: 'Metformin',
    dosage: '500mg',
    route: 'PO',
    scheduled_time: '08:00',
    status: 'given',
    administered_by: 'RN Sarah Chen',
    administered_at: '2026-07-01T08:10:00',
    special_instructions: 'Take with meals',
    notes: '',
  },
  {
    id: 'DOSE_003',
    schedule_id: 'MED_002',
    patient_id: 'PAT_FINCH',
    medication_name: 'Metformin',
    dosage: '500mg',
    route: 'PO',
    scheduled_time: '18:00',
    status: 'pending',
    administered_by: null,
    administered_at: null,
    special_instructions: 'Take with meals',
    notes: '',
  },
  {
    id: 'DOSE_004',
    schedule_id: 'MED_003',
    patient_id: 'PAT_FINCH',
    medication_name: 'Donepezil',
    dosage: '5mg',
    route: 'PO',
    scheduled_time: '21:00',
    status: 'pending',
    administered_by: null,
    administered_at: null,
    special_instructions: 'For cognitive decline. Give at bedtime.',
    notes: '',
  },
];

/* ─── Status Helpers ─────────────────────────────────────────────── */

const STATUS_CONFIG = {
  pending: { label: 'Pending', color: '#f59e0b', Icon: Clock, bg: 'var(--warning-glow)' },
  given:   { label: 'Given',   color: '#10b981', Icon: CheckCircle2, bg: 'var(--emerald-glow)' },
  refused: { label: 'Refused', color: '#ef4444', Icon: XCircle, bg: 'var(--danger-glow)' },
  held:    { label: 'Held',    color: '#64748b', Icon: PauseCircle, bg: 'rgba(0,0,0,0.05)' },
  missed:  { label: 'Missed',  color: '#ef4444', Icon: AlertTriangle, bg: 'var(--danger-glow)' },
};

/* ─── Action Modal ───────────────────────────────────────────────── */

function ActionModal({ dose, onClose, onConfirm }) {
  const [action, setAction] = useState(null);
  const [reason, setReason] = useState('');

  function handleConfirm() {
    onConfirm(dose.id, action, reason);
    onClose();
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <Pill size={20} />
          <div>
            <h3>{dose.medication_name} {dose.dosage} ({dose.route})</h3>
            <p className="text-muted">Scheduled: {dose.scheduled_time}</p>
          </div>
        </div>

        {dose.special_instructions && (
          <div className="modal-instructions">
            <Info size={14} />
            <span>{dose.special_instructions}</span>
          </div>
        )}

        <div className="modal-actions">
          <button
            className={`action-btn given ${action === 'given' ? 'selected' : ''}`}
            onClick={() => setAction('given')}
          >
            <CheckCircle2 size={18} /> Given
          </button>
          <button
            className={`action-btn refused ${action === 'refused' ? 'selected' : ''}`}
            onClick={() => setAction('refused')}
          >
            <XCircle size={18} /> Refused
          </button>
          <button
            className={`action-btn held ${action === 'held' ? 'selected' : ''}`}
            onClick={() => setAction('held')}
          >
            <PauseCircle size={18} /> Held
          </button>
        </div>

        {(action === 'refused' || action === 'held') && (
          <div className="modal-reason">
            <label className="reason-label">
              Reason {action === 'refused' ? 'for refusal' : 'for holding'}
            </label>
            <textarea
              className="reason-textarea"
              placeholder={`Why was this dose ${action}?`}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              rows={2}
            />
          </div>
        )}

        <div className="modal-footer">
          <button className="cancel-btn" onClick={onClose}>Cancel</button>
          <button
            className="confirm-btn"
            disabled={!action || ((action === 'refused' || action === 'held') && !reason.trim())}
            onClick={handleConfirm}
          >
            Confirm
          </button>
        </div>
      </div>
    </div>
  );
}

/* ─── Patient Section ────────────────────────────────────────────── */

function PatientSection({ patient, doses, onAdminister }) {
  const [expanded, setExpanded] = useState(true);
  const pendingCount = doses.filter((d) => d.status === 'pending').length;

  return (
    <div className="patient-section bento-panel animate-in">
      <div className="patient-header" onClick={() => setExpanded(!expanded)}>
        <div className="patient-header-left">
          {expanded ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
          <User size={18} />
          <h3>{patient.name}</h3>
          <span className="patient-room">Room {patient.room}</span>
        </div>
        {pendingCount > 0 && (
          <span className="pending-badge">{pendingCount} Pending</span>
        )}
      </div>

      {expanded && (
        <div className="dose-table-wrapper">
          <table className="dose-table">
            <thead>
              <tr>
                <th>Time</th>
                <th>Medication</th>
                <th>Dosage</th>
                <th>Route</th>
                <th>Instructions</th>
                <th>Status</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {doses.map((dose) => {
                const cfg = STATUS_CONFIG[dose.status] || STATUS_CONFIG.pending;
                return (
                  <tr key={dose.id} className={`dose-row ${dose.status}`}>
                    <td className="time-cell">
                      <Clock size={14} />
                      <span>{dose.scheduled_time}</span>
                    </td>
                    <td className="med-name">{dose.medication_name}</td>
                    <td className="dosage-cell">{dose.dosage}</td>
                    <td className="route-cell">{dose.route}</td>
                    <td className="instructions-cell">
                      {dose.special_instructions || <span className="text-muted">—</span>}
                    </td>
                    <td>
                      <div className="status-chip" style={{ background: cfg.bg, color: cfg.color }}>
                        <cfg.Icon size={14} />
                        <span>{cfg.label}</span>
                      </div>
                    </td>
                    <td>
                      {dose.status === 'pending' ? (
                        <button
                          className="administer-btn"
                          onClick={() => onAdminister(dose)}
                        >
                          Administer
                        </button>
                      ) : (
                        <span className="administered-by">
                          {dose.administered_by || '—'}
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

/* ─── Main Page ──────────────────────────────────────────────────── */

export default function EmarPage() {
  const [doses, setDoses] = useState(MOCK_DOSES);
  const [modalDose, setModalDose] = useState(null);

  function handleAdminister(doseId, action, reason) {
    setDoses((prev) =>
      prev.map((d) =>
        d.id === doseId
          ? {
              ...d,
              status: action,
              administered_by: 'RN Jane Smith',
              administered_at: new Date().toISOString(),
              ...(action === 'refused' ? { notes: `Refused: ${reason}` } : {}),
              ...(action === 'held' ? { notes: `Held: ${reason}` } : {}),
            }
          : d
      )
    );
  }

  const pendingTotal = doses.filter((d) => d.status === 'pending').length;
  const givenTotal = doses.filter((d) => d.status === 'given').length;

  return (
    <div className="emar-page">
      {/* Summary Bar */}
      <div className="emar-summary-bar bento-panel animate-in">
        <div className="emar-stat">
          <span className="emar-stat-value">{doses.length}</span>
          <span className="emar-stat-label">Total Doses</span>
        </div>
        <div className="emar-stat">
          <span className="emar-stat-value text-emerald">{givenTotal}</span>
          <span className="emar-stat-label">Administered</span>
        </div>
        <div className="emar-stat">
          <span className="emar-stat-value text-warning">{pendingTotal}</span>
          <span className="emar-stat-label">Pending</span>
        </div>
      </div>

      {/* Patient Sections */}
      {PATIENTS.map((patient, idx) => (
        <PatientSection
          key={patient.id}
          patient={patient}
          doses={doses.filter((d) => d.patient_id === patient.id)}
          onAdminister={(dose) => setModalDose(dose)}
        />
      ))}

      {/* Action Modal */}
      {modalDose && (
        <ActionModal
          dose={modalDose}
          onClose={() => setModalDose(null)}
          onConfirm={handleAdminister}
        />
      )}
    </div>
  );
}
