import React from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Search, Cpu, Database, LineChart, Layers, ArrowUpRight } from 'lucide-react';
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
        <div className="brand-logo" aria-hidden="true">
          <svg viewBox="0 0 48 48" fill="none" role="presentation"><path d="M8 32h8l5-14 6 18 5-12h8" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round"/><path d="M7 11h34M7 39h34" stroke="currentColor" strokeWidth="1" opacity=".42"/><circle cx="32" cy="24" r="2.5" fill="#e6af63"/></svg>
        </div>
        <div className="brand-text">
          <div className="brand-title">Burn<span>Trace</span></div>
          <div className="brand-subtitle">RELIABILITY WORKBENCH</div>
        </div>
      </div>

      <div className="sidebar-section-label">WORKSPACE <span>01 — 06</span></div>
      <nav className="sidebar-nav" aria-label="Main navigation">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
          >
            <span className="nav-icon">{item.icon}</span>
            <span className="nav-label">{item.label}</span>
            <ArrowUpRight className="nav-arrow" size={14} aria-hidden="true" />
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div className="system-pill"><span className="system-pill-text">RESEARCH PROTOTYPE · SYNTHETIC</span></div>
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
