import React from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Search, Cpu, Database, LineChart, Layers } from 'lucide-react';
import './Sidebar.css';

export function Sidebar() {
  const navItems = [
    { to: '/', icon: <LayoutDashboard size={18} />, label: 'Overview' },
    { to: '/analyze', icon: <Search size={18} />, label: 'Analyze' },
    { to: '/components', icon: <Cpu size={18} />, label: 'Components' },
    { to: '/models', icon: <LineChart size={18} />, label: 'Models & Metrics' },
    { to: '/data', icon: <Database size={18} />, label: 'Operational Data' },
    { to: '/system', icon: <Layers size={18} />, label: 'Pipeline Lineage' },
  ];

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="brand-logo" aria-hidden="true">B</div>
        <div className="brand-text">
          <div className="brand-title">Burn<span>Trace</span></div>
          <div className="brand-subtitle">RELIABILITY WORKBENCH</div>
        </div>
      </div>

      <div className="sidebar-section-label">WORKSPACE</div>
      <nav className="sidebar-nav" aria-label="Main navigation">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
          >
            <span className="nav-icon">{item.icon}</span>
            <span className="nav-label">{item.label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div className="system-pill"><span className="system-pill-text">Research prototype · Synthetic data</span></div>
        <div className="sidebar-meta">
          <div className="meta-row">
            <span>DATASET:</span>
            <strong className="code-font">SIH26170-FINAL-01</strong>
          </div>
          <div className="meta-row">
            <span>PARTITION:</span>
            <span>18 LOTS · FROZEN</span>
          </div>
        </div>
      </div>
    </aside>
  );
}
