import React from 'react';
import './ui.css';

export function EmptyState({ icon: Icon, title, description }) {
  return (
    <div className="state-container">
      {Icon && <Icon className="state-icon" size={48} />}
      <h3 className="state-title">{title}</h3>
      {description && <p>{description}</p>}
    </div>
  );
}
