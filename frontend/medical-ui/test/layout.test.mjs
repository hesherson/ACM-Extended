import test from 'node:test';
import assert from 'node:assert/strict';
import {cardLayout} from '../layout.mjs';
for (const [w,h] of [[360,227],[272,171],[210,132],[522,226]]) {
 test(`native card geometry matches at ${w}x${h}`,()=>{
  const u=h/.21,rowH=(h-u*.007)/2,g=cardLayout([w,h,u,rowH,u*.007,Math.floor(u*.007)],{detail:'500 mL',status:'Running',fraction:.5});
  assert.ok(Math.abs(parseFloat(g.name.fontSize)*h/100-u*.018)<.00001);
  assert.ok(Math.abs(parseFloat(g.icon.width)*w/100-u*.030)<.00001);
  assert.ok(Math.abs(parseFloat(g.volume.left)-parseFloat(g.name.left))<.00001);
  assert.ok(parseFloat(g.name.top)>0);assert.ok(parseFloat(g.status.top)+parseFloat(g.status.height)<75.01);
  assert.equal(parseFloat(g.root['--radius'])*h/100,Math.floor(u*.007));
 });
}
