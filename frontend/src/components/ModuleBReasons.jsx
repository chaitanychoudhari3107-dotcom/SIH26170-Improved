import React from 'react';
import './ModuleBReasons.css';

const REASONS = {
  B_HIGH_FORECAST_DRIFT: 'Forecast drift is high relative to comparable parts',
  B_WIDE_ENVELOPE: 'Forecast uncertainty is wide; engineer review is needed',
  B_LOT_OUTLIER_24H: 'The 24h reading differs from its lot peers',
  B_FORECAST_EXCEEDS_LIMIT: 'The 168h forecast exceeds a supplied specification limit',
  B_ENVELOPE_REACHES_LIMIT: 'The forecast upper bound reaches a supplied limit',
  B_NO_EARLY_SIGNAL: 'Early measurements provide limited supporting evidence',
};

export function ModuleBReasons({ codes, compact = false }) {
  const entries = String(codes || '').split('|').map(part => part.trim()).filter(Boolean);
  if (!entries.length) return <span>No Module B warning indicators at this hour.</span>;

  return <div className={compact ? 'bt-reasons bt-reasons-compact' : 'bt-reasons'}>
    <ul aria-label="Module B indicators">
      {entries.map((entry, index) => {
        const [code, ...parameter] = entry.split(':');
        const label = REASONS[code] || code.replace(/^B_/, '').replaceAll('_', ' ').toLowerCase();
        return <li key={`${entry}-${index}`}>{label}{parameter.length ? <> · <strong>{parameter.join(':').replaceAll('_', ' ')}</strong></> : null}</li>;
      })}
    </ul>
    <details><summary>Technical reason codes</summary><code>{entries.join(' | ')}</code></details>
  </div>;
}
