import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { PageHeader } from '../components/layout/PageHeader';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { LoadingState } from '../components/ui/LoadingState';
import { ErrorState } from '../components/ui/ErrorState';
import { useApi } from '../hooks/useApi';
import { Search, ArrowRight, X } from 'lucide-react';
import './Components.css';

export default function Components() {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [perPage] = useState(50);
  const [searchQuery, setSearchQuery] = useState('');
  const [verdictFilter, setVerdictFilter] = useState('');
  const [variantFilter, setVariantFilter] = useState('');
  const [lotFilter, setLotFilter] = useState('');

  // Fetch 18 lots for the lot filter
  const { data: lotsData } = useApi('/api/lots');
  const lots = lotsData || [];

  // Construct query endpoint
  const queryParams = new URLSearchParams();
  queryParams.set('page', page);
  queryParams.set('per_page', perPage);
  if (searchQuery.trim()) queryParams.set('q', searchQuery.trim());
  if (verdictFilter) queryParams.set('verdict', verdictFilter);
  if (variantFilter) queryParams.set('variant', variantFilter);
  if (lotFilter) queryParams.set('lot', lotFilter);

  const endpoint = `/api/components?${queryParams.toString()}`;
  const { data, loading, error, refetch } = useApi(endpoint);

  const handleResetFilters = () => {
    setSearchQuery('');
    setVerdictFilter('');
    setVariantFilter('');
    setLotFilter('');
    setPage(1);
  };

  const hasActiveFilters = searchQuery || verdictFilter || variantFilter || lotFilter;

  return (
    <div className="page-components">
      <PageHeader 
        title="Component Fleet Catalog" 
        subtitle="Browse, filter, and inspect all 1,343 components across the 18 holdout production lots."
      >
        <div className="components-header-stats">
          <span className="stats-pill">
            TOTAL: <strong>{data?.total ?? 1343}</strong>
          </span>
          <span className="stats-pill">
            SHOWING: <strong>{data?.data?.length || 0}</strong>
          </span>
        </div>
      </PageHeader>

      {/* Filter Toolbar */}
      <div className="filter-toolbar-card">
        <div className="search-filter-box">
          <Search size={16} className="search-icon" />
          <input 
            type="text" 
            className="filter-search-input"
            placeholder="Search Component ID or Lot..."
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setPage(1);
            }}
          />
          {searchQuery && (
            <button className="clear-search-btn" onClick={() => { setSearchQuery(''); setPage(1); }}>
              <X size={14} />
            </button>
          )}
        </div>

        <div className="select-filters-group">
          {/* Fused Verdict Filter */}
          <div className="filter-item">
            <span className="filter-label">VERDICT:</span>
            <select 
              className="filter-select"
              value={verdictFilter}
              onChange={(e) => { setVerdictFilter(e.target.value); setPage(1); }}
            >
              <option value="">All Verdicts</option>
              <option value="PASS">PASS</option>
              <option value="MONITOR">MONITOR</option>
              <option value="REJECT">REJECT</option>
            </select>
          </div>

          {/* Device Variant Filter */}
          <div className="filter-item">
            <span className="filter-label">VARIANT:</span>
            <select 
              className="filter-select"
              value={variantFilter}
              onChange={(e) => { setVariantFilter(e.target.value); setPage(1); }}
            >
              <option value="">All Variants</option>
              <option value="CMOS_A">CMOS_A</option>
              <option value="CMOS_B">CMOS_B</option>
              <option value="CMOS_C">CMOS_C</option>
            </select>
          </div>

          {/* Production Lot Filter */}
          <div className="filter-item">
            <span className="filter-label">LOT:</span>
            <select 
              className="filter-select"
              value={lotFilter}
              onChange={(e) => { setLotFilter(e.target.value); setPage(1); }}
            >
              <option value="">All 18 Lots</option>
              {lots.map(l => (
                <option key={l.lot_id} value={l.lot_id}>
                  {l.lot_id} ({l.device_variant} · {l.component_count} parts)
                </option>
              ))}
            </select>
          </div>

          {hasActiveFilters && (
            <button className="btn-reset-filters" onClick={handleResetFilters}>
              <X size={14} /> Reset Filters
            </button>
          )}
        </div>
      </div>

      {/* Main Table Card */}
      <Card className="catalog-table-card">
        {loading && <LoadingState message="Querying component fleet..." />}
        {error && <ErrorState error={error} onRetry={refetch} />}
        
        {!loading && !error && data?.data && (
          <>
            <div className="table-responsive">
              <table className="catalog-table">
                <thead>
                  <tr>
                    <th>Component ID</th>
                    <th>Lot ID</th>
                    <th>Variant</th>
                    <th>Fused Verdict</th>
                    <th>Evidence Tier</th>
                    <th>Screening Risk</th>
                    <th>Primary Parameter</th>
                    <th style={{ textAlign: 'right' }}>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {data.data.length === 0 ? (
                    <tr>
                      <td colSpan="8" className="empty-table-row">
                        No components matched your filter criteria.
                      </td>
                    </tr>
                  ) : (
                    data.data.map((row) => {
                      const verdict = row.fused_verdict || row.disposition || 'PASS';
                      const tier = row.evidence_tier || 'PASS';
                      const score = row.score;

                      return (
                        <tr 
                          key={row.component_id}
                          className="catalog-row"
                          onClick={() => navigate(`/analyze/${row.component_id}`)}
                        >
                          <td className="code-font font-bold text-accent">
                            {row.component_id}
                          </td>
                          <td className="code-font text-muted">
                            {row.lot_id || '-'}
                          </td>
                          <td>
                            <Badge variant={row.device_variant || row.variant}>
                              {row.device_variant || row.variant}
                            </Badge>
                          </td>
                          <td>
                            <Badge status={verdict}>{verdict}</Badge>
                          </td>
                          <td>
                            <span className="tier-pill" title={tier === 'CONFIRMED' ? 'Measured limit breach in the synthetic screening data; physical defect status requires QA confirmation.' : undefined}>
                              {tier === 'CONFIRMED' ? 'LIMIT BREACH' : tier}
                            </span>
                          </td>
                          <td className="code-font">
                            <span className={`score-badge ${score >= 0.9 ? 'high-risk' : (score >= 0.5 ? 'med-risk' : '')}`}>
                              {score != null ? score.toFixed(4) : '-'}
                            </span>
                          </td>
                          <td className="code-font text-secondary">
                            {row.primary_parameter || '—'}
                          </td>
                          <td style={{ textAlign: 'right' }}>
                            <span className="row-action-btn">
                              Inspect <ArrowRight size={13} />
                            </span>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            <div className="pagination-bar">
              <div className="pagination-info">
                Page <strong className="code-font">{page}</strong> of <strong className="code-font">{data.total_pages || 1}</strong>
                <span className="total-hint">({data.total} total components)</span>
              </div>

              <div className="pagination-controls">
                <button 
                  disabled={!data.has_prev} 
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  className="btn-page"
                >
                  Previous
                </button>
                <button 
                  disabled={!data.has_next} 
                  onClick={() => setPage(p => p + 1)}
                  className="btn-page"
                >
                  Next
                </button>
              </div>
            </div>
          </>
        )}
      </Card>
    </div>
  );
}
