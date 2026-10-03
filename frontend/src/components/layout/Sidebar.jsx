import React from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Search, Cpu, Database, LineChart, Layers } from 'lucide-react';
import './Sidebar.css';

export function Sidebar() {
  const exploreItems = [
    { to: '/', icon: <LayoutDashboard size={18} />, label: 'Overview' },
    { to: '/analyze', icon: <Search size={18} />, label: 'Analyze' },
    { to: '/components', icon: <Cpu size={18} />, label: 'Components' },
  ];
  const evidenceItems = [
    { to: '/models', icon: <LineChart size={18} />, label: 'Models & Metrics' },
    { to: '/data', icon: <Database size={18} />, label: 'Operational Data' },
    { to: '/system', icon: <Layers size={18} />, label: 'Pipeline Lineage' },
  ];

  const renderLink = (item) => (
    <NavLink key={item.to} to={item.to} end={item.to === '/'}
      className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
      <span className="nav-icon">{item.icon}</span>
      <span className="nav-label">{item.label}</span>
    </NavLink>
  );

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="brand-text">
          <div className="brand-title">Burn<span>Trace</span></div>
          <div className="brand-subtitle">RELIABILITY WORKBENCH</div>
        </div>
      </div>

      <nav className="sidebar-nav" aria-label="Main navigation">
        <div className="sidebar-nav-group"><div className="sidebar-section-label">EXPLORE</div>{exploreItems.map(renderLink)}</div>
        <div className="sidebar-nav-group"><div className="sidebar-section-label">EVIDENCE &amp; WORKFLOW</div>{evidenceItems.map(renderLink)}</div>
      </nav>

      <div className="sidebar-footer">
        <span>Research prototype · Synthetic data</span>
        <small>SIH26170-FINAL-01 · 18 held-out lots</small>
      </div>
    </aside>
  );
}
