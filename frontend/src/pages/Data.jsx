import React, { useEffect, useState } from 'react';
import { PageHeader } from '../components/layout/PageHeader';
import { api } from '../services/api';
import './Workspace.css';
const epochs = [0, 24, 96, 168];
export default function Data() {
  const [config,setConfig]=useState(null), [lots,setLots]=useState([]), [key,setKey]=useState('');
  const [form,setForm]=useState({lot_id:'DEMO_A',device_variant:'CMOS_A',expected_count:78,epoch_h:24,csv_text:''});
  const [preview,setPreview]=useState(null), [run,setRun]=useState(null), [selected,setSelected]=useState('');
  const [busy,setBusy]=useState(false), [error,setError]=useState(''), [notice,setNotice]=useState('');
  const [action,setAction]=useState('ACKNOWLEDGE'), [reason,setReason]=useState('');
  async function refresh(){ const c=await api.get('/api/operational/config'); setConfig(c); if(c.mode!=='protected'||c.can_write)setLots(await api.get('/api/operational/lots')); }
  useEffect(()=>{refresh().catch(e=>setError(e.message));},[]);
  async function task(fn){setBusy(true);setError('');setNotice('');try{await fn();}catch(e){setError(e.message);}finally{setBusy(false);}}
  function update(k,v){setForm(f=>({...f,[k]:v}));setPreview(null);}
  async function openRun(id){const result=await api.get(`/api/operational/runs/${id}`);setRun(result);setSelected(result.components[0]?.component_id||'');}
  const component=run?.components.find(c=>c.component_id===selected);
  return <div className="workspace"><PageHeader title="Lot screening workspace" subtitle="Import complete lots, run screening, inspect evidence, and record review decisions."/>
    <section className="work-panel"><h2>Research prototype · {config?.mode||'Loading'}</h2><p>{config?.runtime?.limitations}</p><p>Current: µA. Time: ns. Minimum lot size: 30. Declare the expected lot size from your test manifest before importing.</p>
      {config?.mode==='protected'&&!config.can_write&&<form onSubmit={e=>{e.preventDefault();task(async()=>{api.setToken(key);try{await api.get('/api/operational/access');await refresh();setKey('');}catch(err){api.setToken('');throw err;}});}}><label>Operator key <input type="password" autoComplete="off" value={key} onChange={e=>setKey(e.target.value)} required/></label><button disabled={busy}>Unlock workspace</button></form>}
      {config?.mode==='protected'&&config.can_write&&<button onClick={()=>{api.setToken('');setLots([]);setRun(null);refresh();}}>Lock workspace</button>}
      {config?.mode==='read_only'&&<p>Imports and analysis are disabled. Configure an operator key on the server to enable this workspace.</p>}
      <p>Model runtime: {config?.runtime?.ready?'verified artifacts loaded':'unavailable'}. Reviews use a shared operator identity.</p>
    </section>
    {error&&<p className="work-error" role="alert">{error}</p>}{notice&&<p role="status">{notice}</p>}{busy&&<p role="status">Working… Larger lots may take a moment.</p>}
    <section className="work-panel"><h2>1. Import measurements</h2><div className="work-fields">
      <label>Lot ID<input value={form.lot_id} onChange={e=>update('lot_id',e.target.value)}/></label>
      <label>Variant<select value={form.device_variant} onChange={e=>update('device_variant',e.target.value)}>{['CMOS_A','CMOS_B','CMOS_C'].map(v=><option key={v}>{v}</option>)}</select></label>
      <label>Expected components<input type="number" min="30" max="1000" value={form.expected_count} onChange={e=>update('expected_count',Number(e.target.value))}/></label>
      <label>Measurements through<select value={form.epoch_h} onChange={e=>update('epoch_h',Number(e.target.value))}>{epochs.map(e=><option value={e} key={e}>{e}h</option>)}</select></label>
      <label>CSV file<input type="file" accept=".csv,text/csv" disabled={busy||!config?.can_write} onChange={e=>{const f=e.target.files[0];update('csv_text','');if(f){if(f.size>2000000){setError('CSV must be at most 2 MB.');return;}f.text().then(t=>update('csv_text',t)).catch(()=>setError('Could not read this file.'));}}}/></label>
    </div><p>CSV must contain every epoch up to the selected time. Identical reimports are skipped; conflicting measurements are rejected. Validation makes no permanent changes.</p>
      <div className="work-actions"><button onClick={()=>task(()=>api.download(`/api/operational/template?epoch_h=${form.epoch_h}`,`template_${form.epoch_h}h.csv`))}>Download template</button>
      <a href="/demo/DEMO_A_24h.csv" download>Synthetic training fixture (24h)</a><a href="/demo/DEMO_A_168h.csv" download>Same fixture (168h)</a>
      <button disabled={busy||!config?.can_write||!form.csv_text} onClick={()=>task(async()=>setPreview(await api.post('/api/operational/import/validate',form)))}>Validate CSV</button>
      <button disabled={busy||!preview||!config?.can_write} onClick={()=>task(async()=>{const r=await api.post('/api/operational/import',form);setNotice(`Imported ${r.inserted_measurements} measurements; ${r.unchanged_measurements} unchanged.`);setPreview(null);await refresh();})}>Import validated CSV</button></div>
      {preview&&<p role="status">Valid: {preview.rows} rows, {preview.new_measurements} new measurements. Lot completeness after import: {preview.registered_after_import}/{preview.expected_count}.</p>}
      <p>The downloadable fixture is training data for workflow testing, not independent accuracy evidence. Use its row count as the expected component count.</p>
    </section>
    <section className="work-panel"><h2>2. Analyze a complete lot</h2><button disabled={busy} onClick={()=>task(refresh)}>Refresh lots</button>{!lots.length&&<p>No accessible lots yet. Import a CSV to create a lot.</p>}
    {lots.map(l=><article className="work-lot" key={l.lot_id}><h3>{l.lot_id} · {l.device_variant} · {l.registered}/{l.expected_count} components</h3><div className="work-actions">{epochs.map(e=><button key={e} disabled={busy||!config?.can_write||!config?.runtime?.ready||epochs.filter(t=>t<=e).some(t=>l.epochs[String(t)]!==l.expected_count)} onClick={()=>task(async()=>{const r=await api.post(`/api/operational/lots/${encodeURIComponent(l.lot_id)}/analyze`,{epoch_h:e});await openRun(r.run_id);await refresh();})}>Analyze {e}h ({l.epochs[String(e)]}/{l.expected_count})</button>)}</div><div className="work-actions">{l.runs.map(r=><button key={r.run_id} disabled={busy} onClick={()=>task(()=>openRun(r.run_id))}>Run #{r.run_id} · {r.epoch_h}h</button>)}</div></article>)}
    </section>
    {run&&<section className="work-panel"><h2>3. Review run #{run.run_id} · {run.lot_id} · {run.epoch_h}h</h2><p>{Object.entries(run.counts).map(([k,v])=>`${k}: ${v}`).join(' · ')}</p><p>HOLD means forecast risk; REJECT means an observed specification breach. Early passes are provisional. Missing specification limits are not inferred.</p>
    <div className="work-actions">{['json','csv'].map(f=><button key={f} onClick={()=>task(()=>api.download(`/api/operational/runs/${run.run_id}/export?format=${f}`,`run_${run.run_id}.${f}`))}>Export {f.toUpperCase()}</button>)}</div>
    <label>Component<select value={selected} onChange={e=>setSelected(e.target.value)}>{[...run.components].sort((a,b)=>({REJECT:0,HOLD:1,MONITOR:2,PROVISIONAL_PASS:3,PASS:4}[a.disposition]-{REJECT:0,HOLD:1,MONITOR:2,PROVISIONAL_PASS:3,PASS:4}[b.disposition])).map(c=><option key={c.component_id} value={c.component_id}>{c.disposition} · {c.component_id}</option>)}</select></label>
    {component&&<><h3>{component.disposition} · {component.component_id}</h3><p>{component.reason}</p><div className="work-table"><table><thead><tr>{['Parameter','Unit','Limit','0h','24h','96h','168h','Forecast 168h','Upper bound','Absolute error'].map(h=><th key={h}>{h}</th>)}</tr></thead><tbody>{Object.entries(component.parameters).map(([p,v])=><tr key={p}><th>{p.replaceAll('_',' ')}</th>{[v.unit,v.limit,...epochs.map(e=>v.observed[String(e)]),v.predicted_168h,v.upper_168h,v.absolute_error].map((x,i)=><td key={i}>{x==null?'—':typeof x==='number'?Number(x.toPrecision(5)):x}</td>)}</tr>)}</tbody></table></div>
    <form onSubmit={e=>{e.preventDefault();task(async()=>{await api.post(`/api/operational/runs/${run.run_id}/reviews`,{component_id:selected,action,reason});setReason('');const updated=await api.get(`/api/operational/runs/${run.run_id}`);setRun(updated);setNotice('Review recorded. Original model output preserved.');});}}><h3>Record a review</h3><label>Action<select value={action} onChange={e=>setAction(e.target.value)}>{['ACKNOWLEDGE','REQUEST_RETEST','HOLD','REJECT',...(run.epoch_h===168?['APPROVE']:[])].map(a=><option key={a}>{a}</option>)}</select></label><label>Reason (at least 10 characters)<textarea required minLength={10} maxLength={2000} value={reason} onChange={e=>setReason(e.target.value)}/></label><button disabled={busy||!config?.can_write||reason.trim().length<10}>Save review</button></form>
    <ul>{run.reviews?.filter(r=>r.component_id===selected).map(r=><li key={r.review_id}>{r.created_at} · {r.action} · {r.actor}: {r.reason}</li>)}</ul></>}
    <details><summary>Model provenance and forecast receipt</summary><pre>{JSON.stringify({model:run.model_provenance,forecast:run.forecast_receipt,input_hash:run.input_hash,policy:run.policy_version},null,2)}</pre></details></section>}
  </div>;
}
