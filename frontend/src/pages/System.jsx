import React, { useState } from 'react';
import { PageHeader } from '../components/layout/PageHeader';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { LoadingState } from '../components/ui/LoadingState';
import { ErrorState } from '../components/ui/ErrorState';
import { useApi } from '../hooks/useApi';
import { Server, Database, ShieldCheck, Cpu, FileText, RefreshCw, ChevronRight, Search } from 'lucide-react';
import './System.css';

export default function System() {
  const { data: statusData, loading: statusLoading, error: statusError, refetch: refetchStatus } = useApi('/api/system/status');
  const { data: archData, loading: archLoading } = useApi('/api/pipeline/architecture');
  const { data: specsData, loading: specsLoading } = useApi('/api/reference/specs');
  const { data: dictData, loading: dictLoading } = useApi('/api/reference/dictionary');

  const [activeStageId, setActiveStageId] = useState(1);
  const [activeRefTab, setActiveRefTab] = useState('specs');
  const [dictSearch, setDictSearch] = useState('');
  const [specVariantFilter, setSpecVariantFilter] = useState('ALL');

  if (statusLoading || archLoading) return <LoadingState message="Loading system telemetry and pipeline lineage..." />;
  if (statusError) return <ErrorState error={statusError} onRetry={refetchStatus} />;

  const stages = archData?.stages || [
    { id: 1, name: 'Raw Holdout Partition', source: 'incoming/ (18 Whole Lots, 1,343 Parts)', description: 'Whole-lot holdout split (LOTSPLIT-05) isolating 6 lots per variant with zero leakage.', status: 'FROZEN_BENCHMARK' },
    { id: 2, name: 'Epoch Partitioning', source: '0h, 24h, 96h, 168h Physical Test Data', description: 'Parametric measurements across 6 critical physical channels.', status: 'INGESTED' },
    { id: 3, name: 'Module A Screening Scorer', source: 'Multi-Epoch Static & Lot Outlier Classifier', description: 'Static datasheet limit checking combined with robust lot-relative Mahalanobis outlier scoring.', status: 'EXECUTED_168H' },
    { id: 4, name: 'Module B Prognosis Engine', source: '0h-24h Early Burn-in Readings', description: 'Projections estimating 168h completion values with P95 uncertainty intervals.', status: 'EXECUTED_WIDE' },
    { id: 5, name: 'Decision Fusion Layer', source: 'Fusion_Joined_Holdout.csv', description: 'Cross-module corroboration enforcing CONFIRMED -> REJECT, forecast breaches -> REJECT, drift -> MONITOR, compliant -> PASS.', status: 'SYNTHESIZED' },
    { id: 6, name: 'FastAPI Analytical Engine', source: 'backend/ (Port 8001)', description: 'In-memory analytics server providing instant search, deep-dive evaluation, and operational isolation.', status: 'ONLINE' },
    { id: 7, name: 'Interactive Application', source: 'frontend/ (Port 5174)', description: 'Modern dark-theme analytical console for fleet monitoring and diagnostics.', status: 'ONLINE' }
  ];

  const currentStage = stages.find(s => s.id === activeStageId) || stages[0];

  const filteredSpecs = (specsData || []).filter(item => {
    if (specVariantFilter === 'ALL') return true;
    return item.device_variant === specVariantFilter;
  });

  const filteredDict = (dictData || []).filter(item => {
    if (!dictSearch.trim()) return true;
    const q = dictSearch.toLowerCase();
    return (item.column_name || '').toLowerCase().includes(q) ||
           (item.description || '').toLowerCase().includes(q) ||
           (item.module_b_rule || '').toLowerCase().includes(q);
  });

  return (
    <div className="page-system">
      <PageHeader 
        title="Architecture & Lineage" 
        subtitle="End-to-end data pipeline, module contracts, physical test boundaries, and runtime service health."
      >
        <button className="btn-refresh" onClick={refetchStatus}>
          <RefreshCw size={14} /> Refresh Telemetry
        </button>
      </PageHeader>

      {/* Top Telemetry Strip */}
      <div className="telemetry-grid">
        <div className="telemetry-card">
          <div className="telemetry-header">
            <span className="telemetry-icon-box"><Server size={18} /></span>
            <span className="telemetry-title">API Analytical Engine</span>
            <Badge status="PASS">ONLINE</Badge>
          </div>
          <div className="telemetry-val">FastAPI :8001</div>
          <div className="telemetry-meta">
            <span>Uptime: {statusData?.uptime ? `${Math.floor(statusData.uptime / 3600)}h ${Math.floor((statusData.uptime % 3600) / 60)}m` : 'Active'}</span>
            <span>Env: {statusData?.environment || 'production'}</span>
          </div>
        </div>

        <div className="telemetry-card">
          <div className="telemetry-header">
            <span className="telemetry-icon-box"><Database size={18} /></span>
            <span className="telemetry-title">Frozen Benchmark</span>
            <span className="badge-pill immutable">IMMUTABLE</span>
          </div>
          <div className="telemetry-val">{statusData?.fusion_records?.toLocaleString() || '1,343'} Parts</div>
          <div className="telemetry-meta">
            <span>Dataset: {statusData?.dataset_info?.id || 'SIH26170-FINAL-01'}</span>
            <span>18 Holdout Lots</span>
          </div>
        </div>

        <div className="telemetry-card">
          <div className="telemetry-header">
            <span className="telemetry-icon-box"><ShieldCheck size={18} /></span>
            <span className="telemetry-title">Operational Isolation</span>
            <Badge status="PASS">ACTIVE</Badge>
          </div>
          <div className="telemetry-val">operational.db</div>
          <div className="telemetry-meta">
            <span>Separate from benchmark files</span>
            <span>SQLite WAL Mode</span>
          </div>
        </div>

        <div className="telemetry-card">
          <div className="telemetry-header">
            <span className="telemetry-icon-box"><Cpu size={18} /></span>
            <span className="telemetry-title">Module Contracts</span>
            <Badge status="PASS">SYNTHESIZED</Badge>
          </div>
          <div className="telemetry-val">A + B Fusion</div>
          <div className="telemetry-meta">
            <span>Module A: 13 Attributes</span>
            <span>Module B: 6 Channels</span>
          </div>
        </div>
      </div>

      {/* 7-Stage Architectural Data Lineage Interactive Diagram */}
      <Card title="Authoritative Data Lineage & Pipeline Stages" subtitle="Click any stage to inspect its inputs, transformation logic, and architectural contract.">
        <div className="lineage-interactive-container">
          <div className="lineage-steps-bar">
            {stages.map((stage, idx) => {
              const isActive = stage.id === activeStageId;
              return (
                <button 
                  key={stage.id} 
                  className={`lineage-step-node ${isActive ? 'active' : ''}`}
                  onClick={() => setActiveStageId(stage.id)}
                >
                  <div className="step-num-pill">{stage.id}</div>
                  <div className="step-content-preview">
                    <span className="step-label">{stage.name}</span>
                    <span className="step-status-tag">{stage.status}</span>
                  </div>
                  {idx < stages.length - 1 && <ChevronRight size={16} className="step-arrow-icon" />}
                </button>
              );
            })}
          </div>

          {/* Active Stage Deep-Dive Drawer */}
          <div className="stage-detail-panel">
            <div className="stage-detail-header">
              <div className="stage-num-badge">Stage {currentStage.id} of 7</div>
              <h3 className="stage-title">{currentStage.name}</h3>
              <Badge status={currentStage.status.includes('ONLINE') || currentStage.status.includes('FROZEN') ? 'PASS' : 'MONITOR'}>
                {currentStage.status}
              </Badge>
            </div>

            <div className="stage-detail-body">
              <div className="stage-info-item">
                <span className="stage-info-label">Data Source / Artifact:</span>
                <span className="stage-info-val mono">{currentStage.source}</span>
              </div>
              <div className="stage-info-item">
                <span className="stage-info-label">Architectural Role:</span>
                <span className="stage-info-val">{currentStage.description}</span>
              </div>
            </div>

            {/* Contextual deep dive by stage */}
            <div className="stage-contract-box">
              {currentStage.id === 1 && (
                <div className="contract-content">
                  <h4>Stage 1: Holdout Integrity & Partitioning Guarantee</h4>
                  <p>
                    The frozen holdout partition isolates exactly <strong>18 entire production lots</strong> (6 CMOS_A lots, 6 CMOS_B lots, 6 CMOS_C lots) 
                    comprising <strong>1,343 unique components</strong> (C00158 through C05320). No components or lots in this holdout partition were utilized during 
                    feature selection, statistical calibration, or threshold tuning.
                  </p>
                  <div className="contract-tags">
                    <span className="contract-tag">Partition Protocol: LOTSPLIT-05</span>
                    <span className="contract-tag">Total Parts: 1,343</span>
                    <span className="contract-tag">Lots: 18 Entire Batches</span>
                    <span className="contract-tag">Whole-lot separation</span>
                  </div>
                </div>
              )}

              {currentStage.id === 2 && (
                <div className="contract-content">
                  <h4>Stage 2: Parametric Test Epoch Structure</h4>
                  <p>
                    The synthetic benchmark represents 4 standardized burn-in measurement checkpoints:
                    <strong> 0h (baseline pre-stress)</strong>, <strong>24h (early burn-in screening)</strong>, 
                    <strong> 96h (intermediate wearout checkpoint)</strong>, and <strong>168h (qualification completion)</strong>.
                    Each epoch provides 6 simulated electrical and timing measurements under the benchmark's specified conditions.
                  </p>
                  <div className="contract-tags">
                    <span className="contract-tag">0h: Baseline T0</span>
                    <span className="contract-tag">24h: Prognostic Pivot</span>
                    <span className="contract-tag">96h: Degradation Check</span>
                    <span className="contract-tag">168h: Final Gate</span>
                  </div>
                </div>
              )}

              {currentStage.id === 3 && (
                <div className="contract-content">
                  <h4>Stage 3: Module A Multi-Epoch Screening Contract</h4>
                  <p>
                    Module A evaluates parts across a <strong>13-column contract schema</strong>. It calculates static datasheet limit exceedances 
                    alongside robust lot-relative Mahalanobis outlier distances. If static limits are breached, parts are assigned evidence tier 
                    <span className="code-font red">CONFIRMED</span> with score &ge; 0.90. This internal tier means a measured limit breach in the synthetic benchmark, not a QA-confirmed physical defect. Parts with excessive statistical lot drift are flagged 
                    <span className="code-font amber">MONITOR</span>.
                  </p>
                  <div className="contract-tags">
                    <span className="contract-tag">Scored At: 168h</span>
                    <span className="contract-tag">0.900: hard-limit score floor, not statistical alert cutoff</span>
                    <span className="contract-tag">Output Tiers: PASS / MONITOR / CONFIRMED</span>
                  </div>
                </div>
              )}

              {currentStage.id === 4 && (
                <div className="contract-content">
                  <h4>Stage 4: Module B Prognostic Forecasting Engine</h4>
                  <p>
                    Module B consumes only <strong>0h and 24h readings</strong> to project 168h values and P95 upper confidence bounds.
                    It raises prognostic warning codes: <span className="code-font">B_HIGH_FORECAST_DRIFT</span>, 
                    <span className="code-font">B_WIDE_ENVELOPE</span>, and <span className="code-font">B_LOT_OUTLIER_24H</span>. 
                    If a prediction or its P95 upper bound crosses a static limit, the current fusion policy withholds that component for review. A bound crossing does not confirm measured wearout.
                  </p>
                  <div className="contract-tags">
                    <span className="contract-tag">Input: 0h & 24h Early Burn-in</span>
                    <span className="contract-tag">Output: Predicted 168h + P95 Bound</span>
                    <span className="contract-tag">Channels: 6 Physical Parameters</span>
                  </div>
                </div>
              )}

              {currentStage.id === 5 && (
                <div className="contract-content">
                  <h4>Stage 5: Rule-Based Decision Fusion Matrix</h4>
                  <p>
                    The saved benchmark explorer combines frozen Module A and Module B outputs using the rules below. The operational workspace uses a separate policy that calls forecast-only risk HOLD; its measured 24h and 168h results are under Models &amp; Metrics.
                  </p>
                  <ul className="fusion-rules-list">
                    <li><strong className="text-reject">REJECT (28 parts):</strong> Module A tier is <code>CONFIRMED</code> (23 observed hard-limit breaches) OR Module B prediction / upper bound crosses a limit (5 forecast-only holds). These evidence types are shown separately.</li>
                    <li><strong className="text-monitor">MONITOR (202 parts):</strong> Module A tier is <code>MONITOR</code> (statistical drift) OR Module B issues warning codes without hard limit violations.</li>
                    <li><strong className="text-pass">PASS (1,113 parts):</strong> Neither module triggers this policy. PASS is not a guarantee of future reliability.</li>
                  </ul>
                </div>
              )}

              {currentStage.id === 6 && (
                <div className="contract-content">
                  <h4>Stage 6: In-Memory Analytical Server (FastAPI)</h4>
                  <p>
                    FastAPI serves stored benchmark outputs and separate operational records. Operational entry does not yet run the frozen models on newly entered devices.
                  </p>
                  <div className="contract-tags">
                    <span className="contract-tag">Port: 8001</span>
                    <span className="contract-tag">Latency: not independently benchmarked</span>
                  </div>
                </div>
              )}

              {currentStage.id === 7 && (
                <div className="contract-content">
                  <h4>Stage 7: Interactive Analytical Console</h4>
                  <p>
                    Built with React and designed after the LATENT obsidian design language:
                    deep obsidian backgrounds, micro-borders, clean tabular density, interactive confusion matrix toggles, 
                    multi-epoch burn-in trajectory graphs, and operational record ingestion wizards.
                  </p>
                  <div className="contract-tags">
                    <span className="contract-tag">Port: 5174</span>
                    <span className="contract-tag">Theme: Obsidian / Cyan</span>
                    <span className="contract-tag">Reactivity: Real-time API Hooks</span>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </Card>

      {/* Reference Data & Contract Explorer */}
      <Card 
        title="Physical Reference Specifications & Data Dictionary" 
        subtitle="Authoritative device limits, working conditions, and schema definitions governing the pipeline."
      >
        <div className="ref-tabs-toolbar">
          <div className="ref-nav-tabs">
            <button 
              className={`ref-tab ${activeRefTab === 'specs' ? 'active' : ''}`}
              onClick={() => setActiveRefTab('specs')}
            >
              <Cpu size={15} /> Device Physical Specs ({filteredSpecs.length})
            </button>
            <button 
              className={`ref-tab ${activeRefTab === 'dict' ? 'active' : ''}`}
              onClick={() => setActiveRefTab('dict')}
            >
              <FileText size={15} /> Schema Data Dictionary ({filteredDict.length})
            </button>
          </div>

          {activeRefTab === 'specs' && (
            <div className="ref-filter-group">
              <span className="filter-label">Variant:</span>
              {['ALL', 'CMOS_A', 'CMOS_B', 'CMOS_C'].map(v => (
                <button 
                  key={v}
                  className={`filter-chip ${specVariantFilter === v ? 'active' : ''}`}
                  onClick={() => setSpecVariantFilter(v)}
                >
                  {v}
                </button>
              ))}
            </div>
          )}

          {activeRefTab === 'dict' && (
            <div className="dict-search-wrap">
              <Search size={14} className="search-icon" />
              <input 
                type="text" 
                placeholder="Search attributes, units, or descriptions..." 
                value={dictSearch}
                onChange={e => setDictSearch(e.target.value)}
                className="dict-search-input"
              />
            </div>
          )}
        </div>

        {activeRefTab === 'specs' ? (
          specsLoading ? <LoadingState message="Loading device physical specifications..." /> : (
            <div className="table-responsive">
              <table className="ref-table">
                <thead>
                  <tr>
                    <th>Variant</th>
                    <th>Parameter</th>
                    <th>Unit</th>
                    <th>Vcc (V)</th>
                    <th>Baseline (0h)</th>
                    <th>Static Max Limit</th>
                    <th>Reference Silicon</th>
                    <th>Test Condition</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredSpecs.map((s, idx) => (
                    <tr key={idx}>
                      <td><Badge>{s.device_variant}</Badge></td>
                      <td><strong className="mono">{s.parameter}</strong></td>
                      <td><span className="unit-pill">{s.unit}</span></td>
                      <td className="mono">{s.working_vcc_V}V</td>
                      <td className="mono">{s.synthetic_baseline_0h}</td>
                      <td className="mono font-bold text-accent">{s.static_spec_max}</td>
                      <td className="text-secondary">{s.reference_device}</td>
                      <td className="text-muted text-sm">{s.test_condition}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
        ) : (
          dictLoading ? <LoadingState message="Loading schema data dictionary..." /> : (
            <div className="table-responsive">
              <table className="ref-table">
                <thead>
                  <tr>
                    <th>Column Attribute</th>
                    <th>Type</th>
                    <th>Unit</th>
                    <th>Description</th>
                    <th>Module B Rule / Purpose</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredDict.map((d, idx) => (
                    <tr key={idx}>
                      <td><strong className="mono text-accent">{d.column_name}</strong></td>
                      <td><span className="type-tag">{d.type}</span></td>
                      <td><span className="unit-pill">{d.unit || '-'}</span></td>
                      <td className="desc-cell">{d.description}</td>
                      <td className="rule-cell">{d.module_b_rule || '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
        )}
      </Card>

      {/* Isolation & Architectural Verification Footnote */}
      <div className="system-guarantee-banner">
        <ShieldCheck size={24} className="banner-shield-icon" />
        <div className="banner-content">
          <h4>Architectural Security & Isolation Verification</h4>
          <p>
            Benchmark artifacts are loaded from <code>data/final/</code> while operational measurements are entered into <code>operational.db</code>. The two stores are separate; this page does not independently attest to cryptographic locking or all stages of training provenance.
          </p>
        </div>
      </div>
    </div>
  );
}
