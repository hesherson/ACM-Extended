import test from 'node:test';
import assert from 'node:assert/strict';
import {cardLayout} from '../layout.mjs';
for (const [w,h] of [[360,227],[272,171],[210,132],[522,226]]) {
 test(`native card geometry matches at ${w}x${h}`,()=>{
  const u=h/.21,rowH=(h-u*.007)/2,g=cardLayout([w,h,u,rowH,u*.007,Math.floor(u*.007)],{detail:'500 mL',status:'Running',fraction:.5});
  assert.ok(Math.abs(parseFloat(g.name.fontSize)*h/100-u*.018)<.00001);
  assert.ok(Math.abs(parseFloat(g.icon.width)*w/100-Math.min(rowH*.62,u*.052))<.00001);
  assert.ok(Math.abs(parseFloat(g.volume.left)-parseFloat(g.name.left))<.00001);
  assert.ok(parseFloat(g.name.top)>0);assert.ok(parseFloat(g.status.top)+parseFloat(g.status.height)<75.01);
  assert.equal(parseFloat(g.root['--radius'])*h/100,Math.floor(u*.007));
 });
}

import {nativeFontScale} from '../layout.mjs';
test('native measured width calibrates independently of nominal sizeEx and viewport scale',()=>{
 assert.equal(nativeFontScale([100,18],125,522,522),.8);
 assert.equal(nativeFontScale([100,18],250,1044,522),.8);
 const layout=[522,226,1080,109,8,7];
 const card={detail:'712 mL',fraction:.7};
 const normal=cardLayout(layout,card),calibrated=cardLayout(layout,card,.8);
 assert.deepEqual(calibrated.icon,normal.icon);
 assert.deepEqual(calibrated.root,normal.root);
 assert.ok(Math.abs(parseFloat(calibrated.name.fontSize)/parseFloat(normal.name.fontSize)-.8)<.000001);
 for (const width of [0,NaN,Infinity,-1]) assert.equal(nativeFontScale([100,18],width,522,522),null);
});
