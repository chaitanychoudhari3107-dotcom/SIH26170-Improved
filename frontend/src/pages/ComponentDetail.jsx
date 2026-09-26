import React, { useEffect, useState, useRef, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';

import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { LoadingState } from '../components/ui/LoadingState';
import { ErrorState } from '../components/ui/ErrorState';
import { api } from '../services/api';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';
import { ArrowLeft, Clock, AlertTriangle, CheckCircle, XCircle } from 'lucide-react';
import './ComponentDetail.css';

const parseReasonCodes = (codesString) => {
  if (!codesString) return [];
  return String(codesString).split('|').map(s => s.trim()).filter(Boolean);
};

export default function ComponentDetail() {
  const { componentId } = useParams();
  const [data, setData] = useState(null);
  const [epochsData, setEpochsData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const pending = useRef(null);
  const fetchData = useCallback(async () => {
    pending.current?.abort();
    const controller = new AbortController(); pending.current = controller;
    setLoading(true); setError(null);
    try {
      const [result, epochRes] = await Promise.all([
        api.get(`/api/analysis/${encodeURIComponent(componentId)}`, {signal:controller.signal}),
        api.get(`/api/analysis/${encodeURIComponent(componentId)}/module-a`, {signal:controller.signal})
      ]);
      if (!controller.signal.aborted) { setData(result); setEpochsData(epochRes?.epochs || {}); }
    } catch (err) { if (!controller.signal.aborted) setError(err); }
    finally { if (!controller.signal.aborted) setLoading(false); }
  }, [componentId]);
  useEffect(() => { fetchData(); return () => pending.current?.abort(); }, [fetchData]);

  if (loading) return <LoadingState message={`Analyzing component ${componentId}...`} />;
  if (error) return <ErrorState error={error} onRetry={fetchData} />;
  if (!data) return null;

  const { 
    module_a, 
    module_b, 
    evidence, 
    historical_measurements, 
    lot_id, 
    device_variant, 
    device_family,
    fused_verdict 
  } = data;

  const aReasons = parseReasonCodes(module_a?.reason_codes || module_a?.module_a_reason_codes);
  const bReasons = parseReasonCodes(module_b?.reason_codes || module_b?.module_b_reason_codes);
  
  const parameters = [
    { key: 'IDDQ', label: 'IDDQ Quiescent Current', unit: 'µA' },
    { key: 'Input_Leakage_Current', label: 'Input Leakage Current', unit: 'µA' },
    { key: 'Active_Supply_Current', label: 'Active Supply Current', unit: 'µA' },
    { key: 'Propagation_Delay', label: 'Propagation Delay', unit: 'ns' },
    { key: 'Output_Rise_Time', label: 'Output Rise Time', unit: 'ns' },
    { key: 'Output_Fall_Time', label: 'Output Fall Time', unit: 'ns' }
  ];

  const disposition = module_a?.disposition || module_a?.module_a_disposition || 'UNKNOWN';
  const tier = module_a?.evidence_tier || module_a?.module_a_evidence_tier || 'UNKNOWN';
  const riskScore = module_a?.score ?? module_a?.module_a_score ?? 0;
  const finalVerdict = fused_verdict || (tier === 'CONFIRMED' ? 'REJECT' : disposition);
  const monitorExplanation = disposition === 'MONITOR'
    ? `Module A flagged a lot-relative anomaly in ${lot_id}; send this component for QA review.`
    : bReasons.some(code => code.startsWith('B_WIDE_ENVELOPE'))
      ? 'The 0h/24h forecast has a wide uncertainty envelope; send this component for QA review.'
      : bReasons.some(code => code.startsWith('B_LOT_OUTLIER_24H'))
        ? 'The 24h reading differs from its lot peers; send this component for QA review.'
        : bReasons.some(code => code.startsWith('B_HIGH_FORECAST_DRIFT'))
          ? 'The early forecast indicates elevated drift; send this component for QA review.'
          : 'A configured screening indicator requires QA review; inspect the reason codes below.';

  return (
    <div className="page-detail">
      <div className="detail-breadcrumb">
        <Link to="/components" className="back-link">
          <ArrowLeft size={16} /> Back to Components Catalog
        </Link>
      </div>

      {/* Main Component Header */}
      <header className="detail-header">
        <div className="detail-header-left">
          <div className="detail-id-row">
            <h1 className="detail-title code-font">{componentId}</h1>
            <Badge status={finalVerdict} size="lg">FUSED: {finalVerdict}</Badge>
            <Badge status={tier} size="lg">TIER: {tier === 'CONFIRMED' ? 'MEASURED LIMIT BREACH' : tier}</Badge>
          </div>
          <div className="detail-meta">
            {lot_id && <span className="meta-chip">LOT: <strong>{lot_id}</strong></span>}
            {device_variant && <span className="meta-chip">VARIANT: <strong>{device_variant}</strong></span>}
            {device_family && <span className="meta-chip">FAMILY: <strong>{device_family}</strong></span>}
            <span className="meta-chip">DATASET: <strong>SIH26170-FINAL-01</strong></span>
          </div>
        </div>
      </header>

      {/* Fusion Verdict Banner */}
      <div className={`verdict-banner ${finalVerdict.toLowerCase()}`}>
        <div className="verdict-banner-icon">
          {finalVerdict === 'PASS' && <CheckCircle size={24} className="text-pass" />}
          {finalVerdict === 'MONITOR' && <AlertTriangle size={24} className="text-monitor" />}
          {finalVerdict === 'REJECT' && <XCircle size={24} className="text-reject" />}
        </div>
        <div className="verdict-banner-content">
          <div className="verdict-banner-title">
            FUSED RELIABILITY VERDICT: {finalVerdict}
          </div>
          <div className="verdict-banner-desc">
            {finalVerdict === 'REJECT' && (
              tier === 'CONFIRMED' 
                ? `Measured specification limit exceeded on ${module_a?.primary_parameter || 'one or more parameters'} in this synthetic benchmark. The saved explorer policy rejects this part; physical defect status requires QA verification.`
                : `The saved explorer policy calls this a REJECT because a forecast or its upper bound crossed a limit. The operational workspace treats forecast-only risk as HOLD for engineering review.`
            )}
            {finalVerdict === 'MONITOR' && (
              monitorExplanation
            )}
            {finalVerdict === 'PASS' && (
              `No alert under the current screening policy. This result does not guarantee future reliability.`
            )}
          </div>
        </div>
      </div>

      {/* 3 Core Analytical Diagnostic Cards */}
      <div className="detail-grid">
        {/* Module A Card */}
        <Card title="Module A: Lot-relative screening + limit checks (168h)" className="module-card">
          <div className="score-section">
            <div className="score-label">
              <span>Screening Risk Score</span>
              <span className="code-font font-bold">
                {typeof riskScore === 'number' ? riskScore.toFixed(4) : riskScore}
              </span>
            </div>
            <div className="score-bar-bg">
              <div 
                className="score-bar-fill" 
                style={{ 
                  width: `${Math.min(100, Math.max(0, (riskScore || 0) * 100))}%`,
                  backgroundColor: finalVerdict === 'PASS' ? 'var(--status-pass)' : (finalVerdict === 'REJECT' ? 'var(--status-reject)' : 'var(--status-monitor)')
                }} 
              />
            </div>
            <div className="score-scale-hint">
              <span>0.00 Nominal</span>
              <span>0.90 Hard-limit floor</span>
              <span>1.00 Score maximum</span>
            </div>
            <p className="section-subtitle">The 0.90 floor marks measured limit breaches in the synthetic benchmark; MONITOR can also arise from separate lot-relative evidence at a lower displayed score. The internal CONFIRMED tier is not a QA-confirmed physical defect.</p>
          </div>
          
          <div className="detail-row">
            <span className="label">Module A Disposition:</span>
            <span className="value"><Badge status={disposition}>{disposition}</Badge></span>
          </div>
          <div className="detail-row">
            <span className="label">Evidence Tier:</span>
            <span className="value font-bold">{tier}</span>
          </div>
          <div className="detail-row">
            <span className="label">Primary Flagged Parameter:</span>
            <span className="value code-font text-accent font-bold">
              {module_a?.primary_parameter || module_a?.module_a_primary_parameter || 'None'}
            </span>
          </div>
          {module_a?.statistical_score != null && (
            <div className="detail-row">
              <span className="label">Statistical Rank Distance:</span>
              <span className="value code-font">{Number(module_a.statistical_score).toFixed(4)}</span>
            </div>
          )}
          {module_a?.spec_exceedance_ratio != null && (
            <div className="detail-row">
              <span className="label">Spec Exceedance Ratio:</span>
              <span className="value code-font">{Number(module_a.spec_exceedance_ratio).toFixed(4)}</span>
            </div>
          )}
          {module_a?.analysis_status && (
            <div className="detail-row">
              <span className="label">Execution Status:</span>
              <span className="value code-font">{module_a.analysis_status}</span>
            </div>
          )}

          <div className="reason-section">
            <div className="reason-title">Module A Reason Codes:</div>
            <div className="reason-codes">
              {aReasons.length > 0 ? (
                aReasons.map(code => (
                  <span key={code} className={`reason-tag ${code.includes('STATIC') || code.includes('CONFIRMED') ? 'alert-tag' : ''}`}>
                    {code}
                  </span>
                ))
              ) : (
                <span className="reason-tag pass-tag">A_NOMINAL (No Anomaly)</span>
              )}
            </div>
          </div>
        </Card>

        {/* Evidence & Explainability */}
        <Card title="Fusion Synthesis & Explainability" className="module-card">
          <div className="evidence-header">
            <span className="label">Cross-Module Status:</span>
            <Badge variant={evidence?.b_evidence_status || data?.b_evidence_status || 'NOMINAL'}>
              {evidence?.b_evidence_status || data?.b_evidence_status || 'NOMINAL'}
            </Badge>
          </div>
          
          <div className="evidence-explanation-box">
            <div className="explanation-label">Engineering Assessment:</div>
            <p className="evidence-explanation">
              {evidence?.explanation || 'All measured parameters conform strictly to electrical specification thresholds with normal drift envelopes.'}
            </p>
          </div>

          <div className="reason-section">
            <div className="reason-title">Module B Indicator Codes:</div>
            <div className="reason-codes">
              {bReasons.length > 0 ? (
                bReasons.map(code => (
                  <span key={code} className="reason-tag b-tag">{code}</span>
                ))
              ) : (
                <span className="reason-tag pass-tag">B_CLEAR (Nominal Prognosis)</span>
              )}
            </div>
          </div>

          <div className="corroboration-box">
            <span className="corroboration-title">Corroboration Logic:</span>
            <span className="corroboration-text">
              {tier === 'CONFIRMED'
                ? 'Module A marks an observed specification exceedance in this synthetic benchmark (internal CONFIRMED_FLOOR = 0.90). Hardware defect status still requires QA evidence.'
                : 'Module A screening and Module B 0h-24h trend projection are synthesized under Decision Fusion protocol.'}
            </span>
          </div>
        </Card>

        {/* Multi-Epoch Screening Evolution */}
        <Card title="Multi-Epoch Screening Evolution (Module A)" className="module-card">
          <div className="epochs-progression-list">
            {[0, 24, 96, 168].map(epoch => {
              const epochData = epochsData?.[epoch];
              const epScore = epochData?.module_a_score ?? (epoch === 168 ? riskScore : null);
              const epTier = epochData?.module_a_evidence_tier ?? (epoch === 168 ? tier : null);
              const epDisp = epochData?.module_a_disposition ?? (epoch === 168 ? disposition : null);

              return (
                <div key={epoch} className="epoch-prog-row">
                  <div className="epoch-prog-badge">
                    <span className="code-font font-bold">{epoch}h</span>
                  </div>
                  <div className="epoch-prog-metrics">
                    <div className="epoch-prog-val">
                      <span className="epoch-lbl">Score:</span>
                      <strong className="code-font">{epScore !== null ? Number(epScore).toFixed(4) : '—'}</strong>
                    </div>
                    <div className="epoch-prog-tier">
                      <span className="epoch-lbl">Tier:</span>
                      <span>{epTier || '—'}</span>
                    </div>
                  </div>
                  <div className="epoch-prog-disp">
                    {epDisp ? <Badge status={epDisp} size="sm">{epDisp}</Badge> : <span className="text-muted">—</span>}
                  </div>
                </div>
              );
            })}
          </div>
          <div className="epoch-prog-note">
            <Clock size={14} className="text-accent" />
            <span>Screening results at each burn-in checkpoint; scores need not rise monotonically.</span>
          </div>
        </Card>
      </div>

      {/* Module B Parameter Predictions Grid */}
      <div className="section-header">
        <div>
          <h2 className="section-title">Module B: 168h Prognostic Drift Predictions</h2>
          <p className="section-subtitle">Forecasted physical parameter values and P95 uncertainty intervals derived from 0h + 24h readings</p>
        </div>
      </div>

      <div className="parameters-grid">
        {parameters.map(({ key: param, label, unit }) => {
          const pred = module_b?.predictions?.[param]?.predicted_168h ?? module_b?.[`predicted_${param}_168h`];
          const p95 = module_b?.predictions?.[param]?.p95_168h ?? module_b?.[`module_b_p95_${param}_168h`];
          const limit = evidence?.evidence?.[param]?.limit ?? evidence?.[`evidence_${param}_limit`];
          const delta = evidence?.evidence?.[param]?.pred_rel_delta_from_24h ?? evidence?.[`evidence_${param}_pred_rel_delta_from_24h`];
          const lotdev = evidence?.evidence?.[param]?.lot_rel_dev_24h ?? evidence?.[`evidence_${param}_lot_rel_dev_24h`];
          const isPrimary = (module_b?.primary_parameter === param);
          const actual168 = historical_measurements?.find(m => m.epoch_h === 168)?.[param];
          const exceedsLimit = limit && p95 && (p95 >= limit);

          return (
            <Card 
              key={param} 
              className={`param-card ${isPrimary ? 'primary-param' : ''} ${exceedsLimit ? 'exceeds-limit' : ''}`}
              title={`${label} (${unit})`}
            >
              {isPrimary && <div className="primary-pill">Primary Drift Driver</div>}
              
              <div className="param-stats">
                <div className="stat">
                  <span className="stat-label">Predicted 168h</span>
                  <span className="stat-val code-font">{pred != null ? Number(pred).toFixed(3) : '-'}</span>
                </div>
                <div className="stat">
                  <span className="stat-label">Observed 168h (retrospective)</span>
                  <span className="stat-val code-font">{actual168 != null ? Number(actual168).toFixed(3) : '—'}</span>
                </div>
                <div className="stat">
                  <span className="stat-label">P95 Envelope</span>
                  <span className={`stat-val code-font ${exceedsLimit ? 'text-reject font-bold' : ''}`}>
                    {p95 != null ? Number(p95).toFixed(3) : '-'}
                  </span>
                </div>
                <div className="stat">
                  <span className="stat-label">Static max (when defined)</span>
                  <span className="stat-val code-font">{limit != null ? Number(limit).toFixed(2) : 'Not specified'}</span>
                </div>
              </div>

              <div className="param-secondary-stats">
                {delta != null && (
                  <span className="sub-stat">24h→168h Drift: <strong className="code-font">{(Number(delta) * 100).toFixed(1)}%</strong></span>
                )}
                {lotdev != null && (
                  <span className="sub-stat">Lot Centroid Dev: <strong className="code-font">{(Number(lotdev) * 100).toFixed(1)}%</strong></span>
                )}
              </div>
              
              {limit && p95 && (
                <div className="chart-container">
                  <div className="chart-legend">
                    <span>Upper Bound vs Spec Limit ({Number(limit).toFixed(1)} {unit})</span>
                  </div>
                  <ResponsiveContainer width="100%" height={44}>
                    <BarChart layout="vertical" data={[{ name: param, value: Number(p95) }]} margin={{ top: 0, right: 20, left: 0, bottom: 0 }}>
                      <XAxis type="number" domain={[0, Math.max(Number(limit) * 1.15, Number(p95) * 1.15)]} hide />
                      <YAxis type="category" dataKey="name" hide />
                      <Tooltip formatter={(value) => `${Number(value).toFixed(3)} ${unit}`} />
                      <ReferenceLine x={Number(limit)} stroke="var(--status-reject)" strokeDasharray="3 3" />
                      <Bar 
                        dataKey="value" 
                        fill={Number(p95) > Number(limit) ? 'var(--status-reject)' : 'var(--accent)'} 
                        radius={[0, 4, 4, 0]} 
                        barSize={14} 
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}
            </Card>
          );
        })}
      </div>

      {/* Historical Burn-in Trajectory Measurements */}
      {historical_measurements && historical_measurements.length > 0 && (
        <div className="historical-section">
          <div className="section-header">
            <div>
              <h2 className="section-title">Parametric Measurement History (Burn-in Trajectory)</h2>
              <p className="section-subtitle">Observed synthetic benchmark measurements at all available checkpoints. The 96h and 168h values are shown for retrospective review; they are not Module B inputs.</p>
            </div>
          </div>

          <Card>
            <div className="table-responsive">
              <table className="measurements-table">
                <thead>
                  <tr>
                    <th>Epoch</th>
                    {parameters.map(p => (
                      <th key={p.key}>{p.label} ({p.unit})</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {historical_measurements.map(m => (
                    <tr key={m.epoch_h}>
                      <td><span className="epoch-badge code-font">{m.epoch_h}h</span></td>
                      {parameters.map(p => (
                        <td key={p.key} className="code-font">
                          {m[p.key] != null ? Number(m[p.key]).toFixed(3) : '-'}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
