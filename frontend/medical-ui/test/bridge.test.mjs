import test from 'node:test';
import assert from 'node:assert/strict';
import { createMedicalStore, validState } from '../bridge.mjs';

const binding = { version: 1, session: 'ui:7:1', patientRef: ['1:2', 'mission-a', 'casualty-a'], epoch: 4 };
export const state = () => ({ view: 'transfusion', patient: { ref: [...binding.patientRef], epoch: 4, name: 'Casualty A' },
  accesses: [{ part: 'leftarm', iv: true, site: 1, label: 'Left arm / Middle IV', bags: [
    { label: 'Saline', remainingMl: 750, capacityMl: 1000, thermal: '', role: '', flowing: true, marks: [[0, 0], [0.5, 500], [1, 1000]] },
  ] }], truncated: false, capabilities: ['native-transfusion'], observations: [], sources: [] });
const packet = (sequence = 1) => ({ version: 1, session: binding.session, sequence, capturedAt: 25, state: state() });
const fixture = () => {
  const sent = [];
  let clock = 0;
  const store = createMedicalStore(text => sent.push(JSON.parse(text)), () => clock);
  store.bootstrap(binding);
  return { store, sent, tick: value => { clock = value; } };
};

test('handshake and captured-route action use one shared session with increasing request identity', () => {
  const { store, sent } = fixture();
  assert.deepEqual(sent, [{ version: 1, session: binding.session, sequence: 1, operation: 'ready', route: [] }]);
  assert.equal(store.manage(state().accesses[0]), false);
  assert.equal(store.receive(packet()), true);
  assert.equal(store.manage(state().accesses[0]), true);
  assert.deepEqual(sent[1], { version: 1, session: binding.session, sequence: 2, operation: 'manage', route: ['leftarm', true, 1] });
  assert.equal(store.manage(state().accesses[0]), false);
  assert.equal(sent.length, 2);
});

for (const [label, change] of [
  ['different session', p => { p.session = 'old'; }],
  ['different patient', p => { p.state.patient.ref[0] = '2:9'; }],
  ['different mission', p => { p.state.patient.ref[1] = 'restarted'; }],
  ['different clinical epoch', p => { p.state.patient.epoch++; }],
  ['unknown version', p => { p.version = 2; }],
  ['invalid sequence', p => { p.sequence = 0; }],
  ['nonfinite acquisition clock', p => { p.capturedAt = NaN; }],
  ['nonfinite volume', p => { p.state.accesses[0].bags[0].remainingMl = Infinity; }],
  ['wrong site type', p => { p.state.accesses[0].site = '1'; }],
  ['duplicate route', p => { p.state.accesses.push(structuredClone(p.state.accesses[0])); }],
  ['unimplemented observation', p => { p.state.observations = [{ hr: 80 }]; }],
]) test(`reject ${label} without changing the visible patient`, () => {
  const { store } = fixture();
  const p = packet(); change(p);
  assert.equal(store.receive(p), false);
  assert.equal(store.getSnapshot().state, null);
});

test('duplicate/reordered state cannot rewind data or clear a pending action', () => {
  const { store } = fixture();
  assert.equal(store.receive(packet(3)), true);
  assert.equal(store.manage(state().accesses[0]), true);
  assert.equal(store.receive(packet(2)), false);
  assert.equal(store.receive(packet(3)), false);
  assert.equal(store.receive(packet(4)), true);
  assert.equal(store.getSnapshot().pending, true);
});

test('new bootstrap clears previous patient state and fences delayed former-session packets', () => {
  const { store } = fixture();
  store.receive(packet());
  store.bootstrap({ ...binding, session: 'ui:7:2' });
  assert.equal(store.getSnapshot().state, null);
  assert.equal(store.receive(packet(99)), false);
});

test('stale data disables handoff and a real heartbeat restores freshness', () => {
  const { store, tick } = fixture();
  store.receive(packet()); tick(3501);
  assert.equal(store.manage(state().accesses[0]), false);
  store.checkFreshness();
  assert.equal(store.getSnapshot().status, 'stale');
  store.receive(packet(2));
  assert.equal(store.getSnapshot().status, 'connected');
});

test('removed access cannot be requested from an earlier render', () => {
  const { store } = fixture();
  store.receive(packet());
  const empty = packet(2); empty.state.accesses = [];
  store.receive(empty);
  assert.equal(store.manage(state().accesses[0]), false);
});

test('an exact rejected handoff releases pending state without permitting a stale retry', () => {
  const { store } = fixture();
  store.receive(packet()); store.manage(state().accesses[0]);
  assert.equal(store.reject({ version: 1, session: 'old', request: 2 }), false);
  assert.equal(store.reject({ version: 1, session: binding.session, request: 1 }), false);
  assert.equal(store.getSnapshot().pending, true);
  assert.equal(store.reject({ version: 1, session: binding.session, request: 2 }), true);
  assert.equal(store.getSnapshot().pending, false);
  assert.equal(store.manage(state().accesses[0]), false);
  store.receive(packet(2));
  assert.equal(store.manage(state().accesses[0]), true);
});

test('transport caller mutation cannot rewrite an accepted state snapshot', () => {
  const { store } = fixture();
  const p = packet(); store.receive(p); p.state.patient.name = 'Changed outside transport';
  assert.equal(store.getSnapshot().state.patient.name, 'Casualty A');
  assert.equal(Object.isFrozen(store.getSnapshot().state.accesses[0].bags[0]), true);
});

test('closed views release subscribers, patient data and command authority', () => {
  const { store } = fixture();
  let calls = 0; store.subscribe(() => { calls++; });
  store.receive(packet()); store.retire();
  assert.equal(calls, 2);
  assert.equal(store.receive(packet(2)), false);
  assert.equal(store.manage(state().accesses[0]), false);
  assert.equal(store.getSnapshot().state, null);
});

test('bounded rows and numeric ranges reject oversized or impossible payloads', () => {
  const s = state();
  s.accesses[0].bags = Array.from({ length: 129 }, () => structuredClone(s.accesses[0].bags[0]));
  assert.equal(validState(s), false);
  const empty = state(); empty.accesses[0].bags[0].remainingMl = 0;
  assert.equal(validState(empty), true);
});
