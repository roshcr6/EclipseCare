import React from 'react';
import './UnitSummaryWidget.css';
import { Users, Activity, ShieldAlert, ShieldCheck } from 'lucide-react';

export default function UnitSummaryWidget() {
  return (
    <div className="bento-panel summary-widget animate-in" style={{ animationDelay: '0.2s' }}>
      <div className="panel-header">
        <div>
          <h3>Unit A Status Summary</h3>
          <p className="text-muted">Current shift metrics</p>
        </div>
      </div>
      
      <div className="summary-grid">
        <div className="summary-card">
          <div className="summary-icon-wrapper text-emerald">
            <Users size={22} />
          </div>
          <div className="summary-data">
            <span className="summary-value">48</span>
            <span className="summary-label">Total Residents</span>
          </div>
        </div>

        <div className="summary-card critical">
          <div className="summary-icon-wrapper text-danger">
            <ShieldAlert size={22} />
          </div>
          <div className="summary-data">
            <span className="summary-value text-danger">1</span>
            <span className="summary-label">Critical Alerts</span>
          </div>
        </div>

        <div className="summary-card">
          <div className="summary-icon-wrapper text-info">
            <Activity size={22} />
          </div>
          <div className="summary-data">
            <span className="summary-value">14</span>
            <span className="summary-label">Residents Active</span>
          </div>
        </div>

        <div className="summary-card">
          <div className="summary-icon-wrapper text-tertiary">
            <ShieldCheck size={22} />
          </div>
          <div className="summary-data">
            <span className="summary-value">6</span>
            <span className="summary-label">Staff on Shift</span>
          </div>
        </div>
      </div>
    </div>
  );
}
