import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { PageHeader } from '../components/layout/PageHeader';
import { SearchInput } from '../components/ui/SearchInput';

import { Badge } from '../components/ui/Badge';
import { LoadingState } from '../components/ui/LoadingState';
import { ErrorState } from '../components/ui/ErrorState';
import { EmptyState } from '../components/ui/EmptyState';
import { Search, ArrowRight } from 'lucide-react';
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
            autoFocus={false}
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
          <section className="inspection-start" aria-labelledby="inspection-start-title">
            <span className="inspection-kicker">FOLLOW THE EVIDENCE</span>
            <h2 id="inspection-start-title">One component. Three questions.</h2>
            <p className="inspection-intro">Is it unusual in its lot? Where is it heading? What should QA do next?</p>
            <div className="inspection-steps">
              <div><span>01 / COMPARE</span><h3>Measured behaviour</h3><p>Inspect readings and the component’s position within its lot.</p></div>
              <div><span>02 / FORECAST</span><h3>Future drift</h3><p>Check the 168h forecast and upper bound against the parameter limit.</p></div>
              <div><span>03 / REVIEW</span><h3>QA decision</h3><p>Read the combined decision and the evidence that supports it.</p></div>
            </div>
            <div className="inspection-examples">
              {samples.map(sample => (
                <button key={sample.id} className="inspection-example" onClick={() => navigate(`/analyze/${sample.id}`)}>
                  <Badge status={sample.type}>{sample.type}</Badge>
                  <strong>{sample.type === 'PASS' ? 'Inspect a passing component' : sample.type === 'MONITOR' ? 'Investigate a review case' : 'Examine a rejection'}</strong>
                  <span className="code-font">{sample.id} <ArrowRight size={16} aria-hidden="true" /></span>
                </button>
              ))}
            </div>
            <p className="inspection-footnote">Examples come from the synthetic holdout registry. Forecasts and observed later readings are separate evidence; a PASS is not a flight qualification.</p>
          </section>
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
                    role="link"
                    tabIndex={0}
                    onKeyDown={event => { if (event.key === 'Enter') navigate(`/analyze/${res.component_id}`); }}
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
                        <span className="res-val font-bold" title={tier === 'CONFIRMED' ? 'Measured limit breach in the synthetic screening data; physical defect status requires QA confirmation.' : undefined}>
                          {tier === 'CONFIRMED' ? 'LIMIT BREACH' : tier}
                        </span>
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
