// Run from the repository root with Playwright and Chromium available. Optional ACME_PLAYWRIGHT_MODULE / ACME_CHROMIUM_EXECUTABLE select installed tools.
const fs=require('fs');
const assert=require('node:assert/strict');
const pw=require(process.env.ACME_PLAYWRIGHT_MODULE || 'playwright');
(async()=>{
 const browser=await pw.chromium.launch({headless:true,executablePath:process.env.ACME_CHROMIUM_EXECUTABLE,args:['--no-sandbox','--disable-dev-shm-usage']});
 const html=fs.readFileSync('addons/acm_extended/ui/react/index.html','utf8');
 const hello={version:2,session:'ui:7:1',patientRef:['1:2','mission','patient'],epoch:4};
 const card={slot:0,token:'row:1:0',name:'Saline 750 mL',detail:'Primary',status:'Running',thermal:'LW Quantum / Inline',color:[1,1,1,1],icon:'\\acm_extended\\ui\\bag.paa',vial:'',fraction:.75,marks:Array.from({length:11},(_,i)=>[i/10,i*100]),selected:true};
 const state={view:'transfusion-cards',patient:{ref:hello.patientRef,epoch:4},cards:[card,{...card,slot:1,token:'row:1:1',name:'Blood [PiB] 125 mL',thermal:'',fraction:.5,selected:false,marks:Array.from({length:6},(_,i)=>[i/5,i*50])}],canPrevious:false,canNext:true};
 for(const [width,height] of [[360,227],[272,171],[210,132]]){
  const page=await browser.newPage({viewport:{width:width+40,height:height+40}});
  await page.setContent(`<iframe sandbox="allow-scripts" style="border:0;width:${width}px;height:${height}px"></iframe>`);
  const frame=page.frames()[1];
  await frame.evaluate(()=>{window.messages=[];window.texturePaths=[];window.A3API={SendAlert:s=>window.messages.push(JSON.parse(s)),RequestTexture:(path)=>{window.texturePaths.push(path);return Promise.resolve('data:image/svg+xml;base64,'+btoa('<svg xmlns="http://www.w3.org/2000/svg" width="32" height="64"><rect x="4" y="4" width="24" height="50" fill="white"/></svg>'));}};});
  await frame.setContent(html);
  await frame.evaluate(({hello,state})=>{ACMEUI.bootstrap(hello);ACMEUI.receive({version:2,session:hello.session,sequence:1,capturedAt:10,state});},{hello,state});
  await frame.locator('.card').first().waitFor();await frame.evaluate(()=>document.fonts.ready);
  assert.equal(await frame.getByRole('button').count(),2);
  assert.equal(await frame.getByText('Manage access').count(),0);
  assert.equal(await frame.getByRole('heading').count(),0);
  await frame.getByRole('button').nth(1).focus();
  await frame.evaluate(()=>{window.stableButton=document.querySelectorAll('.card')[1];window.stableImage=document.querySelector('.fluid-icon');window.initialPaths=texturePaths.length;window.baseColor=getComputedStyle(stableButton).backgroundColor;});
  for(let sequence=2;sequence<=26;sequence++){
   await frame.evaluate(({hello,state,sequence})=>ACMEUI.receive({version:2,session:hello.session,sequence,capturedAt:10+sequence/10,state:{...state,cards:state.cards.map(c=>({...c,name:c.slot?'Blood [PiB] '+(150-sequence)+' mL':c.name,fraction:c.fraction-sequence/1000}))}}),{hello,state,sequence});
   await frame.evaluate(()=>new Promise(requestAnimationFrame));
   const stable=await frame.evaluate(()=>({node:document.querySelectorAll('.card')[1]===stableButton,focus:document.activeElement===stableButton,image:document.querySelector('.fluid-icon')===stableImage,paths:texturePaths.length,color:getComputedStyle(stableButton).backgroundColor,base:baseColor,animation:getComputedStyle(stableButton).animationName,transition:getComputedStyle(stableButton).transitionDuration}));
   assert.ok(stable.node&&stable.focus&&stable.image);assert.equal(stable.paths,1);assert.equal(stable.color,stable.base);assert.equal(stable.animation,'none');assert.equal(stable.transition,'0s');
  }
  await frame.getByRole('button').nth(1).click();
  assert.ok(await frame.evaluate(()=>document.querySelectorAll('.card')[1]===stableButton && document.activeElement===stableButton));
  let messages=await frame.evaluate(()=>window.messages);
  assert.equal(messages.at(-1).operation,'select');assert.deepEqual(messages.at(-1).route,['row:1:1']);
  await frame.evaluate(()=>ACMEUI.ack({version:2,session:'ui:7:1',request:2}));
  await frame.getByRole('button').nth(1).press('ArrowDown');
  messages=await frame.evaluate(()=>window.messages);assert.equal(messages.at(-1).operation,'key');assert.deepEqual(messages.at(-1).route,[208]);
  const layout=await frame.evaluate(()=>({scroll:document.documentElement.scrollWidth,width:innerWidth,paths:texturePaths,rects:[...document.querySelectorAll('.card')].map(e=>({y:e.offsetTop,h:e.offsetHeight,w:e.offsetWidth})),font:getComputedStyle(document.querySelector('.name')).fontFamily}));
  assert.equal(layout.scroll,layout.width);assert.ok(layout.paths.every(p=>!p.startsWith('\\')));assert.ok(layout.rects.every(r=>r.y+r.h<=height+1));

  await frame.evaluate(({hello})=>ACMEUI.receive({version:2,session:hello.session,sequence:27,capturedAt:13,state:{view:'transfusion-cards',patient:{ref:hello.patientRef,epoch:4},cards:[],canPrevious:false,canNext:false}}),{hello});
  await frame.getByText('No fluids at this access').waitFor();assert.equal(await frame.getByRole('button').count(),0);
  console.log(JSON.stringify({size:[width,height],...layout,passed:true}));await page.close();
 }
 await browser.close();
})().catch(e=>{console.error(e);process.exitCode=1;});
