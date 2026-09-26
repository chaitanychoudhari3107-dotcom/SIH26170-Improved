import React from 'react';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { LoadingState } from '../components/ui/LoadingState';
import { ErrorState } from '../components/ui/ErrorState';
import { useApi } from '../hooks/useApi';
import { Sliders } from 'lucide-react';
import OperationalEvaluation from '../components/OperationalEvaluation';
import './Models.css';

export default function Models() {
  const { data: modelInfo, loading: infoLoading, error: infoError } = useApi('/api/models/info');
  const { data: evalMetrics, loading: evalLoading, error: evalError, refetch } = useApi('/api/models/evaluation');

  if (infoLoading || evalLoading) return <LoadingState message="Loading model verification telemetry and metrics..." />;
  if (infoError || evalError) return <ErrorState error={infoError || evalError} onRetry={refetch} />;

  const baseline = evalMetrics?.baseline || {};
  const epochs = evalMetrics?.epochs || [];
  const variants = evalMetrics?.by_variant || [];
  const forecasts = evalMetrics?.module_b_forecasts || [];
  const modA = modelInfo?.module_a || {};
  const modB = modelInfo?.module_b || {};

  const currentPoint = baseline;

  return (
    <div className="page-models">
      <div className="models-intro"><span>MEASURED EVIDENCE / SYNTHETIC HOLDOUT</span><h1>Screening results, including the misses.</h1><p>Start with the exact operational review rule used by the workspace. Then inspect its tradeoff, difficult challenge cases, and forecast errors. The separately frozen Module A and B release studies are available below.</p></div>

      <OperationalEvaluation />

      <details className="models-release-details"><summary><span>02 / RELEASE ARTIFACTS</span><strong>Explore separate frozen Module A and Module B evaluations</strong><small>Expand technical tables ↓</small></summary><div className="models-release-content">
      <h2>Separate frozen Module A release evaluation</h2>
      <p className="models-scope-note">The cards and matrix below describe Module A at 168h; they are not the operational review-gate matrix above. The Module B release forecast table uses a different saved artifact from the operational rehearsal fit. “CONFIRMED” is an internal Module A tier for a measured limit breach in synthetic data, not a QA-confirmed physical defect.</p>
      {/* Top Headline Telemetry Strip */}
      <div className="eval-strip-grid">
        <div className="eval-strip-card">
          <span className="strip-label">F2 SCORE (RECALL-FOCUSED)</span>
          <div className="strip-val text-accent">{(baseline.f2 * 100).toFixed(2)}%</div>
          <span className="strip-sub">Module A only · synthetic holdout</span>
        </div>
        <div className="eval-strip-card">
          <span className="strip-label">RECALL / SENSITIVITY</span>
          <div className="strip-val text-pass">{(baseline.recall * 100).toFixed(2)}%</div>
          <span className="strip-sub">{baseline.tp} / {baseline.positives} Defects Flagged</span>
        </div>
        <div className="eval-strip-card">
          <span className="strip-label">PRECISION (PPV)</span>
          <div className="strip-val">{(baseline.precision * 100).toFixed(2)}%</div>
          <span className="strip-sub">{baseline.tp} / {baseline.flagged} Alerts True</span>
        </div>
        <div className="eval-strip-card">
          <span className="strip-label">FPR (FALSE ALARM RATE)</span>
          <div className="strip-val">{(baseline.fpr * 100).toFixed(2)}%</div>
          <span className="strip-sub">{baseline.fp} / {baseline.negatives} Healthy Parts</span>
        </div>
        <div className="eval-strip-card">
          <span className="strip-label">ACCURACY</span>
          <div className="strip-val">{(baseline.accuracy * 100).toFixed(2)}%</div>
          <span className="strip-sub">{baseline.tp + baseline.tn} / {baseline.positives + baseline.negatives} Correct</span>
        </div>
      </div>

      <Card title="Module B: 168h Forecast Accuracy (Synthetic Holdout)" className="subgrid-card">
        <p className="section-subtitle">Retrospective evaluation of forecasts made from 0h and 24h readings. MAE is the average absolute prediction error in the parameter's unit. The comparison baseline assumes the 24h measurement remains unchanged. Upper coverage is the share of actual 168h readings below the supplied P95 upper bound; observed coverage is not uniformly 95%.</p>
        <div className="table-responsive">
          <table className="comparison-table">
            <thead><tr><th>Parameter</th><th>Parts</th><th>Forecast MAE</th><th>Unchanged 24h MAE</th><th>P95 upper coverage</th><th>Above upper bound</th></tr></thead>
            <tbody>{forecasts.map(item => (
              <tr key={item.parameter}>
                <td>{item.parameter.replaceAll('_', ' ')} ({item.unit})</td>
                <td>{item.n}</td>
                <td>{item.mae.toFixed(4)}</td>
                <td>{item.unchanged_24h_mae.toFixed(4)}</td>
                <td>{(item.upper_coverage * 100).toFixed(1)}%</td>
                <td>{item.upper_misses}</td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      </Card>

      {/* Interactive Confusion Matrix Section */}
      <Card title="Module A Confusion Matrix (Synthetic Holdout @ 168h)" className="confusion-matrix-card">
        <div className="cm-controls">
          <div className="cm-toggle-group"><span className="toggle-label">Frozen Module A baseline · observed 1.04% FPR</span></div>
          <div className="cm-active-description">
            <Sliders size={14} className="text-accent" />
            <span>{currentPoint.description}</span>
          </div>
        </div>

        <div className="cm-main-layout">
          {/* 2x2 Matrix Table */}
          <div className="cm-matrix-container">
            <div className="cm-matrix-headers">
              <div className="col-empty" />
              <div className="col-header">PREDICTED ABNORMAL</div>
              <div className="col-header">PREDICTED HEALTHY</div>
            </div>

            <div className="cm-matrix-row">
              <div className="row-header">ACTUAL DEFECT (P=90)</div>
              <div className="cm-cell tp-cell">
                <span className="cell-label">TRUE POSITIVE (TP)</span>
                <span className="cell-val text-pass">{currentPoint.tp}</span>
                <span className="cell-sub">Defect caught by screen</span>
              </div>
              <div className="cm-cell fn-cell">
                <span className="cell-label">FALSE NEGATIVE (FN)</span>
                <span className="cell-val text-reject">{currentPoint.fn}</span>
                <span className="cell-sub">Defect passed undetected</span>
              </div>
            </div>

            <div className="cm-matrix-row">
              <div className="row-header">ACTUAL HEALTHY (N=1253)</div>
              <div className="cm-cell fp-cell">
                <span className="cell-label">FALSE POSITIVE (FP)</span>
                <span className="cell-val text-monitor">{currentPoint.fp}</span>
                <span className="cell-sub">Healthy flagged (false alarm)</span>
              </div>
              <div className="cm-cell tn-cell">
                <span className="cell-label">TRUE NEGATIVE (TN)</span>
                <span className="cell-val">{currentPoint.tn}</span>
                <span className="cell-sub">Synthetic healthy part not flagged</span>
              </div>
            </div>
          </div>

          {/* Metric Derivation Card */}
          <div className="cm-derivations-panel">
            <h4 className="derivation-title">Calculated Performance Derivations</h4>
            <div className="derivation-list">
              <div className="derivation-row">
                <span className="d-label">Recall / Sensitivity:</span>
                <span className="d-formula">TP / (TP + FN) = {currentPoint.tp}/90 =</span>
                <strong className="d-val text-pass">{(currentPoint.recall * 100).toFixed(2)}%</strong>
              </div>
              <div className="derivation-row">
                <span className="d-label">Precision (PPV):</span>
                <span className="d-formula">TP / (TP + FP) = {currentPoint.tp}/({currentPoint.tp + currentPoint.fp}) =</span>
                <strong className="d-val">{(currentPoint.precision * 100).toFixed(2)}%</strong>
              </div>
              <div className="derivation-row">
                <span className="d-label">Specificity (TNR):</span>
                <span className="d-formula">TN / (TN + FP) = {currentPoint.tn}/1253 =</span>
                <strong className="d-val">{(currentPoint.specificity * 100).toFixed(2)}%</strong>
              </div>
              <div className="derivation-row">
                <span className="d-label">False Positive Rate (FPR):</span>
                <span className="d-formula">FP / (FP + TN) = {currentPoint.fp}/1253 =</span>
                <strong className="d-val">{(currentPoint.fpr * 100).toFixed(2)}%</strong>
              </div>
              <div className="derivation-row">
                <span className="d-label">F1 Score:</span>
                <span className="d-formula">2·P·R / (P + R) =</span>
                <strong className="d-val">{(currentPoint.f1 * 100).toFixed(2)}%</strong>
              </div>
              <div className="derivation-row highlight">
                <span className="d-label">F2 Score (β=2):</span>
                <span className="d-formula">5·TP / (5·TP + FP + 4·FN) =</span>
                <strong className="d-val text-accent">{(currentPoint.f2 * 100).toFixed(2)}%</strong>
              </div>
            </div>
          </div>
        </div>
      </Card>

      {/* Epoch Evolution & Variant Breakdown Grid */}
      <div className="eval-subgrids">
        {/* Multi-Epoch Screening Evolution */}
        <Card title="Defect Emergence Over Burn-in Epochs (0h → 168h)" className="subgrid-card">
          <div className="table-responsive">
            <table className="epoch-eval-table">
              <thead>
                <tr>
                  <th>Epoch</th>
                  <th>TP Caught</th>
                  <th>FN Missed</th>
                  <th>FP Alarms</th>
                  <th>Recall</th>
                  <th>Precision</th>
                  <th>Accuracy</th>
                </tr>
              </thead>
              <tbody>
                {epochs.map(e => (
                  <tr key={e.epoch} className={e.epoch === '168h' ? 'highlight-epoch' : ''}>
                    <td className="code-font font-bold">
                      {e.epoch} {e.epoch === '168h' && <Badge status="PASS" size="sm">FINAL</Badge>}
                    </td>
                    <td className="code-font text-pass font-bold">{e.tp}</td>
                    <td className="code-font text-reject">{e.fn}</td>
                    <td className="code-font">{e.fp}</td>
                    <td className="code-font">{(e.recall * 100).toFixed(1)}%</td>
                    <td className="code-font">{(e.precision * 100).toFixed(1)}%</td>
                    <td className="code-font">{(e.accuracy * 100).toFixed(1)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="subgrid-note">
            In this synthetic holdout, more labelled defects are detected as later measurements become available: recall rises from 15.6% at 0h to 72.2% at 168h.
          </div>
        </Card>

        {/* Variant Breakdown */}
        <Card title="Performance by Device Variant (18 Holdout Lots)" className="subgrid-card">
          <div className="table-responsive">
            <table className="epoch-eval-table">
              <thead>
                <tr>
                  <th>Device Variant</th>
                  <th>Holdout Parts</th>
                  <th>TP</th>
                  <th>FN</th>
                  <th>FP</th>
                  <th>Recall</th>
                  <th>Precision</th>
                </tr>
              </thead>
              <tbody>
                {variants.map(v => (
                  <tr key={v.device_variant}>
                    <td><Badge variant={v.device_variant}>{v.device_variant}</Badge></td>
                    <td className="code-font">{v.components}</td>
                    <td className="code-font text-pass">{v.tp}</td>
                    <td className="code-font text-reject">{v.fn}</td>
                    <td className="code-font">{v.fp}</td>
                    <td className="code-font font-bold">{(v.recall * 100).toFixed(1)}%</td>
                    <td className="code-font">{(v.precision * 100).toFixed(1)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="subgrid-note">
            Evaluated on whole-lot holdout partitions (6 lots per variant) ensuring zero cross-lot contamination.
          </div>
        </Card>
      </div>

      {/* Model Manifests & Test Verification */}
      <div className="manifests-grid">
        <Card title="Module A: Release Manifest & Claim Verifications">
          <div className="manifest-body">
            <div className="manifest-row">
              <span className="m-label">Model Pipeline:</span>
              <span className="m-val code-font">{modA.model_version || 'ModuleA-FINAL01'}</span>
            </div>
            <div className="manifest-row">
              <span className="m-label">Dataset ID:</span>
              <span className="m-val code-font">{modA.dataset_id || 'SIH26170-FINAL-01'}</span>
            </div>
            <div className="manifest-row">
              <span className="m-label">Unit Test Suite:</span>
              <span className="m-val text-pass font-bold">151 passed (delivered report)</span>
            </div>
            <div className="manifest-row">
              <span className="m-label">Verified Claims:</span>
              <span className="m-val text-pass font-bold">166 verified (delivered report)</span>
            </div>
            <div className="manifest-row">
              <span className="m-label">Operating Threshold:</span>
              <span className="m-val code-font">0.939541 (rank cutoff)</span>
            </div>
            <div className="manifest-row">
              <span className="m-label">Confirmed Floor:</span>
              <span className="m-val code-font">0.900 (Datasheet Exceedance)</span>
            </div>
          </div>
        </Card>

        <Card title="Module B: Release Manifest & Claim Verifications">
          <div className="manifest-body">
            <div className="manifest-row">
              <span className="m-label">Release Candidate:</span>
              <span className="m-val code-font">{modB.release_candidate || 'ModuleB-FINAL01-RC2'}</span>
            </div>
            <div className="manifest-row">
              <span className="m-label">Release State:</span>
              <span className="m-val code-font">{modB.release_state || 'SPENT_HOLDOUT'}</span>
            </div>
            <div className="manifest-row">
              <span className="m-label">Unit & Integration Tests:</span>
              <span className="m-val text-pass font-bold">102 passed (0 failed)</span>
            </div>
            <div className="manifest-row">
              <span className="m-label">Verified Claims:</span>
              <span className="m-val text-pass font-bold">210 verified (0 failed)</span>
            </div>
            <div className="manifest-row">
              <span className="m-label">Holdout Completeness:</span>
              <span className="m-val text-pass font-bold">Enforced (18 Whole Lots)</span>
            </div>
            <div className="manifest-row">
              <span className="m-label">Disposition Rule:</span>
              <span className="m-val text-muted">Defers to Fusion (Decision D1)</span>
            </div>
          </div>
        </Card>
      </div>
      </div></details>
    </div>
  );
}
