import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { PageHeader } from '../components/layout/PageHeader';
import { SearchInput } from '../components/ui/SearchInput';

import { Badge } from '../components/ui/Badge';
import { LoadingState } from '../components/ui/LoadingState';
import { ErrorState } from '../components/ui/ErrorState';
import { EmptyState } from '../components/ui/EmptyState';
import { Search, ArrowRight, Cpu } from 'lucide-react';
import { api } from '../services/api';
import './Analyze.css';

export default function Analyze() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const query = searchParams.get('q') || '';
  
  const [inputValue, setInputValue] = useState(query);
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [samples, setSamples] = useState([]);
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    let active = true;
    Promise.all(['PASS', 'MONITOR', 'REJECT'].map(async type => {
      const result = await api.get(`/api/components?verdict=${type}&per_page=1`);
      return result.data?.[0] ? { id: result.data[0].component_id, type } : null;
    })).then(values => {
      if (active) setSamples(values.filter(Boolean));
    }).catch(() => { if (active) setSamples([]); });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    setInputValue(query);
    setError(null);
    if (!query) { setResults([]); setLoading(false); return () => controller.abort(); }
    setLoading(true);
    api.get(`/api/analysis/search?q=${encodeURIComponent(query)}`, {signal:controller.signal})
      .then(data => { if (!controller.signal.aborted) setResults(Array.isArray(data) ? data : (data.results || [])); })
      .catch(err => { if (!controller.signal.aborted) setError(err); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [query, retry]);

  const performSearch = () => setRetry(v => v + 1);

  const handleSearch = (val) => {
    if (val.trim()) {
      setSearchParams({ q: val.trim() });
    } else {
      setSearchParams({});
    }
  };

  return (
    <div className="page-analyze">
      <PageHeader 
        title="Component Deep-Dive & Inspection" 
        subtitle="Search any component across the 1,343 holdout population (C00158–C05320) or browse by lot"
      />
      
      {/* Search Bar */}
      <div className="analyze-search-container">
        <div className="search-input-wrapper">
          <SearchInput 
            value={inputValue}
            onChange={setInputValue}
            onSubmit={handleSearch}
            placeholder="Search by Component ID (e.g. C00158, C00282) or Lot (e.g. A_L03)..."
            autoFocus={true}
          />
        </div>

        {/* Quick Sample Selector */}
        <div className="sample-chips-row">
          <span className="sample-label">Quick Inspection Examples:</span>
          {samples.map(s => (
            <button
              key={s.id}
              className="sample-chip"
              onClick={() => {
                setInputValue(s.id);
                handleSearch(s.id);
              }}
            >
              <Badge status={s.type} size="sm">{s.type}</Badge>
              <span className="code-font">{s.id}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Search Results */}
      <div className="analyze-results">
        {loading && <LoadingState message="Searching component registry..." />}
        {error && <ErrorState error={error} onRetry={() => performSearch(query)} />}
        
        {!loading && !error && query && results.length === 0 && (
          <EmptyState 
            icon={Search} 
            title="No matching components found" 
            description={`No components found matching "${query}". Remember component IDs run from C00158 to C05320 across 18 whole lots.`} 
          />
        )}

        {!loading && !error && !query && (
          <div className="search-prompt-card">
            <div className="prompt-icon-box">
              <Cpu size={32} className="text-accent" />
            </div>
            <h3 className="prompt-title">Ready for Component Diagnostic</h3>
            <p className="prompt-desc">
              Enter any component ID from the frozen holdout dataset to inspect its static screening score, 4-epoch degradation trajectory, Module B 168h drift forecast, and synthesized reliability verdict.
            </p>
          </div>
        )}

        {!loading && !error && results.length > 0 && (
          <div className="results-container">
            <div className="results-meta">
              Found <strong>{results.length}</strong> matching component{results.length > 1 ? 's' : ''}
            </div>

            <div className="results-grid">
              {results.map((res) => {
                const verdict = res.fused_verdict || res.disposition || 'UNKNOWN';
                const tier = res.evidence_tier || 'UNKNOWN';
                const isFail = (tier === 'CONFIRMED' || verdict === 'REJECT');

                return (
                  <div 
                    key={res.component_id} 
                    className={`component-result-card ${isFail ? 'fail-border' : ''}`}
                    onClick={() => navigate(`/analyze/${res.component_id}`)}
                  >
                    <div className="res-card-top">
                      <span className="res-card-id code-font">{res.component_id}</span>
                      <Badge status={verdict}>
                        {verdict}
                      </Badge>
                    </div>

                    <div className="res-card-middle">
                      <div className="res-info-row">
                        <span className="res-lbl">Evidence Tier:</span>
                        <span className="res-val font-bold">{tier}</span>
                      </div>
                      <div className="res-info-row">
                        <span className="res-lbl">Screening Risk:</span>
                        <span className="res-val code-font">{res.score != null ? res.score.toFixed(4) : 'N/A'}</span>
                      </div>
                      <div className="res-info-row">
                        <span className="res-lbl">Flagged Feature:</span>
                        <span className="res-val code-font text-accent">{res.primary_parameter || 'None (Nominal)'}</span>
                      </div>
                    </div>

                    <div className="res-card-action">
                      <span>Launch Deep Dive</span>
                      <ArrowRight size={14} />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
