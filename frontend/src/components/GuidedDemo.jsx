import React, { useEffect, useState } from 'react';
import { CartesianGrid, Legend, Line, LineChart, ReferenceDot, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { api } from '../services/api';
import { ModuleBReasons } from './ModuleBReasons';
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
  const coreValues = measurement ? [...values, measurement.lot_median_24h] : [];
  const coreSpread = coreValues.length ? Math.max(...coreValues) - Math.min(...coreValues) : 0;
  const showLimit = measurement?.limit != null && measurement.limit >= Math.min(...coreValues) - coreSpread && measurement.limit <= Math.max(...coreValues) + coreSpread;
  const visibleValues = measurement ? [...coreValues,
    ...(showLimit ? [measurement.limit] : [])] : [];
  const spread = visibleValues.length ? Math.max(...visibleValues) - Math.min(...visibleValues) : 0;
  const padding = Math.max(spread * 0.12, Math.max(...(visibleValues.length ? visibleValues : [1])) * 0.02);
  const yDomain = visibleValues.length ? [Math.max(0, Math.min(...visibleValues) - padding), Math.max(...visibleValues) + padding] : ['auto', 'auto'];
  return <section className="guided-demo work-panel" aria-label="Guided operational demonstration">
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
        <option value="ALL">All parameters</option>
        {Object.keys(item.parameters).map(p => <option key={p} value={p}>{p.replaceAll('_', ' ')}</option>)}
      </select></label>
      {parameter === 'ALL' && <div className="demo-all-parameters">
        <p>All six measured parameters for this component. Each row shows its own unit; values with different units are not combined on one axis. Choose a parameter above for its trend chart.</p>
        <div className="demo-all-scroll"><table>
          <thead><tr><th>Parameter</th><th>Unit</th><th>Observed 0h</th><th>Observed 24h</th><th>24h lot median</th><th>Forecast 168h</th><th>Upper bound</th><th>Static limit</th>{showLater && <><th>Observed 96h</th><th>Observed 168h</th></>}</tr></thead>
          <tbody>{Object.entries(item.parameters).map(([name, values]) => <tr key={name}>
            <th scope="row">{name.replaceAll('_', ' ')}</th><td>{values.unit}</td>
            {[values.observed_early['0'], values.observed_early['24'], values.lot_median_24h,
              values.predicted_168h, values.upper_168h, values.limit,
              ...(showLater ? [values.observed_retrospective['96'], values.observed_retrospective['168']] : [])]
              .map((v, index) => <td key={index}>{v == null ? '—' : readable(v)}</td>)}
          </tr>)}</tbody>
        </table></div>
        <p>The 96h and 168h observed readings appear only after you select “Reveal” below. The forecast remains the original prediction made from 0h and 24h readings.</p>
      </div>}
      {measurement && <>
        <div className="demo-chart" role="img" aria-label={`Observed 0h and 24h ${parameter}, forecast 168h and lot median, ${showLater ? 'with retrospective 96h and 168h readings' : 'without later observed readings'}`}>
          <ResponsiveContainer width="100%" height={270}>
            <LineChart data={chart} margin={{top: 20, right: 25, bottom: 5, left: 15}}>
              <CartesianGrid strokeDasharray="3 3" stroke="#526b73" opacity={0.35} />
              <XAxis dataKey="hour" /><YAxis domain={yDomain} width={65} tickFormatter={readable} />
              <Tooltip formatter={(v, name) => [`${readable(v)} ${measurement.unit}`, name]}
                contentStyle={{backgroundColor: '#20343b', border: '1px solid #526b73', color: '#f2f3ea'}}
                labelStyle={{color: '#f2f3ea'}} itemStyle={{color: '#f2f3ea'}} /><Legend />
              <ReferenceLine x="24h" stroke="#b4c9c7" strokeDasharray="3 5" />
              {showLimit && <ReferenceLine y={measurement.limit} stroke="#f37a7b" strokeDasharray="2 4" label="limit" />}
              <Line type="linear" dataKey="measured" name="Observed" stroke="#82c7b5" strokeWidth={3} connectNulls={false} />
              <Line type="linear" dataKey="forecast" name="Forecast from 0h/24h" stroke="#81b9e6" strokeWidth={3} strokeDasharray="6 3" connectNulls />
              <ReferenceDot x="24h" y={measurement.lot_median_24h} r={6} fill="#d8cfb2" stroke="#15242c" />
              <ReferenceLine segment={[{x:'168h',y:measurement.predicted_168h},{x:'168h',y:measurement.upper_168h}]} stroke="#f3b65a" strokeWidth={3} />
              {measurement.upper_168h != null && <ReferenceDot x="168h" y={measurement.upper_168h} r={6} fill="#f3b65a" stroke="#15242c" label="upper" />}
            </LineChart>
          </ResponsiveContainer>
        </div>
        <p>24h lot median (sand point): {readable(measurement.lot_median_24h)} {measurement.unit} · 168h forecast: {readable(measurement.predicted_168h)} {measurement.unit} · upper bound (amber marker): {readable(measurement.upper_168h)} {measurement.unit} · {measurement.limit == null ? 'no supplied static limit' : `static limit: ${readable(measurement.limit)} ${measurement.unit}${showLimit ? '' : ' (outside this chart scale)'}`}. The median is a single 24h lot comparison, not a forecast or specification limit. The vertical marker at 24h is the early-decision cutoff.</p>
      </>}
      <div className="demo-decision"><strong>24h: {item.at_24h.disposition.replaceAll('_', ' ')}</strong><p>{item.at_24h.reason}</p><p>Module A: {item.at_24h.module_a_disposition} · score {readable(item.at_24h.module_a_score)}.</p><div className="demo-reason-heading">Module B indicators</div><ModuleBReasons codes={item.at_24h.module_b_reason_codes} /></div>
      <button type="button" onClick={() => setShowLater(v => !v)} aria-expanded={showLater}>{showLater ? 'Hide retrospective measurements' : 'Reveal 96h and 168h observed readings'}</button>
      {showLater && <div className="demo-retrospective"><strong>Retrospective 168h decision: {item.at_168h.disposition}</strong><p>{item.at_168h.reason}</p><p>Later readings were hidden from the 24h decision. The original 24h forecast was reused.</p></div>}
      <p className="demo-caveat">{demo.limitations} The current Module B artifact is a {demo.module_b_release_state} build. For actual imported lots, use the workspace below and record a review.</p>
      <div className="demo-finish"><strong>Walkthrough complete</strong><p>These examples are read-only. Measurement import, QA outcomes, and review records below are the separate, password-protected operator workflow.</p><a href="#measurement-import">See how a new lot is imported ↓</a></div>
    </>}
  </section>;
}
