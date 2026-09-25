import React from 'react';
import { Loader } from 'lucide-react';
import './ui.css';

export function LoadingState({ message = 'Loading...' }) {
  return (
    <div className="state-container">
      <Loader className="state-icon" size={32} style={{ animation: 'spin 1s linear infinite' }} />
      <p>{message}</p>
      <style>{`
        @keyframes spin { 100% { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}
