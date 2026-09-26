import React, { useEffect, useState } from 'react';
import { ArrowRight, RotateCcw } from 'lucide-react';
import { CartesianGrid, Line, LineChart, ReferenceDot, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import { ModuleBReasons } from './ModuleBReasons';
import './ComponentStory.css';

const CASES = [
  { title: 'A quiet warning', match: 'Static-pass review', caption: 'No 24h limit breach, yet the envelope requests review.' },
  { title: 'A clear breach', match: 'Observed limit breach', caption: 'A measured value crosses a specification limit.' },
  { title: 'A missed drift', match: 'Planted drift · missed at 24h', caption: 'A planted defect receives a provisional pass at 24h.' },
];
const fmt = value => value != null && Number.isFinite(Number(value)) ? Number(value).toPrecision(4) : '—';

export default function ComponentStory() {
  const navigate = useNavigate();
  const [demo, setDemo] = useState(null);
  const [error, setError] = useState('');
  const [selected, setSelected] = useState(0);
  const [parameter, setParameter] = useState('');
  const [revealed, setRevealed] = useState(false);
  useEffect(() => {
    let active = true;
    api.get('/api/operational/demo').then(result => { if (active) setDemo(result); })
      .catch(err => { if (active) setError(err.message); });
    return () => { active = false; };
  }, []);

  const choice = CASES[selected];
  const item = demo?.cases?.find(entry => entry.title === choice.match);
  const activeParameter = item?.parameters?.[parameter] ? parameter : item?.primary_parameter;
  const measurement = item?.parameters?.[activeParameter];
  const early = measurement?.observed_early;
  const later = measurement?.observed_retrospective;
  const chart = measurement && [0, 24, 96, 168].map(hour => ({
    hour: `${hour}h`,
    observed: hour <= 24 ? early[String(hour)] : revealed ? later[String(hour)] : null,
    forecast: hour === 24 ? early['24'] : hour === 168 ? measurement.predicted_168h : null,
  }));
  const visible = measurement && [early['0'], early['24'], measurement.predicted_168h,
    measurement.upper_168h, measurement.lot_median_24h,
    ...(revealed ? [later['96'], later['168']] : [])].filter(Number.isFinite);
  const span = visible?.length ? Math.max(...visible) - Math.min(...visible) : 1;
  const pad = Math.max(span * 0.18, Math.abs(visible?.[0] || 1) * 0.025);
  const showLimit = measurement?.limit != null && measurement.limit >= Math.min(...visible) - span && measurement.limit <= Math.max(...visible) + span;
  const domain = visible?.length ? [Math.max(0, Math.min(...visible, ...(showLimit ? [measurement.limit] : [])) - pad), Math.max(...visible, ...(showLimit ? [measurement.limit] : [])) + pad] : ['auto', 'auto'];
  const lotDifference = measurement ? early['24'] - measurement.lot_median_24h : 0;

  return <section className="bt-story" aria-labelledby="bt-story-title">
    <div className="bt-story-intro">
      <div className="bt-story-eyebrow"><span className="bt-story-mark" /> BURNTRACE / COMPONENT EVIDENCE</div>
      <h1 id="bt-story-title">A component can look fine at 24 hours. What happens next?</h1>
      <p>Follow one part through observed measurements, a 168h forecast, its lot context, and a recorded screening decision.</p>
      <div className="bt-story-case-tabs" role="group" aria-label="Choose a component story">
        {CASES.map((c, index) => <button key={c.match} type="button" aria-pressed={selected === index}
          onClick={() => { setSelected(index); setParameter(''); setRevealed(false); }}><span>0{index + 1}</span>{c.title}</button>)}
      </div>
      <p className="bt-story-case-caption">{choice.caption}</p>
      <div className="bt-story-actions">
        <button type="button" className="bt-story-primary" onClick={() => navigate('/data#guided-demo')}>Explore all five cases <ArrowRight size={17} /></button>
        <button type="button" className="bt-story-secondary" onClick={() => navigate('/models')}>See measured performance <ArrowRight size={16} /></button>
      </div>
      <p className="bt-story-disclosure">Constructed synthetic examples from the operational backend. A demo decision is not proof of accuracy on physical hardware.</p>
    </div>
    <div className="bt-instrument">
      <div className="bt-instrument-header"><span>SCREENING RECORD / 24H SNAPSHOT</span><span className="bt-instrument-live">● READ-ONLY MODEL RUN</span></div>
      {error && <div role="alert" className="bt-story-state">Model run unavailable: {error}. <button type="button" onClick={() => navigate('/models')}>View frozen evaluation →</button></div>}
      {!demo && !error && <div role="status" className="bt-story-state">Running the synthetic lot through the operational model…</div>}
      {demo && !item && <div role="alert" className="bt-story-state">This example is unavailable in the current model run.</div>}
      {item && measurement && <>
        <div className="bt-instrument-subhead"><div><small>COMPONENT / {item.lot_size || demo.lot_size}-PART LOT</small><strong>{item.component_id}</strong></div><label className="bt-parameter-picker"><span>INSPECT PARAMETER</span><select value={activeParameter} onChange={event => setParameter(event.target.value)}>{Object.keys(item.parameters).map(name => <option key={name} value={name}>{name.replaceAll('_', ' ')}</option>)}</select></label></div>
        <div className="bt-evidence-sequence" aria-label="Screening sequence"><span>01 / Measured 0–24h</span><span>02 / Forecast 168h</span><span>03 / Compare lot</span><span>04 / QA decision</span></div>
        <div className="bt-story-chart" role="img" aria-label={`${activeParameter.replaceAll('_', ' ')}: observed readings at 0h and 24h, forecast and upper bound at 168h, 24h lot median${revealed ? ', and later observed readings at 96h and 168h' : ''}`}>
          <ResponsiveContainer width="100%" height={218}>
            <LineChart data={chart} margin={{top: 18, right: 24, bottom: 4, left: 3}}>
              <CartesianGrid stroke="#52656a" strokeDasharray="2 5" opacity={0.38} />
              <XAxis dataKey="hour" stroke="#aabcb9" tick={{fontSize: 11}} />
              <YAxis width={59} domain={domain} tickFormatter={fmt} stroke="#aabcb9" tick={{fontSize: 10}} />
              <Tooltip formatter={(v, name) => [`${fmt(v)} ${measurement.unit}`, name]}
                contentStyle={{background:'#20343b',border:'1px solid #5a7074',color:'#fff'}} labelStyle={{color:'#fff'}} itemStyle={{color:'#fff'}} />
              <ReferenceLine x="24h" stroke="#8b9c9e" strokeDasharray="3 5" />
              {showLimit && <ReferenceLine y={measurement.limit} stroke="#f37a7b" strokeDasharray="3 3" />}
              <Line type="linear" dataKey="observed" name="Observed" stroke="#82c7b5" strokeWidth={3} dot={{r:4}} connectNulls={false} />
              <Line type="linear" dataKey="forecast" name="Forecast from 0h/24h" stroke="#81b9e6" strokeWidth={2.5} strokeDasharray="6 4" connectNulls dot={{r:4}} />
              <ReferenceLine segment={[{x:'168h',y:measurement.predicted_168h},{x:'168h',y:measurement.upper_168h}]} stroke="#f3b65a" strokeWidth={3} />
              <ReferenceDot x="24h" y={measurement.lot_median_24h} r={5} fill="#dbb578" stroke="#15242c" />
              {measurement.upper_168h != null && <ReferenceDot x="168h" y={measurement.upper_168h} r={5} fill="#f3b65a" stroke="#15242c" />}
            </LineChart>
          </ResponsiveContainer>
        </div>
        <div className="bt-chart-key"><span><i className="bt-key-observed" />Measured</span><span><i className="bt-key-forecast" />Forecast</span><span><i className="bt-key-upper" />Forecast → upper bound</span><span><i className="bt-key-lot" />24h lot median</span>{showLimit && <span><i className="bt-key-limit" />Static limit</span>}</div>
        <p className="bt-chart-note">The vertical marker is the 24h decision cutoff. The lot median is a single 24h comparison, not a time-series forecast. {measurement.limit != null && !showLimit ? 'The static limit is outside this chart scale; its value is listed below.' : ''}</p>
        <div className="bt-story-readings">
          <div><small>OBSERVED / 0H → 24H</small><strong>{fmt(early['0'])} → {fmt(early['24'])} <em>{measurement.unit}</em></strong></div>
          <div><small>FORECAST / 168H</small><strong>{fmt(measurement.predicted_168h)} <em>{measurement.unit}</em></strong></div>
          <div><small>UPPER BOUND / 168H</small><strong>{fmt(measurement.upper_168h)} <em>{measurement.unit}</em></strong></div>
          <div><small>STATIC LIMIT</small><strong>{fmt(measurement.limit)} <em>{measurement.unit}</em></strong></div>
        </div>
        <div className="bt-lot-context"><span>LOT COMPARISON / 24H</span><strong>{fmt(early['24'])} {measurement.unit} <em>vs.</em> {fmt(measurement.lot_median_24h)} {measurement.unit} median</strong><small>{lotDifference >= 0 ? 'Above' : 'Below'} this lot’s 24h median by {fmt(Math.abs(lotDifference))} {measurement.unit}. Context only; the median is not a specification limit.</small></div>
        <div className="bt-story-verdict"><div><small>24H QA ACTION</small><strong className={`bt-verdict-${item.at_24h.disposition.toLowerCase()}`}>{item.at_24h.disposition.replaceAll('_', ' ')}</strong><p>{item.at_24h.reason}</p></div><span>MODULE A · {item.at_24h.module_a_disposition}</span></div>
        <div className="bt-evidence-explain">The disposition considers all six parameters, not only the selected chart. Module A: <strong>{item.at_24h.module_a_disposition}</strong>. <div className="bt-reason-heading">Module B indicators</div><ModuleBReasons codes={item.at_24h.module_b_reason_codes} compact />{item.synthetic_label && item.at_24h.disposition === 'PROVISIONAL_PASS' ? <p>This planted defect is a documented 24h miss; provisional pass is not final clearance.</p> : null}</div>
        <div className="bt-story-reveal"><button type="button" aria-expanded={revealed} onClick={() => setRevealed(value => !value)}><RotateCcw size={15}/>{revealed ? 'Hide later measurements' : 'Reveal later measurements'}</button>{revealed && <p>Retrospective: observed 96h {fmt(later['96'])} and 168h {fmt(later['168'])} {measurement.unit}. 168h decision: <strong>{item.at_168h.disposition.replaceAll('_', ' ')}</strong>. These values were not inputs to the 24h decision.</p>}</div>
      </>}
    </div>
  </section>;
}
