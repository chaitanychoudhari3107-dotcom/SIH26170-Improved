import React, { useState } from 'react';
import { Card } from './ui/Card';
import evaluation from '../data/operationalEvaluation.json';
import './OperationalEvaluation.css';

const operatingPoints = [
  ['static_limits', 'Observed static limits'],
  ['module_a', 'Module A'],
  ['strong_signal', 'Operational strong signal'],
  ['review_gate', 'Operational review gate'],
];

export default function OperationalEvaluation() {
  const [epoch, setEpoch] = useState('24');
  const current = evaluation.epochs[epoch];
  const matrix = current.review_gate;
  return <section className="operational-evaluation" aria-label="Operational policy evaluation">
    <Card title="Operational policy · measured review outcomes">
      <p>Retrospective synthetic holdout: {evaluation.population.toLocaleString()} parts, {evaluation.defects} labelled defects, {evaluation.healthy.toLocaleString()} healthy parts across {evaluation.lots} complete lots. These outcomes were already inspected during development; this is not independent validation of a newly tuned rule.</p>
      <div className="operational-tabs" role="group" aria-label="Evaluation time">
        {['24', '168'].map(value => <button key={value} type="button" aria-pressed={epoch === value} onClick={() => setEpoch(value)}>{value}h</button>)}
      </div>
      <p><strong>Review gate:</strong> REJECT, HOLD and MONITOR count as flagged for human review. At 24h, all remaining decisions are <strong>PROVISIONAL_PASS</strong>, not final clearance. HOLD is forecast risk; REJECT is an observed limit breach. MONITOR is not a confirmed defect.</p>
      <div className="operational-matrix" role="group" aria-label={`${epoch} hour operational review gate confusion matrix`}>
        <div><span>TP · defective flagged</span><strong>{matrix.tp}</strong></div>
        <div><span>FN · defective missed</span><strong>{matrix.fn}</strong></div>
        <div><span>FP · healthy reviewed</span><strong>{matrix.fp}</strong></div>
        <div><span>TN · healthy cleared</span><strong>{matrix.tn}</strong></div>
      </div>
      <p>Recall {((matrix.tp / evaluation.defects) * 100).toFixed(1)}% · healthy review rate {((matrix.fp / evaluation.healthy) * 100).toFixed(2)}%. The stronger REJECT/HOLD signal catches {current.strong_signal.tp} defects and flags {current.strong_signal.fp} healthy parts. Current dispositions: {Object.entries(current.dispositions).map(([name, count]) => `${name} ${count}`).join(' · ')}.</p>
    </Card>
    <Card title={`Same ${epoch}h lots · defects caught versus healthy reviews`}>
      <p>Each row uses the same {evaluation.population.toLocaleString()} labelled parts. Static limits flag observed specification breaches only; Module A flags its MONITOR output; the operational rows run the actual workspace policy. More catches can require substantially more healthy reviews.</p>
      <div className="operational-table"><table><thead><tr><th>Decision rule</th><th>Defects caught / 90</th><th>Defects missed</th><th>Healthy reviewed / 1,253</th></tr></thead><tbody>
        {operatingPoints.map(([key, label]) => { const m = current[key]; return <tr key={key}><th scope="row">{label}</th><td>{m.tp} ({((m.tp / 90) * 100).toFixed(1)}%)</td><td>{m.fn}</td><td>{m.fp} ({((m.fp / 1253) * 100).toFixed(2)}%)</td></tr>; })}
      </tbody></table></div>
      <p>The operational Module B artifact is a reconstructed rehearsal fit. Results are specific to this synthetic population and rule; they do not establish zero missed defects in real hardware.</p>
    </Card>
    <Card title="Operational Module B · 168h forecasts from 0h and 24h">
      <p>MAE is mean absolute error in the parameter's unit. Upper coverage is the observed share of true 168h readings at or below the reported upper bound. There are {evaluation.defects} defective parts; coverage below 95% means the displayed upper bound did not reach its nominal target on this holdout.</p>
      <div className="operational-table"><table><thead><tr><th>Parameter</th><th>MAE · all</th><th>MAE · defective</th><th>Upper coverage · all</th><th>Upper coverage · defective</th></tr></thead><tbody>
        {evaluation.module_b.map(m => <tr key={m.parameter}><th scope="row">{m.parameter} ({m.unit})</th><td>{m.all_mae.toFixed(4)}</td><td>{m.defect_mae.toFixed(4)}</td><td>{(m.all_coverage * 100).toFixed(1)}%</td><td>{(m.defect_coverage * 100).toFixed(1)}%</td></tr>)}
      </tbody></table></div>
      <p>These metrics describe the operational rehearsal artifact. The separate Module B release table below evaluates a different saved forecast output.</p>
    </Card>
  </section>;
}
