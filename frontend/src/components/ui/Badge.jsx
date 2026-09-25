import React from 'react';
import './ui.css';

export function Badge({ status, variant, size = 'md', children, icon }) {
  let type = 'default';
  const s = String(status || variant || children || '').toUpperCase();
  
  if (s === 'PASS' || s === 'VERIFIED_PASS' || s === 'HEALTHY') type = 'pass';
  else if (s === 'MONITOR' || s === 'WARNING' || s === 'DRIFT') type = 'monitor';
  else if (s === 'REJECT' || s === 'FAILED' || s === 'CRITICAL') type = 'reject';
  else if (s === 'CONFIRMED' || s === 'SPEC_EXCEED') type = 'confirmed';
  else if (s.startsWith('CMOS_')) type = 'variant';
  else if (s.endsWith('H') || s.startsWith('EPOCH')) type = 'epoch';
  
  return (
    <span className={`badge badge-${type} badge-${size}`}>
      {icon && <span className="badge-icon">{icon}</span>}
      {children || status || variant}
    </span>
  );
}

