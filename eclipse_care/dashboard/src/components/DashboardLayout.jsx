import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import './DashboardLayout.css';
import { Activity, Bell, Users, Settings, ClipboardList, Stethoscope } from 'lucide-react';

const PAGE_TITLES = {
  '/': { title: 'Unit A Command Center', subtitle: 'Real-time telemetry and predictive analytics' },
  '/handoff': { title: 'SBAR Shift Handoff', subtitle: 'Structured handoff — auto-populated from telemetry' },
  '/emar': { title: 'eMAR Medication Log', subtitle: 'Electronic medication administration record' },
};

export default function DashboardLayout({ children }) {
  const location = useLocation();
  const pageInfo = PAGE_TITLES[location.pathname] || PAGE_TITLES['/'];

  return (
    <div className="dashboard-container">
      {/* Sidebar Navigation */}
      <nav className="sidebar">
        <div className="brand">
          <Activity className="brand-icon" size={28} />
          <h2>Eclipse Care</h2>
        </div>
        
        <div className="nav-links">
          <NavLink to="/" end className={({ isActive }) => isActive ? 'active' : ''}>
            <Activity size={18} /> Overview
          </NavLink>
          <NavLink to="/handoff" className={({ isActive }) => isActive ? 'active' : ''}>
            <ClipboardList size={18} /> SBAR Handoff
          </NavLink>
          <NavLink to="/emar" className={({ isActive }) => isActive ? 'active' : ''}>
            <Stethoscope size={18} /> eMAR Log
          </NavLink>
          <NavLink to="/alerts" className={({ isActive }) => isActive ? 'active' : ''}>
            <Bell size={18} /> Alerts
          </NavLink>
        </div>
        
        <div className="spacer"></div>

        <div className="nav-links">
          <NavLink to="/settings" className={({ isActive }) => isActive ? 'active' : ''}>
            <Settings size={18} /> Settings
          </NavLink>
        </div>

        <div className="user-profile">
          <div className="avatar">JS</div>
          <div className="user-info">
            <p className="name">Jane Smith, RN</p>
            <p className="role">Shift Supervisor</p>
          </div>
        </div>
      </nav>

      {/* Main Content Area */}
      <main className="main-content">
        <header className="top-header">
          <div>
            <h1>{pageInfo.title}</h1>
            <p className="text-muted">{pageInfo.subtitle}</p>
          </div>
          <div className="status-badge pulse-active">
            <span className="dot"></span>
            System Online
          </div>
        </header>
        
        <div className="scrollable-content">
          {children}
        </div>
      </main>
    </div>
  );
}
