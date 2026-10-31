// Local rendering transport. Native SQF retains selection, custody and all treatment actions.
export const VERSION = 2;
const object = v => v !== null && typeof v === 'object' && !Array.isArray(v)
  && [Object.prototype, null].includes(Object.getPrototypeOf(v));
const text = (v, max) => typeof v === 'string' && v.length <= max;
const integer = v => Number.isSafeInteger(v) && v >= 0 && v <= 2_000_000_000;
const reference = v => Array.isArray(v) && v.length === 3 && v.every(x => text(x, 256));
const freeze = v => { if (v && typeof v === 'object') { Object.values(v).forEach(freeze); Object.freeze(v); } return v; };
export function validState(s) {
  if (!object(s) || s.view !== 'transfusion-cards' || !object(s.patient) || !reference(s.patient.ref)
    || !integer(s.patient.epoch) || !Array.isArray(s.cards) || s.cards.length > 2
    || typeof s.canPrevious !== 'boolean' || typeof s.canNext !== 'boolean') return false;
  const slots = new Set(), tokens = new Set();
  return s.cards.every(c => {
    if (!object(c) || ![0,1].includes(c.slot) || slots.has(c.slot) || !text(c.token,64) || !c.token || tokens.has(c.token)
      || !text(c.name,512) || !c.name || !text(c.detail,1024) || !text(c.status,128) || !text(c.thermal,128)
      || !text(c.icon,512) || !text(c.vial,512) || typeof c.selected !== 'boolean'
      || !Array.isArray(c.color) || c.color.length !== 4 || !c.color.every(x => Number.isFinite(x) && x >= 0 && x <= 1)
      || !Number.isFinite(c.fraction) || c.fraction < -1 || c.fraction > 1
      || !Array.isArray(c.marks) || c.marks.length > 11 || !c.marks.every(m => Array.isArray(m) && m.length === 2
        && Number.isFinite(m[0]) && m[0] >= 0 && m[0] <= 1 && Number.isFinite(m[1]) && m[1] >= 0 && m[1] <= 10000)) return false;
    slots.add(c.slot); tokens.add(c.token); return true;
  });
}
export function createMedicalStore(send, now = () => performance.now()) {
  let binding = null, sequence = 0, request = 0, pendingAt = null;
  let snapshot = freeze({status:'loading',state:null,receivedAt:null,pending:false});
  const listeners = new Set();
  const update = value => { snapshot = freeze(value); listeners.forEach(fn => fn()); };
  const emit = (operation, route = []) => {
    if (!binding || request >= 1_000_000) return false;
    send(JSON.stringify({version:VERSION,session:binding.session,sequence:++request,operation,route})); return true;
  };
  const command = (operation, argument) => {
    if (!binding || snapshot.status !== 'connected' || snapshot.pending || now()-snapshot.receivedAt > 3500) return false;
    pendingAt = now(); update({...snapshot,pending:true}); return emit(operation,[argument]);
  };
  return {
    subscribe(fn) { listeners.add(fn); return () => listeners.delete(fn); }, getSnapshot: () => snapshot,
    bootstrap(p) {
      if (!object(p) || p.version !== VERSION || !text(p.session,64) || !p.session || !reference(p.patientRef) || !integer(p.epoch)) return false;
      binding = freeze(structuredClone(p)); sequence = 0; request = 0; pendingAt = null;
      update({status:'loading',state:null,receivedAt:null,pending:false}); return emit('ready');
    },
    receive(p) {
      if (!binding || !object(p) || p.version !== VERSION || p.session !== binding.session || !integer(p.sequence)
        || p.sequence <= sequence || !Number.isFinite(p.capturedAt) || !validState(p.state)
        || p.state.patient.epoch !== binding.epoch || !p.state.patient.ref.every((v,i) => v === binding.patientRef[i])) return false;
      sequence = p.sequence;
      update({status:'connected',state:structuredClone(p.state),receivedAt:now(),pending:snapshot.pending}); return true;
    },
    ack(p) {
      if (!binding || !snapshot.pending || !object(p) || p.version !== VERSION || p.session !== binding.session || p.request !== request) return false;
      pendingAt = null; update({...snapshot,pending:false}); return true;
    },
    checkFreshness() {
      const stale = snapshot.receivedAt !== null && now()-snapshot.receivedAt > 3500;
      const expired = pendingAt !== null && now()-pendingAt > 2000;
      if (expired) pendingAt = null;
      if (stale || expired) update({...snapshot,status:stale ? 'stale' : snapshot.status,pending:expired ? false : snapshot.pending});
    },
    select(token) { return snapshot.state?.cards.some(c => c.token === token) ? command('select',token) : false; },
    wheel(direction) { return [-1,1].includes(direction) ? command('wheel',direction) : false; },
    key(code) { return [200,208,201,209,199,207].includes(code) ? command('key',code) : false; },
    retire() { binding=null; sequence=0; pendingAt=null; update({status:'closed',state:null,receivedAt:null,pending:false}); listeners.clear(); },
  };
}
