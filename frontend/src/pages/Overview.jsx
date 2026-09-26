import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import ComponentStory from '../components/ComponentStory';
import operationalEvaluation from '../data/operationalEvaluation.json';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { LoadingState } from '../components/ui/LoadingState';
import { ErrorState } from '../components/ui/ErrorState';
import { SearchInput } from '../components/ui/SearchInput';
import { useApi } from '../hooks/useApi';
import { AlertTriangle, Cpu, Search, ArrowRight, Layers, CheckCircle2, XCircle, GitBranch } from 'lucide-react';
import './Overview.css';

export default function Overview() {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');
  
  const { data: summary, loading: summaryLoading, error: summaryError, refetch: refetchSummary } = useApi('/api/analysis/summary');
  const { data: evalMetrics } = useApi('/api/models/evaluation');
  const { data: recent, loading: recentLoading } = useApi('/api/components?page=1&per_page=12');

  const handleSearchSubmit = (query) => {
    if (query && query.trim()) {
      navigate(`/analyze?q=${encodeURIComponent(query.trim())}`);
    }
  };

  if (summaryLoading) return <LoadingState message="Loading fleet reliability analytics..." />;
  if (summaryError) return <ErrorState error={summaryError} onRetry={refetchSummary} />;

  const baseline = evalMetrics?.baseline || {};
  const review = operationalEvaluation.epochs['168'].review_gate;

  return (
    <div className="page-overview">
      <ComponentStory />
      <section className="overview-operational-proof" aria-labelledby="operational-proof-title">
        <div className="proof-heading"><div><span>MEASURED EVIDENCE / 168H OPERATIONAL REVIEW GATE</span><h2 id="operational-proof-title">What the screening rule caught—and missed</h2></div><button type="button" onClick={() => navigate('/models')}>Inspect the exact matrix <ArrowRight size={15}/></button></div>
        <div className="proof-numbers">
          <div><strong>{review.tp}/{operationalEvaluation.defects}</strong><span>Synthetic defects flagged for review</span></div>
          <div className="proof-miss"><strong>{review.fn}</strong><span>Synthetic defects missed</span></div>
          <div><strong>{review.fp}</strong><span>Healthy parts sent for review</span></div>
        </div>
        <p>MONITOR, HOLD and REJECT count as review alerts. These are retrospective synthetic results on {operationalEvaluation.population.toLocaleString()} parts across {operationalEvaluation.lots} lots; this holdout was inspected during development and does not establish performance on physical hardware.</p>
      </section>
      <div className="overview-section-heading">
        <div><span className="overview-section-kicker">FROZEN BENCHMARK / EXPLORER</span><h2>From one part to the fleet</h2><p>1,343 synthetic holdout components across 18 lots. These saved explorer dispositions are separate from the operational policy evaluation.</p></div>
        <div className="header-chips">
          <span className="spec-chip">
            <span className="spec-dot live" />
            DATASET: {summary?.dataset_id || 'SIH26170-FINAL-01'}
          </span>
          <span className="spec-chip">
            STATUS: {summary?.dataset_status || 'FROZEN_FINAL'}
          </span>
        </div>
      </div>

      {/* Quick Search Banner */}
      <div className="overview-search-banner">
        <div className="search-banner-inner">
          <div className="search-banner-text">
            <Search size={18} className="search-banner-icon" />
            <span>Direct Component Inspection</span>
          </div>
          <div className="search-banner-input">
            <SearchInput 
              value={searchQuery}
              onChange={setSearchQuery}
              onSubmit={handleSearchSubmit}
              placeholder="Search component (e.g. C00158, C01949, C05320) or lot (e.g. A_L03)..."
            />
          </div>
        </div>
      </div>

      {/* Top Level Metric KPIs */}
      <div className="kpi-grid">
        <div className="kpi-card">
          <div className="kpi-header">
            <span className="kpi-title">FLEET POPULATION</span>
            <Cpu size={16} className="kpi-icon text-muted" />
          </div>
          <div className="kpi-value">{summary?.total_components?.toLocaleString() || '1,343'}</div>
          <div className="kpi-sub">
            <span>18 Whole Lots</span> · <span className="code-font">C00158–C05320</span>
          </div>
          <div className="kpi-bar-track">
            <div className="kpi-bar-fill accent" style={{ width: '100%' }} />
          </div>
        </div>

        <div className="kpi-card pass">
          <div className="kpi-header">
            <span className="kpi-title">PASS DISPOSITION</span>
            <CheckCircle2 size={16} className="kpi-icon text-pass" />
          </div>
          <div className="kpi-value text-pass">
            {summary?.pass_count?.toLocaleString() || '1,113'}
          </div>
          <div className="kpi-sub">
            <strong>{((summary?.pass_count / summary?.total) * 100).toFixed(1)}%</strong> under the frozen explorer fusion output
          </div>
          <div className="kpi-bar-track">
            <div className="kpi-bar-fill pass" style={{ width: `${(summary?.pass_count / summary?.total) * 100}%` }} />
          </div>
        </div>

        <div className="kpi-card monitor">
          <div className="kpi-header">
            <span className="kpi-title">MONITOR DISPOSITION</span>
            <AlertTriangle size={16} className="kpi-icon text-monitor" />
          </div>
          <div className="kpi-value text-monitor">
            {summary?.monitor_count?.toLocaleString() || '202'}
          </div>
          <div className="kpi-sub">
            <strong>{((summary?.monitor_count / summary?.total) * 100).toFixed(1)}%</strong> drift / statistical outliers
          </div>
          <div className="kpi-bar-track">
            <div className="kpi-bar-fill monitor" style={{ width: `${(summary?.monitor_count / summary?.total) * 100}%` }} />
          </div>
        </div>

        <div className="kpi-card reject">
          <div className="kpi-header">
            <span className="kpi-title">REJECT DISPOSITION</span>
            <XCircle size={16} className="kpi-icon text-reject" />
          </div>
          <div className="kpi-value text-reject">
            {summary?.reject_count?.toLocaleString() || '28'}
          </div>
          <div className="kpi-sub">
            <strong>{summary?.confirmed_count ?? 23}</strong> observed hard-limit breaches + <strong>{(summary?.reject_count ?? 28) - (summary?.confirmed_count ?? 23)}</strong> forecast-only holds in the frozen explorer output
          </div>
          <div className="kpi-bar-track">
            <div className="kpi-bar-fill reject" style={{ width: `${(summary?.reject_count / summary?.total) * 100}%` }} />
          </div>
        </div>
      </div>

      <p className="overview-policy-note">The counts above are the frozen benchmark explorer's saved fusion output. The operational workspace uses a separately evaluated review policy; see its 24h and 168h confusion matrices under Models &amp; Metrics.</p>

      <section className="dataset-evidence" aria-labelledby="dataset-evidence-title">
        <div>
          <h2 id="dataset-evidence-title">Dataset &amp; evidence</h2>
          <p><strong>5,400 synthetic components</strong> across 72 lots and three device variants, with six electrical parameters measured at 0h, 24h, 96h and 168h. The evaluation explorer contains 1,343 components from 18 held-out lots.</p>
          <p>Five separately frozen, 64-part challenge lots expose difficult cases and documented misses. Labels are synthetic injections, not verified physical defects. The operational rule was also inspected on the holdout during development.</p>
        </div>
        <div className="dataset-evidence-links">
          <button type="button" onClick={() => navigate('/models')}>See measured results <ArrowRight size={14}/></button>
          <button type="button" onClick={() => navigate('/system')}>Explore data lineage <ArrowRight size={14}/></button>
        </div>
      </section>

      {/* Analytical Workflow Architecture Banner */}
      <div className="lineage-strip-card">
        <div className="lineage-strip-header">
          <div className="lineage-strip-title">
            <Layers size={16} className="text-accent" />
            <span>VERIFIED DATA LINEAGE & ANALYTICAL PIPELINE</span>
          </div>
          <button className="lineage-strip-btn" onClick={() => navigate('/system')}>
            View Full Architecture <ArrowRight size={14} />
          </button>
        </div>
        <div className="lineage-flow-steps">
          <div className="flow-step">
            <div className="step-num">01</div>
            <div className="step-title">Raw Holdout</div>
            <div className="step-meta">1,343 Components · 18 Lots</div>
          </div>
          <div className="flow-divider">→</div>
          <div className="flow-step">
            <div className="step-num">02</div>
            <div className="step-title">Epoch Splits</div>
            <div className="step-meta">0h, 24h, 96h, 168h</div>
          </div>
          <div className="flow-divider">→</div>
          <div className="flow-step active">
            <div className="step-num">03</div>
            <div className="step-title">Module A Screen</div>
            <div className="step-meta">Static + Outlier Scorer</div>
          </div>
          <div className="flow-divider">+</div>
          <div className="flow-step active">
            <div className="step-num">04</div>
            <div className="step-title">Module B Forecast</div>
            <div className="step-meta">0h–24h to 168h + P95</div>
          </div>
          <div className="flow-divider">→</div>
          <div className="flow-step highlight">
            <div className="step-num">05</div>
            <div className="step-title">Decision Fusion</div>
            <div className="step-meta">A+B Verdict Synthesis</div>
          </div>
        </div>
      </div>

      {/* Module Overview Grid */}
      <div className="modules-overview-grid">
        {/* Module A Summary */}
        <Card title="Module A: Lot-relative screening + limit checks (168h)" className="summary-module-card">
          <div className="module-summary-body">
            <div className="module-stat-row">
              <span className="stat-label">Model Pipeline:</span>
              <span className="stat-val code-font">ModuleA-FINAL01</span>
            </div>
            <div className="module-stat-row">
              <span className="stat-label">Operating Threshold:</span>
              <span className="stat-val code-font">0.900 hard-limit score floor; statistical alerts use separate criteria</span>
            </div>
            <div className="module-stat-row">
              <span className="stat-label">Measured limit breaches:</span>
              <span className="stat-val text-reject font-bold">23 synthetic parts</span>
            </div>
            <div className="module-stat-row">
              <span className="stat-label">Statistical MONITOR:</span>
              <span className="stat-val text-monitor font-bold">55 parts (Rank Drift)</span>
            </div>
            <div className="module-stat-row">
              <span className="stat-label">Nominal PASS:</span>
              <span className="stat-val text-pass font-bold">1,265 parts</span>
            </div>
            <div className="tier-breakdown-bar">
              <div className="tier-segment pass" style={{ width: '94.2%' }} title="PASS: 1,265" />
              <div className="tier-segment monitor" style={{ width: '4.1%' }} title="MONITOR: 55" />
              <div className="tier-segment reject" style={{ width: '1.7%' }} title="Measured limit breaches: 23" />
            </div>
            <div className="tier-labels">
              <span>PASS (94.2%)</span>
              <span>MONITOR (4.1%)</span>
              <span>LIMIT BREACH (1.7%)</span>
            </div>
          </div>
        </Card>

        {/* Module B Summary */}
        <Card title="Module B: 168h Prognosis (0–24h Input)" className="summary-module-card">
          <div className="module-summary-body">
            <div className="module-stat-row">
              <span className="stat-label">Model Release:</span>
              <span className="stat-val code-font">ModuleB-FINAL01-RC2 · saved benchmark forecasts</span>
            </div>
            <div className="module-stat-row">
              <span className="stat-label">Prediction Target:</span>
              <span className="stat-val">168h Parametric Drift</span>
            </div>
            <div className="module-stat-row">
              <span className="stat-label">Input Predictors:</span>
              <span className="stat-val">0h + 24h Burn-in only</span>
            </div>
            <div className="module-stat-row">
              <span className="stat-label">Uncertainty Envelope:</span>
              <span className="stat-val text-accent">P95 Upper Bound</span>
            </div>
            <div className="module-stat-row">
              <span className="stat-label">Predicted Wearout Breaches:</span>
              <span className="stat-val text-reject font-bold">5 parts (forecast upper bound crossed limit)</span>
            </div>
            <div className="module-callout">
              <GitBranch size={14} className="text-accent" />
              <span>Module B supplies forecasts and risk flags; final disposition is synthesized in Fusion.</span>
            </div>
          </div>
        </Card>

        {/* Model Evaluation & Performance Summary */}
        <Card title="Module A Only: Screening Performance (168h)" className="summary-module-card">
          <div className="module-summary-body">
            <div className="eval-mini-grid">
              <div className="eval-mini-box">
                <span className="eval-mini-label">RECALL</span>
                <span className="eval-mini-val">{(baseline.recall * 100 || 72.2).toFixed(1)}%</span>
                <span className="eval-mini-sub">{baseline.tp || 65}/90 Defects</span>
              </div>
              <div className="eval-mini-box">
                <span className="eval-mini-label">PRECISION</span>
                <span className="eval-mini-val">{(baseline.precision * 100 || 83.3).toFixed(1)}%</span>
                <span className="eval-mini-sub">{baseline.tp || 65}/({(baseline.tp || 65) + (baseline.fp || 13)}) Flagged</span>
              </div>
              <div className="eval-mini-box highlight">
                <span className="eval-mini-label">F2 SCORE</span>
                <span className="eval-mini-val text-accent">{(baseline.f2 * 100 || 74.2).toFixed(1)}%</span>
                <span className="eval-mini-sub">Recall-Weighted</span>
              </div>
              <div className="eval-mini-box">
                <span className="eval-mini-label">OBSERVED FPR</span>
                <span className="eval-mini-val">{(baseline.fpr * 100 || 1.04).toFixed(2)}%</span>
                <span className="eval-mini-sub">{baseline.fp || 13} False Alarms</span>
              </div>
            </div>

            <div className="decision-callout">
              <div className="decision-header">
                <strong>Decision D2 Operating Point:</strong>
              </div>
              <p className="decision-text">
                These figures count Module A MONITOR and CONFIRMED as alerts: {baseline.fp ?? 13} healthy parts flagged and {baseline.fn ?? 25} defects missed. The {summary?.monitor_count ?? 202} MONITOR and {summary?.reject_count ?? 28} REJECT fusion decisions are a different policy; its precision and false-alarm rate are not shown here.
              </p>
            </div>
          </div>
        </Card>
      </div>

      {/* Fleet Variant Breakdown & Recent Table */}
      <div className="overview-bottom-grid">
        {/* Device Variants */}
        <Card title="Device Variant Distribution (Holdout 18 Lots)" className="variant-card">
          <div className="variant-list">
            {summary?.by_variant && Object.entries(summary.by_variant).map(([variant, count]) => {
              const pct = ((count / summary.total) * 100).toFixed(1);
              return (
                <div key={variant} className="variant-item">
                  <div className="variant-item-header">
                    <span className="variant-name">
                      <Badge variant={variant}>{variant}</Badge>
                    </span>
                    <span className="variant-counts">
                      <strong>{count}</strong> parts ({pct}%)
                    </span>
                  </div>
                  <div className="variant-bar-track">
                    <div className="variant-bar-fill" style={{ width: `${pct}%` }} />
                  </div>
                  <div className="variant-meta">
                    <span>6 Whole Lots</span> · <span>Contiguous ID Allocation</span>
                  </div>
                </div>
              );
            })}
          </div>
        </Card>

        {/* Recent Components */}
        <Card title="Holdout Components Preview" className="recent-card">
          {recentLoading ? (
            <LoadingState message="Loading components preview..." />
          ) : (
            <div className="table-wrapper">
              <table className="mini-table">
                <thead>
                  <tr>
                    <th>Component ID</th>
                    <th>Lot</th>
                    <th>Variant</th>
                    <th>Verdict</th>
                    <th>Tier</th>
                    <th>Risk</th>
                  </tr>
                </thead>
                <tbody>
                  {(recent?.data || []).slice(0, 8).map((row) => (
                    <tr 
                      key={row.component_id} 
                      onClick={() => navigate(`/analyze/${row.component_id}`)}
                      className="clickable-row"
                    >
                      <td className="code-font font-bold text-accent">{row.component_id}</td>
                      <td className="code-font text-muted">{row.lot_id || '-'}</td>
                      <td><Badge variant={row.device_variant || row.variant}>{row.device_variant || row.variant}</Badge></td>
                      <td><Badge status={row.fused_verdict || row.disposition} /></td>
                      <td><span className="tier-tag">{row.evidence_tier || '-'}</span></td>
                      <td className="code-font">{row.score !== null ? row.score?.toFixed(3) : '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className="table-footer-action">
                <button className="btn-view-all" onClick={() => navigate('/components')}>
                  View All 1,343 Components <ArrowRight size={14} />
                </button>
              </div>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
