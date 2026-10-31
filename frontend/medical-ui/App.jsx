import React, {useEffect, useState, useSyncExternalStore} from 'react';
import {createRoot} from 'react-dom/client';
import {createMedicalStore} from './bridge.mjs';
import {cardLayout} from './layout.mjs';
const store = createMedicalStore(message => globalThis.A3API?.SendAlert(message));
window.ACMEUI = Object.freeze({bootstrap:p=>store.bootstrap(p),receive:p=>store.receive(p),ack:p=>store.ack(p)});
const textures = new Map();
function Texture({path,className}) {
  const [src,setSrc] = useState(null);
  useEffect(() => {
    let live = true; setSrc(null);
    if (!path || typeof globalThis.A3API?.RequestTexture !== 'function') return;
    if (!textures.has(path)) {
      if (textures.size >= 32) textures.delete(textures.keys().next().value);
      textures.set(path,Promise.resolve().then(()=>globalThis.A3API.RequestTexture(path.replace(/^\\+/,''),128))
        .then(value => typeof value === 'string' && value.startsWith('data:image/') ? value : null).catch(()=>null));
    }
    textures.get(path).then(value => {if (live) setSrc(value);});
    return () => {live=false;};
  },[path]);
  return src ? <img className={className} src={src} alt="" draggable="false"/> : null;
}
const keys = {ArrowUp:200,ArrowDown:208,PageUp:201,PageDown:209,Home:199,End:207};
function Card({card,enabled,layout}) {
  const geometry=cardLayout(layout,card);
  const piggyback = card.name.includes('[PiB]');
  return <button type="button" className={`card ${card.selected?'selected':''} ${piggyback?'piggyback':''} ${card.fraction>=0?'with-track':''}`}
    style={{...geometry.root,gridRow:card.slot+1}} aria-pressed={card.selected} disabled={!enabled}
    title={[card.name,card.detail,card.status,card.thermal].filter(Boolean).join('\n')} onClick={()=>store.select(card.token)}>
    <div className="fluid-icon" style={geometry.icon}><Texture path={card.icon}/></div>
    <div className="name caption" style={{...geometry.name,color:`rgba(${card.color.slice(0,3).map(v=>v*255).join(',')},${card.color[3]})`}}>{card.name}</div>
    {card.detail && <div className="detail caption" style={geometry.detail}>{card.detail}</div>}
    {card.status && <div className="status caption" style={geometry.status}>{card.status}</div>}
    {card.thermal && <div className={`thermal caption ${card.thermal.includes('Warming')?'warming':''}`} style={geometry.thermal}>{card.thermal}</div>}
    <div className="vial-icon" style={geometry.vial}><Texture path={card.vial}/></div>
    {card.fraction>=0 && <div className="volume" style={geometry.volume} role="progressbar" aria-label={`${card.name} remaining volume`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={card.fraction*100}>
      <div className="track"><div className="fill" style={{width:`${card.fraction*100}%`}}/></div>
      {card.marks.map(([fraction,ml])=><span className="mark" key={ml} style={{...geometry.mark,left:`${fraction*100}%`}}><i style={geometry.tick}/>{ml}</span>)}
    </div>}
  </button>;
}
function App() {
  const snapshot=useSyncExternalStore(store.subscribe,store.getSnapshot);
  useEffect(()=>{
    const timer=setInterval(()=>store.checkFreshness(),250);
    const close=()=>{clearInterval(timer);store.retire();};
    window.addEventListener('pagehide',close,{once:true});
    return ()=>{clearInterval(timer);window.removeEventListener('pagehide',close);};
  },[]);
  useEffect(()=>{if(snapshot.state) store.painted();},[snapshot.state]);
  const enabled=snapshot.status==='connected';
  return <main style={cardLayout(snapshot.state?.layout,{}).root} aria-label="Fluids at selected access" onWheel={e=>{e.preventDefault();if(e.deltaY) store.wheel(e.deltaY<0?1:-1);}}
    onKeyDown={e=>{if(keys[e.key]){e.preventDefault();store.key(keys[e.key]);}}}>
    {snapshot.state?.cards.map(card=><Card key={card.token} card={card} enabled={enabled} layout={snapshot.state.layout}/>)}
    {snapshot.state?.cards.length===0 && <p className="empty">No fluids at this access</p>}
  </main>;
}
createRoot(document.getElementById('root')).render(<App/>);
