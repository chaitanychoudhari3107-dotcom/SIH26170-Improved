import React from 'react';
import { AlertCircle } from 'lucide-react';
import './ui.css';

export function ErrorState({ error, onRetry }) {
  return (
    <div className="state-container">
      <AlertCircle className="state-icon" size={48} color="var(--status-reject)" />
      <h3 className="state-title">Something went wrong</h3>
      <p>{error?.message || 'Failed to load data.'}</p>
      {onRetry && (
        <button className="btn-primary" onClick={onRetry}>
          Try Again
        </button>
      )}
    </div>
  );
}
