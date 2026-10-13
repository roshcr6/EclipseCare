import React from 'react';
import './VitalsWidget.css';
import { LineChart, Line, ResponsiveContainer, YAxis } from 'recharts';
import { Heart } from 'lucide-react';

const mockData = [
  { time: '10:00', hr: 65 },
  { time: '10:05', hr: 68 },
  { time: '10:10', hr: 64 },
  { time: '10:15', hr: 70 },
  { time: '10:20', hr: 72 },
  { time: '10:25', hr: 66 },
  { time: '10:30', hr: 65 }
];

export default function VitalsWidget() {
  return (
    <div className="bento-panel vitals-widget animate-in" style={{ animationDelay: '0.3s' }}>
      <div className="panel-header">
        <h3>Unit Average Vitals</h3>
        <span className="heart-icon-container">
          <Heart size={20} className="pulse-icon" />
        </span>
      </div>
      
      <div className="vitals-stats">
        <div className="stat-block">
          <span className="label">Avg Heart Rate</span>
          <div className="value-group">
            <span className="value">68</span>
            <span className="unit">bpm</span>
          </div>
          <span className="trend positive">Normal Baseline</span>
        </div>
        
        <div className="stat-block">
          <span className="label">Active Alerts</span>
          <div className="value-group">
            <span className="value danger">1</span>
          </div>
          <span className="trend negative">Needs attention</span>
        </div>
      </div>
      
      <div className="chart-container">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={mockData}>
            <YAxis domain={['dataMin - 5', 'dataMax + 5']} hide />
            <Line 
              type="monotone" 
              dataKey="hr" 
              stroke="var(--emerald-500)" 
              strokeWidth={3} 
              dot={false}
              animationDuration={1500}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
