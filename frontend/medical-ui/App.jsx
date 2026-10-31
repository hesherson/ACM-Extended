import React, { useEffect, useState, useSyncExternalStore } from 'react';
import { createRoot } from 'react-dom/client';
import { createMedicalStore } from './bridge.mjs';

const store = createMedicalStore(message => {
  if (typeof globalThis.A3API?.SendAlert !== 'function') throw new Error('Game interface unavailable');
  globalThis.A3API.SendAlert(message);
});
window.ACMEUI = Object.freeze({ bootstrap: packet => store.bootstrap(packet), receive: packet => store.receive(packet), reject: packet => store.reject(packet) });

function App() {
  const snapshot = useSyncExternalStore(store.subscribe, store.getSnapshot);
  const [selection, setSelection] = useState(null);
  useEffect(() => {
    const timer = setInterval(() => store.checkFreshness(), 500);
    const close = () => { clearInterval(timer); store.retire(); };
    window.addEventListener('pagehide', close, { once: true });
    return () => { clearInterval(timer); window.removeEventListener('pagehide', close); };
  }, []);
  const state = snapshot.state;
  const key = row => `${row.part}:${row.iv}:${row.site}`;
  const current = state?.accesses.find(row => key(row) === selection) ?? state?.accesses[0];
  const enabled = snapshot.status === 'connected' && !snapshot.pending;
  return <main>
    <header><div><span className="eyebrow">CIRCULATION</span><h1>{state?.patient.name || 'Loading patient…'}</h1></div>
      <span className={`connection ${snapshot.status}`}>{snapshot.status === 'connected' ? 'Connected' : snapshot.status === 'stale' ? 'Connection lost' : 'Connecting'}</span></header>
    <div className="workspace">
      <nav aria-label="Established vascular access"><div className="section-label">ESTABLISHED ACCESS <span>{state?.accesses.length ?? '—'}</span></div>
        {state?.accesses.map(row => <button className={`access ${current === row ? 'selected' : ''}`} key={key(row)} onClick={() => setSelection(key(row))}>
          <span className="access-kind">{row.iv ? 'IV' : 'IO'}</span><span><strong>{row.label}</strong><small>{row.bags.length ? `${row.bags.length} connected ${row.bags.length === 1 ? 'bag' : 'bags'}` : 'No bag connected'}</small></span><span className="chevron">›</span></button>)}
        {state && !state.accesses.length && <p className="empty">No established IV/IO access.</p>}
      </nav>
      <section className="detail" aria-label="Connected fluid bags">
        <div className="detail-heading"><div><span className="eyebrow">SELECTED ACCESS</span><h2>{current?.label || 'Vascular access'}</h2></div>
          <button className="primary" disabled={!enabled || !current} onClick={() => store.manage(current)}>{snapshot.pending ? 'Opening…' : 'Manage access'}</button></div>
        <div className="bags">{current?.bags.map((bag, index) => <article className="bag" key={index}>
          <div className="bag-top"><div><span className="eyebrow">{bag.role || 'CONNECTED FLUID'}</span><h3>{bag.label}</h3></div><span className={`flow ${bag.flowing ? 'running' : ''}`}>{bag.flowing ? 'Running' : 'Not running'}</span></div>
          <div className="volume"><strong>{bag.remainingMl.toLocaleString()}<small> mL</small></strong><span>{bag.capacityMl.toLocaleString()} mL capacity</span></div>
          <div className="progress" role="progressbar" aria-label={`${bag.label} remaining volume`} aria-valuenow={bag.remainingMl} aria-valuemin={0} aria-valuemax={bag.capacityMl || 1}><div style={{ width: `${bag.capacityMl ? 100 * bag.remainingMl / bag.capacityMl : 0}%` }} /></div>
          <div className="graduations" aria-hidden="true">{bag.marks.map(([fraction, ml]) => <span key={ml} style={{ left: `${fraction * 100}%`, transform: fraction === 0 ? 'none' : fraction === 1 ? 'translateX(-100%)' : 'translateX(-50%)' }}>{ml}</span>)}</div>
          {bag.thermal && <p className="thermal">{bag.thermal}</p>}
        </article>)}</div>
        {current && !current.bags.length && <div className="empty-panel"><span className="empty-symbol">＋</span><h3>No bag connected</h3></div>}
        {state?.truncated && <p className="notice">Additional bags are available in Native controls.</p>}
        {snapshot.error && <p className="notice" role="alert">{snapshot.error}</p>}
      </section>
    </div>
  </main>;
}

createRoot(document.getElementById('root')).render(<App />);
