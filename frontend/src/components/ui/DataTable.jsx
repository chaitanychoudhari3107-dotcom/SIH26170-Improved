import React from 'react';
import './ui.css';

export function DataTable({ columns, data, onRowClick }) {
  return (
    <div className="table-container">
      <table>
        <thead>
          <tr>
            {columns.map((col, i) => (
              <th key={i}>{col.header}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, i) => (
            <tr key={i} tabIndex={onRowClick ? 0 : undefined} onKeyDown={e => { if (e.key === 'Enter' && onRowClick) onRowClick(row); }} onClick={() => onRowClick && onRowClick(row)} style={{ cursor: onRowClick ? 'pointer' : 'default' }}>
              {columns.map((col, j) => (
                <td key={j}>{col.accessor(row)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
