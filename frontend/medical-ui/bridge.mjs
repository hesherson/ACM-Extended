// Shared client boundary for ACME panels and future device shells. No simulated patient state lives here.
export const VERSION = 1;
const parts = new Set(['head', 'body', 'leftarm', 'rightarm', 'leftleg', 'rightleg']);
const object = value => value !== null && typeof value === 'object' && !Array.isArray(value)
  && [Object.prototype, null].includes(Object.getPrototypeOf(value));
const text = (value, max) => typeof value === 'string' && value.length <= max;
const integer = value => Number.isSafeInteger(value) && value >= 0 && value <= 2_000_000_000;
const reference = value => Array.isArray(value) && value.length === 3 && value.every(v => text(v, 256));
const sameRef = (a, b) => a.every((value, i) => value === b[i]);
const freeze = value => {
  if (value && typeof value === 'object') {
    Object.values(value).forEach(freeze);
    Object.freeze(value);
  }
  return value;
};

export function validState(state) {
  if (!object(state) || state.view !== 'transfusion' || !object(state.patient)
    || !reference(state.patient.ref) || !integer(state.patient.epoch) || !text(state.patient.name, 256)
    || !Array.isArray(state.accesses) || state.accesses.length > 24 || typeof state.truncated !== 'boolean'
    || !Array.isArray(state.capabilities) || state.capabilities.length !== 1
    || state.capabilities[0] !== 'native-transfusion'
    || !Array.isArray(state.observations) || state.observations.length !== 0
    || !Array.isArray(state.sources) || state.sources.length !== 0) return false;
  let bags = 0;
  const routes = new Set();
  return state.accesses.every(access => {
    if (!object(access) || !parts.has(access.part) || typeof access.iv !== 'boolean'
      || !integer(access.site) || access.site > 2 || (!access.iv && access.site !== 0)
      || !text(access.label, 256) || !Array.isArray(access.bags)) return false;
    const key = `${access.part}:${access.iv}:${access.site}`;
    if (routes.has(key)) return false;
    routes.add(key);
    bags += access.bags.length;
    return bags <= 128 && access.bags.every(bag => object(bag) && text(bag.label, 512)
      && text(bag.thermal, 128) && text(bag.role, 64) && typeof bag.flowing === 'boolean'
      && Number.isFinite(bag.remainingMl) && bag.remainingMl >= 0
      && Number.isFinite(bag.capacityMl) && bag.capacityMl >= bag.remainingMl
      && Array.isArray(bag.marks) && bag.marks.length <= 11 && bag.marks.every(mark =>
        Array.isArray(mark) && mark.length === 2 && Number.isFinite(mark[0]) && mark[0] >= 0 && mark[0] <= 1
        && Number.isFinite(mark[1]) && mark[1] >= 0 && mark[1] <= bag.capacityMl));
  });
}

export function createMedicalStore(send, now = () => performance.now()) {
  let binding = null;
  let sequence = 0;
  let request = 0;
  let snapshot = freeze({ status: 'loading', state: null, receivedAt: null, pending: false });
  const listeners = new Set();
  const update = value => { snapshot = freeze(value); listeners.forEach(listener => listener()); };
  const emit = (operation, route = []) => {
    if (!binding) return false;
    send(JSON.stringify({ version: VERSION, session: binding.session, sequence: ++request, operation, route }));
    return true;
  };
  return {
    subscribe(listener) { listeners.add(listener); return () => listeners.delete(listener); },
    getSnapshot: () => snapshot,
    bootstrap(packet) {
      if (!object(packet) || packet.version !== VERSION || !text(packet.session, 64) || !packet.session
        || !reference(packet.patientRef) || !integer(packet.epoch)) return false;
      binding = freeze(structuredClone(packet));
      sequence = 0;
      request = 0;
      update({ status: 'loading', state: null, receivedAt: null, pending: false });
      return emit('ready');
    },
    receive(packet) {
      if (!binding || !object(packet) || packet.version !== VERSION || packet.session !== binding.session
        || !integer(packet.sequence) || packet.sequence <= sequence || !Number.isFinite(packet.capturedAt)
        || !validState(packet.state) || packet.state.patient.epoch !== binding.epoch
        || !sameRef(packet.state.patient.ref, binding.patientRef)) return false;
      // Do not retain references into the transport caller's mutable objects.
      const state = structuredClone(packet.state);
      sequence = packet.sequence;
      update({ status: 'connected', state, receivedAt: now(), pending: snapshot.pending });
      return true;
    },
    reject(packet) {
      if (!binding || !snapshot.pending || !object(packet) || packet.version !== VERSION
        || packet.session !== binding.session || packet.request !== request) return false;
      update({ ...snapshot, status: 'stale', pending: false, error: 'Selected access is no longer available.' });
      return true;
    },
    checkFreshness() {
      if (snapshot.receivedAt !== null && now() - snapshot.receivedAt > 3500 && snapshot.status !== 'stale') {
        update({ ...snapshot, status: 'stale' });
      }
    },
    manage(access) {
      if (!binding || snapshot.status !== 'connected' || snapshot.pending || !snapshot.state
        || now() - snapshot.receivedAt > 3500
        || !snapshot.state.accesses.some(row => row.part === access?.part && row.iv === access?.iv && row.site === access?.site)) return false;
      update({ ...snapshot, pending: true });
      return emit('manage', [access.part, access.iv, access.site]);
    },
    retire() {
      binding = null;
      sequence = 0;
      update({ status: 'closed', state: null, receivedAt: null, pending: false });
      listeners.clear();
    },
  };
}
