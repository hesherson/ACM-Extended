// Run from the repository root. Requires Playwright; optional module/executable env paths.
const fs=require('fs'),assert=require('node:assert/strict');
const pw=require(process.env.ACME_PLAYWRIGHT_MODULE||'playwright');
let testBrowser;
(async()=>{
 const browser=await pw.chromium.launch({headless:true,executablePath:process.env.ACME_CHROMIUM_EXECUTABLE,args:['--no-sandbox','--disable-dev-shm-usage']});
 testBrowser=browser;
 const css=fs.readFileSync('frontend/medical-ui/tokens.css','utf8')+fs.readFileSync('frontend/medical-ui/style.css','utf8');
 const page=await browser.newPage({viewport:{width:320,height:200}});
 // Separate-surface model, not an Arma engine test. The game-like background
 // is composited AFTER the browser PNG is rendered; the browser cannot sample it.
 // The other case has real content inside the browser for its filter to sample.
 const samples={};
 for(const internal of [false,true]){
  await page.setContent('<style>html,body{margin:0;background:transparent}iframe{border:0;width:320px;height:200px}</style><iframe sandbox="allow-scripts"></iframe>');
  const frame=page.frames()[1];
  await frame.setContent(`<style>${css}html,body{background:transparent}.pattern{position:absolute;inset:0;background:repeating-linear-gradient(90deg,#111 0 4px,#eee 4px 8px)}.card{--card-surface:transparent!important;--card-rule:transparent!important;box-shadow:none!important}</style>${internal?'<div class="pattern"></div>':''}<main class="acme-medical-surface" data-acme-backdrop="internal" style="--gap:8px;--radius:7px"><button class="card" aria-label="Boundary probe"></button></main>`);
  await frame.evaluate(()=>new Promise(requestAnimationFrame));
  const diagnostic=await frame.evaluate(()=>({pattern:document.querySelectorAll(".pattern").length,bg:getComputedStyle(document.body).backgroundImage,html:getComputedStyle(document.documentElement).backgroundColor,button:getComputedStyle(document.querySelector(".card")).backgroundColor,filter:getComputedStyle(document.querySelector(".card")).backdropFilter}));
  const shot=await page.screenshot({omitBackground:true});
  console.log(JSON.stringify({internal,diagnostic}));
  const values=await page.evaluate(async bytes=>{
   const bitmap=await createImageBitmap(new Blob([new Uint8Array(bytes)],{type:'image/png'}));
   const canvas=document.createElement('canvas');canvas.width=bitmap.width;canvas.height=bitmap.height;const context=canvas.getContext('2d');for(let x=0;x<canvas.width;x+=4){context.fillStyle=(x/4)%2?'#eee':'#111';context.fillRect(x,0,4,canvas.height);}context.drawImage(bitmap,0,0);
   const data=context.getImageData(32,40,256,1).data;const line=Array.from({length:256},(_,i)=>data[i*4]);
   return {range:Math.max(...line)-Math.min(...line),meanStep:line.slice(1).reduce((sum,x,i)=>sum+Math.abs(x-line[i]),0)/255};
  },[...shot]);
  samples[internal?'insideBrowser':'outsideBrowser']=values;
 }
 assert.ok(samples.outsideBrowser.range>180 && samples.outsideBrowser.meanStep>40,JSON.stringify(samples));
 assert.ok(samples.insideBrowser.range<35 && samples.insideBrowser.meanStep<5,JSON.stringify(samples));
 await page.setContent(`<style>${css}</style><main class="acme-medical-surface" style="--gap:8px;--radius:7px"><button class="card" aria-label="Normal card"></button></main>`);
 const production=await page.locator('.card').evaluate(el=>({filter:getComputedStyle(el).backdropFilter,animation:getComputedStyle(el).animationName,transition:getComputedStyle(el).transitionDuration,opacity:getComputedStyle(el).opacity}));
 assert.equal(production.filter,'none');assert.equal(production.animation,'none');assert.equal(production.transition,'0s');assert.equal(production.opacity,'1');
 console.log(JSON.stringify({separateSurfaceModel:true,engineTest:false,samples,production,passed:true}));
 await browser.close();
})().catch(async e=>{console.error(e);if(testBrowser)await testBrowser.close();process.exitCode=1;});
