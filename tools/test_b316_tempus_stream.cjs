/* Test the embedded bridge and packet reader with deterministic browser time and timeouts. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

for (const [suffix, stow, sample, event] of [
    ['tempus','Ol','u4','tempus:waveform'],
    ['tempusls','Qm','_d','tempusLS:waveform']
]) {
    const html = fs.readFileSync(`addons/acme_${suffix}/ui/${suffix}.html`, 'utf8');
    for (const script of html.matchAll(/<script[^>]*>([\s\S]*?)<\/script>/g)) new vm.Script(script[1]);
    const pro = suffix === 'tempus';
    const apiName = pro ? 'tp' : 'tls';
    let time = 100;
    let id = 0;
    const timers = new Map();
    const emitted = [];
    const context = {
        window: {[apiName]: {hasSyncSignal:true}},
        performance: {now:()=>time*1000},
        location: {origin:'null'},
        MessageEvent: class {constructor(_, data){Object.assign(this,data);}},
        setTimeout(fn, ms) { timers.set(++id,{fn, due:time+ms/1000});return id; },
        clearTimeout: key => timers.delete(key)
    };
    context.window.addEventListener = (_,run) => {context.init=run;};
    context.window.dispatchEvent = ({data}) => {
        if (data.type === event) context[stow](data,time);
        else emitted.push(data);
    };
    vm.createContext(context);
    const start = html.indexOf(pro?'function s4(':'function Mo(');
    const end = html.indexOf(pro?'var Dl=H':'var ep=new Set',start);
    const functions = html.slice(start,end);
    const data = pro ? 'wt' : 'Wr';
    vm.runInContext(`const ${data}=new Map();` + functions,context);
    const bridge = html.split('// SQF samples carry offsets')[1].split('</script>')[0].split('\n').slice(1).join('\n');
    vm.runInContext(bridge,context);
    context.init();
    const api = context.window[apiName];
    const advance = t => {
        time = t;
        for (const [key,{fn,due}] of timers) if (due <= t) {timers.delete(key);fn();}
    };
    const leads = ['I','II','III','AVR','AVL','AVF','V1','V2','V3','V4','V5','V6'];
    const packets = (base) => leads.map((lead,i)=>({
        channel:'ecg',lead,units:'acme',sampleRateHz:100,samples:Array.from({length:100},(_,x)=>base+i+x)
    }));
    api.resetWaveforms();
    const deliver = (samples, offset, elapsed, peaks) => {
        for (let first = 0; first < samples.length; first += 3) {
            api.waveformPart(offset, elapsed, first, samples.slice(first, first + 3), samples.length, peaks);
        }
    };
    const firstPackets = packets(0);
    api.waveformPart(0, 0.06, 0, firstPackets.slice(0, 3), firstPackets.length, [30,80]);
    assert.equal(context[sample]('ecg','II',100.1).value, 0);
    deliver(firstPackets, 0, 0.06, [30,80]);
    advance(100.29);
    deliver(packets(100), 1, 0.29, [10]);
    assert.equal(context[sample]('ecg','II',100.5).value,51);
    assert.equal(context[sample]('ecg','II',101).value,101);
    assert.equal(context[sample]('ecg','V6',101).value,111);
    // Duplicated or delayed blocks cannot replace already queued samples or arm extra markers.
    deliver(packets(400), 0, 0.29, [30]);
    assert.equal(context[sample]('ecg','II',100.5).value,51);
    advance(100.30);
    assert.equal(emitted.length,pro?0:1);
    advance(100.80);
    if (!pro) assert.equal(emitted.length,2);
    api.resetWaveforms();
    advance(101.1);
    assert.equal(emitted.length,pro?0:2);
    assert.equal(context[sample]('ecg','V6',101.1).value,0);
    api.waveformPart(0, 0.06, 0, firstPackets.slice(0, 3), firstPackets.length, []);
    api.resetWaveforms();
    api.waveformPart(0, 0.06, 3, firstPackets.slice(3), firstPackets.length, []);
    assert.equal(context[sample]('ecg','III',101.1).value, 0);
    deliver(packets(500), 0, 0.06, []);
    assert.equal(context[sample]('ecg','III',101.1).value,502);
    console.log(`PASS ${suffix} syntax, all lead channels, contiguous timing, replay and episode reset`);
}
