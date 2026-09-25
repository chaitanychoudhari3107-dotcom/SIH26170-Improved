import React from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Search, Cpu, Database, LineChart, Layers } from 'lucide-react';
import './Sidebar.css';

export function Sidebar() {
  const navItems = [
    { to: '/', icon: <LayoutDashboard size={18} />, label: 'Overview', badge: null },
    { to: '/analyze', icon: <Search size={18} />, label: 'Analyze', badge: 'Deep-Dive' },
    { to: '/components', icon: <Cpu size={18} />, label: 'Components', badge: '1,343' },
    { to: '/models', icon: <LineChart size={18} />, label: 'Models & Metrics', badge: 'A F2=74.2%' },
    { to: '/data', icon: <Database size={18} />, label: 'Operational Data', badge: 'DB' },
    { to: '/system', icon: <Layers size={18} />, label: 'Pipeline Lineage', badge: null },
  ];

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="brand-logo">
          <Cpu className="brand-icon" size={20} />
        </div>
        <div className="brand-text">
          <div className="brand-title">SIH26170</div>
          <div className="brand-subtitle">RELIABILITY ANALYTICS</div>
        </div>
      </div>

      <div className="sidebar-section-label">NAVIGATION</div>
      <nav className="sidebar-nav">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
          >
            <span className="nav-icon">{item.icon}</span>
            <span className="nav-label">{item.label}</span>
            {item.badge && <span className="nav-badge">{item.badge}</span>}
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div className="system-pill">

          <span className="system-pill-text">RESEARCH PROTOTYPE</span>
        </div>
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
