import React from 'react';
import './ResidentList.css';
import { Bed, Activity, User, Moon, ArrowRight } from 'lucide-react';

const MOCK_RESIDENTS = [
  { id: 1, name: 'Eleanor Vance', room: '102', status: 'In Bed', state: 'sleeping' },
  { id: 2, name: 'Arthur Pendelton', room: '105', status: 'Walking (PT)', state: 'active' },
  { id: 3, name: 'Martha Jones', room: '201', status: 'Resting', state: 'normal' },
  { id: 4, name: 'James Wilson', room: '205', status: 'No Movement (2h)', state: 'warning' },
];

export default function ResidentList() {
  return (
    <div className="bento-panel resident-list animate-in" style={{ animationDelay: '0.2s' }}>
      <div className="panel-header">
        <div>
          <h3>Unit A Residents</h3>
          <p className="text-muted">Current status via edge telemetry</p>
        </div>
        <button className="btn-secondary text-sm">
          View All <ArrowRight size={14} />
        </button>
      </div>
      
      <div className="table-container">
        <table className="resident-table">
          <thead>
            <tr>
              <th>Status</th>
              <th>Resident</th>
              <th>Room</th>
              <th>Activity State</th>
            </tr>
          </thead>
          <tbody>
            {MOCK_RESIDENTS.map((res, idx) => (
              <tr 
                key={res.id} 
                className="resident-row"
                style={{ animationDelay: `${0.3 + (idx * 0.1)}s` }}
              >
                <td>
                  <div className={`status-icon ${res.state}`}>
                    {res.state === 'sleeping' && <Moon size={18} />}
                    {res.state === 'active' && <Activity size={18} />}
                    {res.state === 'normal' && <User size={18} />}
                    {res.state === 'warning' && <Bed size={18} />}
                  </div>
                </td>
                <td className="resident-name">{res.name}</td>
                <td className="resident-room">{res.room}</td>
                <td>
                  <div className={`status-pill ${res.state}`}>
                    {res.status}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
