import React, { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Sidebar } from './components/layout/Sidebar';
const Overview = lazy(() => import('./pages/Overview'));
const Analyze = lazy(() => import('./pages/Analyze'));
const ComponentDetail = lazy(() => import('./pages/ComponentDetail'));
const Components = lazy(() => import('./pages/Components'));
const Data = lazy(() => import('./pages/Data'));
const Models = lazy(() => import('./pages/Models'));
const System = lazy(() => import('./pages/System'));
import './App.css';

function App() {
  return (
    <BrowserRouter>
      <div className="app-container">
        <Sidebar />
        <main className="main-content">
          <Suspense fallback={<p role="status">Loading page…</p>}><Routes>
            <Route path="/" element={<Overview />} />
            <Route path="/analyze" element={<Analyze />} />
            <Route path="/analyze/:componentId" element={<ComponentDetail />} />
            <Route path="/components" element={<Components />} />
            <Route path="/data" element={<Data />} />
            <Route path="/models" element={<Models />} />
            <Route path="/system" element={<System />} />
          <Route path="*" element={<section><h1>Page not found</h1><a href="/">Return to overview</a></section>} />
          </Routes></Suspense>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
