import React from 'react';
import './SmartAlertFeed.css';
import { ShieldAlert, AlertTriangle, Info, ArrowRight } from 'lucide-react';

const MOCK_ALERTS = [
  {
    id: 1,
    type: 'FALL_DETECTED',
    resident: 'Eleanor Vance (Room 102)',
    time: 'Just now',
    severity: 'emergency',
    message: 'Impact detected (3.2g). Potential fall.',
    llm_suppressed: false
  },
  {
    id: 101,
    type: 'PREDICTIVE_UTI_RISK',
    resident: 'Harold Finch (Room 204)',
    time: '3:00 AM',
    severity: 'warning',
    message: 'Nocturnal bathroom visits increased by 42% over 3 days. Elevated resting HR (+6 bpm).',
    llm_suppressed: false
  },
  {
    id: 2,
    type: 'HR_ANOMALY',
    resident: 'Arthur Pendelton (Room 105)',
    time: '12m ago',
    severity: 'warning',
    message: 'Heart rate elevated (105 bpm) vs baseline (65 bpm).',
    llm_suppressed: true,
    llm_reasoning: 'Resident is currently in physical therapy session. Elevation expected.'
  },
  {
    id: 3,
    type: 'BATTERY_LOW',
    resident: 'Martha Jones (Room 201)',
    time: '1h ago',
    severity: 'info',
    message: 'Wearable battery at 15%.',
    llm_suppressed: false
  }
];

export default function SmartAlertFeed() {
  return (
    <div className="bento-panel alert-feed animate-in" style={{ animationDelay: '0.1s' }}>
      <div className="panel-header">
        <div>
          <h3>Smart Alert Feed</h3>
          <p className="text-muted">Real-time anomaly & predictive events</p>
        </div>
        <div className="badge-count">1 Critical</div>
      </div>
      
      <div className="alert-list">
        {MOCK_ALERTS.map((alert, index) => (
          <div 
            key={alert.id} 
            className={`alert-card ${alert.severity} ${alert.llm_suppressed ? 'suppressed' : ''}`}
            style={{ animationDelay: `${0.15 + (index * 0.1)}s` }}
          >
            <div className="alert-icon-container">
              {alert.severity === 'emergency' && <ShieldAlert size={20} />}
              {alert.severity === 'warning' && !alert.llm_suppressed && <AlertTriangle size={20} />}
              {alert.severity === 'info' && !alert.llm_suppressed && <Info size={20} />}
              {alert.llm_suppressed && <Info size={20} />}
            </div>
            
            <div className="alert-content">
              <div className="alert-top">
                <span className="resident">{alert.resident}</span>
                <span className="time">{alert.time}</span>
              </div>
              <p className="message">{alert.message}</p>
              
              {alert.llm_suppressed && (
                <div className="ai-context">
                  <div className="ai-badge">AI Suppressed</div>
                  <p>{alert.llm_reasoning}</p>
                </div>
              )}
              
              {!alert.llm_suppressed && (
                <div className="alert-actions">
                  <button className="btn-primary">Acknowledge</button>
                  <button className="btn-secondary">
                    Details <ArrowRight size={14} />
                  </button>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
