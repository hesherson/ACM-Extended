import React, {useEffect, useMemo, useRef, useState, useSyncExternalStore} from 'react';
import {createRoot} from 'react-dom/client';
import {createMedicalStore} from './bridge.mjs';
import {cardLayout, nativeFontScale, FONT_PROBE} from './layout.mjs';
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
function Card({card,enabled,layout,fontScale}) {
  const geometry=cardLayout(layout,card,fontScale);
  const piggyback = card.name.includes('[PiB]');
  return <button type="button" className={`card ${card.selected?'selected':''} ${piggyback?'piggyback':''} ${card.fraction>=0?'with-track':''}`}
    style={{...geometry.root,gridRow:card.slot+1}} aria-pressed={card.selected} disabled={!enabled}
    title={[card.name,card.detail,card.status,card.thermal].filter(Boolean).join('\n')} onClick={()=>store.select(card.token)}>
    <div className="fluid-icon" style={geometry.icon}><Texture path={card.icon}/></div>
    <div className="name caption" style={{...geometry.name,'--color-clinical':`rgba(${card.color.slice(0,3).map(v=>v*255).join(',')},${card.color[3]})`}}>{card.name}</div>
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
  const fontKey=JSON.stringify([snapshot.state?.fontProbe,snapshot.state?.layout]);
  const [fontReady,setFontReady]=useState(false);
  const needsFont=Boolean(snapshot.state?.fontProbe);
  useEffect(()=>{
    if (!needsFont || fontReady) return;
    let live=true;
    document.fonts.load('18px "Roboto Condensed"',FONT_PROBE).then(()=>{
      if (!live) return;
      if (document.fonts.check('18px "Roboto Condensed"',FONT_PROBE)) setFontReady(true);
      else store.fallback();
    }).catch(()=>{if(live) store.fallback();});
    return ()=>{live=false;};
  },[needsFont,fontReady]);
  // Once loaded, measure the same face synchronously on metric changes. Never
  // unmount a painted card or start another asynchronous font load for layout.
  const scale=useMemo(()=>{
    const probe=snapshot.state?.fontProbe,layout=snapshot.state?.layout;
    if (!probe) return 1;
    if (!fontReady) return null;
    try {
      const context=document.createElement('canvas').getContext('2d');
      if (!context) return null;
      context.font=`${probe[1]*document.documentElement.clientHeight/layout[1]}px "Roboto Condensed"`;
      return nativeFontScale(probe,context.measureText(FONT_PROBE).width,document.documentElement.clientWidth,layout[0]);
    } catch {return null;}
  },[fontReady,fontKey]);
  const previousScale=useRef(1);
  useEffect(()=>{
    if (scale !== null) previousScale.current=scale;
    else if (fontReady && needsFont) store.fallback();
  },[scale,fontReady,needsFont]);
  const calibrated=scale !== null;
  const renderCards=!needsFont || fontReady;
  useEffect(()=>{
    const timer=setInterval(()=>store.checkFreshness(),250);
    const close=()=>{clearInterval(timer);store.retire();};
    window.addEventListener('pagehide',close,{once:true});
    return ()=>{clearInterval(timer);window.removeEventListener('pagehide',close);};
  },[]);
  useEffect(()=>{
    if (!snapshot.state || !calibrated) return;
    const frame=requestAnimationFrame(()=>store.painted());
    return ()=>cancelAnimationFrame(frame);
  },[snapshot.state,calibrated]);
  const enabled=snapshot.status==='connected';
  return <main className="acme-medical-surface" style={{...cardLayout(snapshot.state?.layout,{}).root,'--text-inset':`${100*(snapshot.state?.fontProbe?.[2]||0)/(snapshot.state?.layout?.[1]||1)}vh`}} aria-label="Fluids at selected access" onWheel={e=>{e.preventDefault();if(e.deltaY) store.wheel(e.deltaY<0?1:-1);}}
    onKeyDown={e=>{if(keys[e.key]){e.preventDefault();store.key(keys[e.key]);}}}>
    {renderCards && snapshot.state?.cards.map(card=><Card key={card.token} card={card} enabled={enabled} layout={snapshot.state.layout} fontScale={scale ?? previousScale.current}/>)}
  </main>;
}
createRoot(document.getElementById('root')).render(<App/>);
