// Exercise the packed HTML and native host waveform surface.
const fs=require('fs'),path=require('path'),assert=require('node:assert/strict');
const {chromium}=require(process.env.ACME_PLAYWRIGHT_MODULE||'playwright');
(async()=>{
const browser=await chromium.launch({headless:true,executablePath:process.env.ACME_CHROMIUM_EXECUTABLE,args:['--no-sandbox','--disable-dev-shm-usage']});
for(const [addon,api,hello] of [['acme_tempus','tp','TP|hello'],['acme_tempusls','tls','TLS|hello'],['acme_atak',null,'BATDOK|114.101.97.100.121']]){
 const page=await browser.newPage({viewport:{width:1100,height:800}}),errors=[],messages=[];
 page.on('pageerror',e=>errors.push(e.message));page.on('dialog',async d=>{messages.push(d.message());await d.accept();});
 const file=fs.readdirSync(path.join('addons',addon,'ui')).find(x=>x.endsWith('.html'));
 await page.goto('file://'+path.resolve('addons',addon,'ui',file));await page.waitForTimeout(250);
 assert(messages.some(s=>s.startsWith(hello)),addon+' did not initialize its native bridge');
 if(!api){
  await page.evaluate(()=>{const state='[[2026,11,3,12,0,0,1],"QA Medic",[],[],[],[],[0,"",""]]';batdok.set(Array.from(state,c=>c.charCodeAt(0)));});
  await page.getByText('Callsign: QA Medic',{exact:true}).waitFor();
 }
 if(api){
  assert.equal(await page.evaluate(api=>typeof window[api].waveforms,api),'function');
  await page.evaluate(api=>{window[api].mode('dialog');if(api==='tp')window[api].power(true,12000,true);else window[api].power(true);},api);await page.waitForTimeout(150);
  await page.evaluate(api=>{
   const v=api==='tp'?{hr:73,electricalHR:73,rhythm:0,spo2:96,resp:14,etco2:35,sys:110,dia:70,mean:83,t1:98.6,pi:5}:{hr:73,rhythm:'sinus',pads:true,ecg:true,shockable:false,cpr:false,capture:false};window[api].vitals(v);
   const samples=Array.from({length:176},(_,i)=>i%27===0?-45:0);
   window[api].waveforms([{channel:'ecg',units:'acme',sampleRateHz:33.3333333333,samples},...['I','II','III','AVR','AVL','AVF','V1','V2','V3','V4','V5','V6'].map(lead=>({channel:'ecg',lead,units:'acme',sampleRateHz:33.3333333333,samples}))],true);
  },api);
  const canvas=page.locator('canvas[aria-label="ECG II waveform"]').first();await canvas.waitFor();await page.waitForTimeout(150);const first=await canvas.getAttribute('data-sweep-index');await page.waitForTimeout(150);const second=await canvas.getAttribute('data-sweep-index');assert.notEqual(first,second,'sweep cursor did not advance');
  const pixels=await canvas.evaluate(c=>{const d=c.getContext('2d').getImageData(0,0,c.width,c.height).data;let n=0;for(let i=0;i<d.length;i+=4)if(d[i+1]>80&&d[i+1]>d[i]*1.3)n++;return n;});assert(pixels>0,'host waveform was blank');
  await page.evaluate(api=>window[api].waveforms([{channel:'ecg',units:'acme',sampleRateHz:33.3333333333,samples:Array(176).fill(0)},{channel:'ecg',lead:'II',units:'acme',sampleRateHz:33.3333333333,samples:Array(176).fill(0)}],true),api);await page.waitForTimeout(100);
  if(api==='tp'){await page.evaluate(()=>tp.key('diagnostic'));await page.waitForTimeout(150);assert.equal(await page.locator('.d-diagnostic-lead canvas').count(),12,'diagnostic screen did not draw twelve leads');}
  await page.evaluate(api=>api==='tp'?window[api].power(false,0,false):window[api].power(false),api);await page.waitForTimeout(100);
 }
 assert.deepEqual(errors,[],addon+' browser errors');console.log('PASS',addon,'native handshake, host bridge'+(api?', sweep, power and signal reset':''));await page.close();
}
await browser.close();
})().catch(e=>{console.error(e);process.exit(1);});
