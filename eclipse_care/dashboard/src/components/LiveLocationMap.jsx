import React from 'react';
import './LiveLocationMap.css';
import { MapPin, Navigation, AlertOctagon, Map as MapIcon, ArrowRight } from 'lucide-react';

const MOCK_ZONES = [
  { id: 1, name: "East Wing", count: 12, status: "secure" },
  { id: 2, name: "Dining Hall", count: 28, status: "secure" },
  { id: 3, name: "Front Exit", count: 2, status: "warning" },
  { id: 4, name: "Garden Door", count: 0, status: "secure" }
];

const MOCK_RESIDENTS = [
  { id: 1, name: "Eleanor Vance", zone: "Front Exit", elopement_risk: true, time_in_zone: "4m" },
  { id: 2, name: "Arthur Pendelton", zone: "Front Exit", elopement_risk: false, time_in_zone: "1m" }
];

export default function LiveLocationMap() {
  return (
    <div className="bento-panel location-map animate-in" style={{ animationDelay: '0.3s' }}>
      <div className="panel-header">
        <div>
          <h3>Live Tracking (RTLS)</h3>
          <p className="text-muted">Real-time zone monitoring</p>
        </div>
        <div className="status-badge pulse-active">
          <span className="dot"></span>
          Geofence Active
        </div>
      </div>
      
      <div className="location-content">
        <div className="zones-list">
          <div className="section-header">
            <h4 className="section-title">Facility Zones</h4>
            <button className="text-btn text-emerald">View Map <MapIcon size={14} /></button>
          </div>
          {MOCK_ZONES.map((zone, idx) => (
            <div 
              key={zone.id} 
              className={`zone-card ${zone.status}`}
              style={{ animationDelay: `${0.4 + (idx * 0.1)}s` }}
            >
              <div className="zone-info">
                <MapPin size={18} />
                <span className="zone-name">{zone.name}</span>
              </div>
              <div className="zone-count-pill">{zone.count} Residents</div>
            </div>
          ))}
        </div>
        
        <div className="exit-watch">
          <h4 className="section-title">Proximity Watch (Exits)</h4>
          {MOCK_RESIDENTS.map((res, idx) => (
            <div 
              key={res.id} 
              className={`resident-watch-card ${res.elopement_risk ? 'high-risk' : ''}`}
              style={{ animationDelay: `${0.6 + (idx * 0.1)}s` }}
            >
              <div className="watch-top">
                <span className="watch-name">{res.name}</span>
                <span className="watch-time">{res.time_in_zone}</span>
              </div>
              <div className="watch-bottom">
                <Navigation size={14} className="text-muted" />
                <span className="watch-zone">Detected at {res.zone}</span>
              </div>
              {res.elopement_risk && (
                <div className="elopement-warning">
                  <AlertOctagon size={14} />
                  <span>Elopement Risk</span>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
