import React, { useState } from 'react';
import './HandoffPage.css';
import {
  ClipboardList, AlertTriangle, Heart, Wind, Activity,
  Moon, Send, ChevronDown, ChevronUp, Clock, User, FileText
} from 'lucide-react';

/* ─── Mock Data (mirrors backend API shape) ─────────────────────── */
const MOCK_HANDOFF = {
  facility_id: 'FAC_001',
  outgoing_nurse: 'RN Sarah Chen',
  incoming_nurse: '',
  shift_start: '2026-07-01T07:00:00',
  shift_end: '2026-07-01T19:00:00',
  residents: [
    {
      resident_name: 'Eleanor Vance',
      room: '102',
      situation_alerts: ['FALL_DETECTED (09:14 — AI confidence 92%)'],
      situation_summary:
        'Fall detected at 09:14. Resident was assisted. No visible injury. Vitals stable post-fall.',
      background_baseline_hr: 68,
      background_conditions: ['Dementia (mild)', 'Osteoporosis'],
      assessment_current_hr: 72,
      assessment_current_spo2: 96.0,
      assessment_adl_state: 'resting',
      assessment_sleep_quality: 'Good (6.2h, 1 disturbance)',
      recommendation: '',
    },
    {
      resident_name: 'Harold Finch',
      room: '204',
      situation_alerts: [
        'PREDICTIVE_UTI_RISK (03:00 — bathroom visits +42%)',
        'HR_ANOMALY (14:30 — 89 bpm vs 62 bpm baseline)',
      ],
      situation_summary:
        'Predictive engine flagged UTI risk. HR trending upward. Appetite reduced at lunch.',
      background_baseline_hr: 62,
      background_conditions: ['Type 2 Diabetes', 'History of recurrent UTI'],
      assessment_current_hr: 85,
      assessment_current_spo2: 94.0,
      assessment_adl_state: 'resting',
      assessment_sleep_quality: 'Poor (4.1h, 5 disturbances)',
      recommendation: '',
    },
  ],
};

/* ─── Helpers ────────────────────────────────────────────────────── */
function formatTime(iso) {
  return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}
function formatDate(iso) {
  return new Date(iso).toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' });
}

/* ─── Sub-components ─────────────────────────────────────────────── */

function SBARSection({ label, icon: Icon, color, children }) {
  return (
    <div className="sbar-section">
      <div className="sbar-section-header" style={{ borderLeftColor: color }}>
        <Icon size={16} style={{ color }} />
        <span className="sbar-label">{label}</span>
      </div>
      <div className="sbar-section-body">{children}</div>
    </div>
  );
}

function ResidentCard({ resident, index, onRecChange }) {
  const [expanded, setExpanded] = useState(true);
  const hasAlerts = resident.situation_alerts.length > 0;

  return (
    <div
      className={`resident-handoff-card animate-in ${hasAlerts ? 'has-alerts' : ''}`}
      style={{ animationDelay: `${0.1 + index * 0.12}s` }}
    >
      {/* Card Header */}
      <div className="card-header" onClick={() => setExpanded(!expanded)}>
        <div className="card-header-left">
          <div className="room-badge">Rm {resident.room}</div>
          <h3 className="card-resident-name">{resident.resident_name}</h3>
          {hasAlerts && (
            <span className="alert-count-badge">
              <AlertTriangle size={12} /> {resident.situation_alerts.length}
            </span>
          )}
        </div>
        <button className="expand-btn">
          {expanded ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
        </button>
      </div>

      {/* SBAR Content */}
      {expanded && (
        <div className="sbar-content">
          {/* S — Situation */}
          <SBARSection label="Situation" icon={AlertTriangle} color="#ef4444">
            {resident.situation_alerts.length > 0 ? (
              <ul className="alert-list-sbar">
                {resident.situation_alerts.map((a, i) => (
                  <li key={i} className="alert-item">{a}</li>
                ))}
              </ul>
            ) : (
              <p className="no-events">No alerts this shift.</p>
            )}
            {resident.situation_summary && (
              <p className="situation-summary">{resident.situation_summary}</p>
            )}
          </SBARSection>

          {/* B — Background */}
          <SBARSection label="Background" icon={FileText} color="#3b82f6">
            <div className="background-grid">
              <div className="bg-item">
                <span className="bg-label">Baseline HR</span>
                <span className="bg-value">{resident.background_baseline_hr} bpm</span>
              </div>
              <div className="bg-item">
                <span className="bg-label">Conditions</span>
                <span className="bg-value">
                  {resident.background_conditions.join(', ') || 'None documented'}
                </span>
              </div>
            </div>
          </SBARSection>

          {/* A — Assessment */}
          <SBARSection label="Assessment" icon={Activity} color="#10b981">
            <div className="assessment-grid">
              <div className="assess-metric">
                <Heart size={16} className="metric-icon hr" />
                <div>
                  <span className="metric-value">{resident.assessment_current_hr} bpm</span>
                  <span className="metric-label">Heart Rate</span>
                </div>
              </div>
              <div className="assess-metric">
                <Wind size={16} className="metric-icon spo2" />
                <div>
                  <span className="metric-value">{resident.assessment_current_spo2}%</span>
                  <span className="metric-label">SpO2</span>
                </div>
              </div>
              <div className="assess-metric">
                <Activity size={16} className="metric-icon adl" />
                <div>
                  <span className="metric-value capitalize">{resident.assessment_adl_state}</span>
                  <span className="metric-label">ADL State</span>
                </div>
              </div>
              <div className="assess-metric">
                <Moon size={16} className="metric-icon sleep" />
                <div>
                  <span className="metric-value">{resident.assessment_sleep_quality || 'N/A'}</span>
                  <span className="metric-label">Sleep Quality</span>
                </div>
              </div>
            </div>
          </SBARSection>

          {/* R — Recommendation (editable) */}
          <SBARSection label="Recommendation (Watch For)" icon={ClipboardList} color="#f59e0b">
            <textarea
              className="rec-textarea"
              placeholder="Type your recommendation for the incoming nurse..."
              value={resident.recommendation}
              onChange={(e) => onRecChange(index, e.target.value)}
              rows={3}
            />
          </SBARSection>
        </div>
      )}
    </div>
  );
}

/* ─── Main Page ──────────────────────────────────────────────────── */

export default function HandoffPage() {
  const [handoff, setHandoff] = useState(MOCK_HANDOFF);
  const [generalNotes, setGeneralNotes] = useState('');
  const [submitted, setSubmitted] = useState(false);

  function handleRecChange(residentIndex, value) {
    setHandoff((prev) => {
      const updated = { ...prev, residents: [...prev.residents] };
      updated.residents[residentIndex] = {
        ...updated.residents[residentIndex],
        recommendation: value,
      };
      return updated;
    });
  }

  function handleSubmit() {
    setSubmitted(true);
    // In production: POST /v1/handoff/submit
    setTimeout(() => setSubmitted(false), 3000);
  }

  return (
    <div className="handoff-page">
      {/* Shift Info Bar */}
      <div className="shift-info-bar bento-panel animate-in">
        <div className="shift-meta">
          <div className="shift-meta-item">
            <User size={16} />
            <span>Outgoing: <strong>{handoff.outgoing_nurse}</strong></span>
          </div>
          <div className="shift-meta-item">
            <Clock size={16} />
            <span>
              {formatDate(handoff.shift_start)}{' '}
              {formatTime(handoff.shift_start)} — {formatTime(handoff.shift_end)}
            </span>
          </div>
        </div>
        <div className="shift-resident-count">
          {handoff.residents.length} Residents
        </div>
      </div>

      {/* Resident SBAR Cards */}
      <div className="handoff-cards">
        {handoff.residents.map((res, i) => (
          <ResidentCard key={i} resident={res} index={i} onRecChange={handleRecChange} />
        ))}
      </div>

      {/* General Notes + Submit */}
      <div className="handoff-footer bento-panel animate-in" style={{ animationDelay: '0.5s' }}>
        <div className="footer-notes">
          <label className="footer-label">General Shift Notes</label>
          <textarea
            className="general-textarea"
            placeholder="Any overall notes for the incoming shift (equipment issues, schedule changes, etc.)..."
            value={generalNotes}
            onChange={(e) => setGeneralNotes(e.target.value)}
            rows={3}
          />
        </div>
        <button
          className={`submit-handoff-btn ${submitted ? 'submitted' : ''}`}
          onClick={handleSubmit}
          disabled={submitted}
        >
          {submitted ? (
            <>Handoff Submitted</>
          ) : (
            <><Send size={16} /> Submit Shift Handoff</>
          )}
        </button>
      </div>
    </div>
  );
}
