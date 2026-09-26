import React, { useEffect, useState } from 'react';
import { CartesianGrid, Legend, Line, LineChart, ReferenceDot, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { api } from '../services/api';
import './GuidedDemo.css';

const readable = value => Number(value).toPrecision(5);

export default function GuidedDemo() {
  const [demo, setDemo] = useState(null);
  const [error, setError] = useState('');
  const [selected, setSelected] = useState(0);
  const [parameter, setParameter] = useState('');
  const [showLater, setShowLater] = useState(false);
  useEffect(() => {
    let active = true;
    api.get('/api/operational/demo').then(result => {
      if (active) { setDemo(result); setParameter(result.cases[0].primary_parameter); }
    }).catch(e => { if (active) setError(e.message); });
    return () => { active = false; };
  }, []);
  const item = demo?.cases[selected];
  const measurement = item?.parameters[parameter];
  const chart = measurement && ['0', '24', '96', '168'].map(hour => ({
    hour: `${hour}h`,
    measured: (Number(hour) <= 24 || showLater) ?
      (Number(hour) <= 24 ? measurement.observed_early[hour] : measurement.observed_retrospective[hour]) : null,
    forecast: hour === '24' ? measurement.observed_early['24'] :
      hour === '168' ? measurement.predicted_168h : null,
  }));
  const values = measurement && [measurement.observed_early['0'], measurement.observed_early['24'],
    measurement.predicted_168h, measurement.upper_168h,
    ...(showLater ? Object.values(measurement.observed_retrospective) : [])].filter(Number.isFinite);
  const showLimit = measurement?.limit != null && measurement.limit <= Math.max(...(values || [1])) * 2;
  const visibleValues = measurement ? [...values, measurement.lot_median_24h,
    ...(showLimit ? [measurement.limit] : [])] : [];
  const spread = visibleValues.length ? Math.max(...visibleValues) - Math.min(...visibleValues) : 0;
  const padding = Math.max(spread * 0.12, Math.max(...(visibleValues.length ? visibleValues : [1])) * 0.02);
  const yDomain = visibleValues.length ? [Math.max(0, Math.min(...visibleValues) - padding), Math.max(...visibleValues) + padding] : ['auto', 'auto'];
  return <section id="guided-demo" className="guided-demo work-panel" aria-label="Guided operational demonstration">
    <h2>Public screening walkthrough · no password needed</h2>
    <p>In about one minute: choose a case below, inspect its 0h/24h readings and 168h forecast, then reveal the later observed result. The backend runs complete synthetic lots; this walkthrough does not alter the protected workspace. The fourth case keeps an earlier warning visible beside a later PASS, and the fifth shows a planted drift the policy misses at 24h.</p>
    {error && <p role="alert" className="work-error">Demo unavailable: {error}</p>}
    {!demo && !error && <p role="status">Running the synthetic lot through the operational model…</p>}
    {item && <>
      <div className="demo-cases" role="group" aria-label="Choose a demonstration case">
        {demo.cases.map((c, index) => <button key={c.component_id} type="button" aria-pressed={selected === index} onClick={() => {
          setSelected(index); setParameter(c.primary_parameter); setShowLater(c.title === 'Earlier alert → PASS');
        }}>{c.title}</button>)}
      </div>
      <h3>{item.component_id} · {item.title}</h3>
      <p>{item.description} {item.synthetic_label ? `Label: ${item.synthetic_label}.` : 'This example has no independently verified physical defect label.'} Its decision is not proof of performance on real hardware.</p>
      <div className="demo-steps">
        <div><span>1 · Measurements</span><strong>0h + 24h observed</strong></div>
        <div><span>2 · Model B</span><strong>168h forecast + upper bound</strong></div>
        <div><span>3 · Model A</span><strong>Compared with the {item.lot_size || demo.lot_size}-part lot</strong></div>
        <div><span>4 · QA action</span><strong>{item.at_24h.disposition.replaceAll('_', ' ')}</strong></div>
      </div>
      {item.synthetic_label && item.at_24h.disposition === 'PROVISIONAL_PASS' && <div className="demo-history-alert" role="status">
        <strong>Known synthetic injection · missed at 24h</strong>
        <p>The 24h snapshot gives this planted drift a provisional pass. Reveal 96h and 168h to see the later change and review decision. This is a visible model failure, not an early-detection success claim.</p>
      </div>}
      {item.at_168h.prior_24h_alert && <div className="demo-history-alert" role="status">
        <strong>Earlier 24h MONITOR → current 168h PASS · QA review still needed</strong>
        <p>The 168h model snapshot says PASS, but it does not erase the 24h warning. This is a retrospective constructed stress case, shown here so the review rule is visible without unlocking the operator workspace.</p>
      </div>}
      <label>Inspect parameter <select value={parameter} onChange={e => setParameter(e.target.value)}>
        {Object.keys(item.parameters).map(p => <option key={p} value={p}>{p.replaceAll('_', ' ')}</option>)}
      </select></label>
      {measurement && <>
        <div className="demo-chart" role="img" aria-label={`Observed 0h and 24h ${parameter}, forecast 168h and lot median, ${showLater ? 'with retrospective 96h and 168h readings' : 'without later observed readings'}`}>
          <ResponsiveContainer width="100%" height={270}>
            <LineChart data={chart} margin={{top: 20, right: 25, bottom: 5, left: 15}}>
              <CartesianGrid strokeDasharray="3 3" stroke="#64748b" opacity={0.35} />
              <XAxis dataKey="hour" /><YAxis domain={yDomain} width={65} tickFormatter={readable} />
              <Tooltip formatter={(v, name) => [`${readable(v)} ${measurement.unit}`, name]}
                contentStyle={{backgroundColor: '#111723', border: '1px solid #2a3b5c', color: '#f1f5f9'}}
                labelStyle={{color: '#f1f5f9'}} itemStyle={{color: '#f1f5f9'}} /><Legend />
              <ReferenceLine y={measurement.lot_median_24h} stroke="#c084fc" strokeDasharray="5 5" label="24h lot median" />
              {showLimit && <ReferenceLine y={measurement.limit} stroke="#f87171" strokeDasharray="2 4" label="limit" />}
              <Line type="linear" dataKey="measured" name="Observed" stroke="#34d399" strokeWidth={3} connectNulls={false} />
              <Line type="linear" dataKey="forecast" name="Forecast from 0h/24h" stroke="#38bdf8" strokeWidth={3} strokeDasharray="6 3" connectNulls />
              {measurement.upper_168h != null && <ReferenceDot x="168h" y={measurement.upper_168h} r={6} fill="#fbbf24" stroke="#111827" label="upper" />}
            </LineChart>
          </ResponsiveContainer>
        </div>
        <p>24h lot median: {readable(measurement.lot_median_24h)} {measurement.unit} · 168h forecast: {readable(measurement.predicted_168h)} {measurement.unit} · upper bound: {readable(measurement.upper_168h)} {measurement.unit} · {measurement.limit == null ? 'no supplied static limit' : `static limit: ${readable(measurement.limit)} ${measurement.unit}`}. The lot median is context, not the policy threshold.</p>
      </>}
      <div className="demo-decision"><strong>24h: {item.at_24h.disposition.replaceAll('_', ' ')}</strong><p>{item.at_24h.reason}</p><p>Module A: {item.at_24h.module_a_disposition} · score {readable(item.at_24h.module_a_score)}. {item.at_24h.module_b_reason_codes ? `Module B codes: ${item.at_24h.module_b_reason_codes}` : 'No Module B warning codes.'}</p></div>
      <button type="button" onClick={() => setShowLater(v => !v)} aria-expanded={showLater}>{showLater ? 'Hide retrospective measurements' : 'Reveal 96h and 168h observed readings'}</button>
      {showLater && <div className="demo-retrospective"><strong>Retrospective 168h decision: {item.at_168h.disposition}</strong><p>{item.at_168h.reason}</p><p>Later readings were hidden from the 24h decision. The original 24h forecast was reused.</p></div>}
      <p className="demo-caveat">{demo.limitations} The current Module B artifact is a {demo.module_b_release_state} build. For actual imported lots, use the workspace below and record a review.</p>
    </>}
  </section>;
}
