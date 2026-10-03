import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowRight, ChartNoAxesCombined, Database, ScanSearch } from 'lucide-react';
import ComponentStory from '../components/ComponentStory';
import { SearchInput } from '../components/ui/SearchInput';
import operationalEvaluation from '../data/operationalEvaluation.json';
import './Overview.css';

export default function Overview() {
  const navigate = useNavigate();
  const [hour, setHour] = useState(24);
  const [searchQuery, setSearchQuery] = useState('');
  const review = operationalEvaluation.epochs[String(hour)].review_gate;
  function searchComponent(query) {
    if (query?.trim()) navigate(`/analyze?q=${encodeURIComponent(query.trim())}`);
  }

  return <div className="page-overview">
    <ComponentStory />
    <section className="overview-operational-proof" aria-labelledby="operational-proof-title">
      <div className="proof-heading">
        <div><span>02 / MEASURED PERFORMANCE · SYNTHETIC HOLDOUT</span><h2 id="operational-proof-title">What reached review—and what was missed?</h2><p>Same 1,343 parts across 18 held-out lots at each decision hour. Switch snapshots to see how the review workload changes.</p></div>
        <Link to="/models">Inspect the exact matrix <ArrowRight size={16} aria-hidden="true" /></Link>
      </div>
      <div className="overview-hour-control" role="group" aria-label="Evaluation snapshot">
        {[24, 168].map(epoch => <button key={epoch} type="button" aria-pressed={hour === epoch} onClick={() => setHour(epoch)}>{epoch}h <span>{epoch === 24 ? 'early review' : 'later snapshot'}</span></button>)}
      </div>
      <div className="proof-numbers" aria-live="polite" aria-atomic="true">
        <div><strong>{review.tp} / {operationalEvaluation.defects}</strong><span>Synthetic defects flagged for review</span></div>
        <div className="proof-miss"><strong>{review.fn}</strong><span>Synthetic defects missed</span></div>
        <div><strong>{review.fp}</strong><span>Healthy parts sent for review</span></div>
      </div>
      <p className="overview-proof-note"><strong>{hour}h review gate.</strong> MONITOR, HOLD and REJECT count as alerts. {hour === 24 ? 'Other decisions are provisional passes, not final clearance. ' : ''}These retrospective synthetic results were inspected during development and do not establish performance on physical hardware.</p>
    </section>
    <section className="overview-next" aria-labelledby="overview-next-title">
      <div className="overview-next-heading"><span>03 / CONTINUE THE INSPECTION</span><h2 id="overview-next-title">Go from the result to the evidence</h2><p>Choose the level of detail you need. The saved component explorer and the operational workspace are separate views.</p></div>
      <div className="overview-next-grid">
        <article className="overview-next-card"><ScanSearch size={20} aria-hidden="true"/><h3>Inspect a component</h3><p>Search the frozen synthetic benchmark by component or lot, then follow its readings and forecast.</p><SearchInput value={searchQuery} onChange={setSearchQuery} onSubmit={searchComponent} placeholder="Component ID or lot ID"/><button type="button" className="overview-search-action" disabled={!searchQuery.trim()} onClick={() => searchComponent(searchQuery)}>Inspect search <ArrowRight size={15} aria-hidden="true"/></button><Link to="/components">Browse all 1,343 parts <ArrowRight size={15} aria-hidden="true"/></Link></article>
        <article className="overview-next-card"><ChartNoAxesCombined size={20} aria-hidden="true"/><h3>Examine the evidence</h3><p>See the 24h and 168h confusion matrices, comparison rules, difficult cases, and forecast errors.</p><Link to="/models">Open Models &amp; Metrics <ArrowRight size={15} aria-hidden="true"/></Link></article>
        <article className="overview-next-card"><Database size={20} aria-hidden="true"/><h3>Screen a lot</h3><p>Import a complete measurement file, analyze a snapshot, and record a traceable QA review.</p><Link to="/data">Open Operational Data <ArrowRight size={15} aria-hidden="true"/></Link></article>
      </div>
      <p className="overview-data-footnote">Evidence uses synthetic data: 5,400 generated components across 72 lots, with 1,343 parts in this held-out explorer. <Link to="/system">See the data and pipeline lineage <ArrowRight size={13} aria-hidden="true"/></Link></p>
    </section>
  </div>;
}
