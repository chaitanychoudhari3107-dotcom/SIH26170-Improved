import React from 'react';
import { Search } from 'lucide-react';
import './ui.css';

export function SearchInput({ value, onChange, placeholder = 'Search...', onSubmit, autoFocus }) {
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && onSubmit) {
      onSubmit(value);
    }
  };

  return (
    <div className="search-wrapper">
      <Search className="search-icon" size={18} />
      <input
        type="text"
        className="search-input"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        autoFocus={autoFocus}
      />
    </div>
  );
}
