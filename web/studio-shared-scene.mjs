/** M2 experimental: routing of typed operations to existing renderers.
 * This module DOES NOT own time, geometry, animation or export. The Studio
 * provides the logical time; SpatialSeed/GIL/SVG own their native renderers.
 */
export const SPACES = Object.freeze(['spatialseed', 'svg', 'media']);
const allowed = new Set(SPACES);
const identifier = /^[A-Za-z0-9][A-Za-z0-9_.:\-]{0,127}$/;
function requireId(value, label) {
  if (typeof value !== 'string' || !identifier.test(value))
    throw new TypeError(`${label}: identificador inválido`);
  return value;
}
export function objectRef(space, id) {
  if (!allowed.has(space)) throw new TypeError('Espaço desconhecido');
  return Object.freeze({space, id: requireId(id, 'objeto')});
}
export function sceneEvent({type, source, target = null, payload = null}) {
  const event = {
    type: requireId(type, 'evento'),
    source: objectRef(source?.space, source?.id),
    target: target ? objectRef(target.space, target.id) : null,
    payload,
  };
  if (JSON.stringify(event).length > 65536)
    throw new RangeError('Evento acima de 64 KiB');
  return Object.freeze(event);
}
/**
 * Adapter contract:
 *   seek(t)                receives same Studio logical seconds as all adapters
 *   set(id, property, v)   applies an already evaluated property
 *   event(id, envelope)   receives a routed, typed event
 *   renderAt(t)            renders at the same logical instant (optional)
 * No automatic code evaluation or undeclared cross-layer effects.
 */
export function createSharedSceneBridge(adapters) {
  if (!adapters || typeof adapters !== 'object' || Array.isArray(adapters))
    throw new TypeError('Adaptadores são obrigatórios');
  const registered = SPACES.filter(space => Object.hasOwn(adapters, space));
  for (const space of registered) {
    const a = adapters[space];
    if (!a || typeof a.seek !== 'function')
      throw new TypeError(`Adaptador ${space} sem seek(t)`);
  }
  return Object.freeze({
    /** Provide time from the Studio; does not create a second clock. */
    at(time, operations = []) {
      if (typeof time !== 'number' || !Number.isFinite(time) || time < 0 || time > 86400)
        throw new RangeError('Tempo lógico inválido');
      if (!Array.isArray(operations) || operations.length > 4096)
        throw new RangeError('Número de operações inválido');
      // Validate completely BEFORE touching any renderer.
      const work = operations.map(op => {
        if (!op || (op.kind !== 'set' && op.kind !== 'event'))
          throw new TypeError('Operação tipada inválida');
        const target = objectRef(op.target?.space, op.target?.id);
        const adapter = adapters[target.space];
        if (!adapter) throw new Error(`Espaço sem adaptador: ${target.space}`);
        if (op.kind === 'set') {
          const property = requireId(op.property, 'propriedade');
          if (typeof adapter.set !== 'function') throw new Error('Adaptador sem set');
          return {kind: 'set', adapter, id: target.id, property, value: op.value};
        }
        if (typeof adapter.event !== 'function') throw new Error('Adaptador sem event');
        const envelope = sceneEvent({...op.event, target});
        return {kind: 'event', adapter, id: target.id, envelope};
      });
      for (const space of registered) adapters[space].seek(time);
      for (const op of work) {
        if (op.kind === 'set') op.adapter.set(op.id, op.property, op.value);
        else op.adapter.event(op.id, op.envelope);
      }
      for (const space of registered) adapters[space].renderAt?.(time);
      return Object.freeze({time, operations: work.length, spaces: registered.slice()});
    },
  });
}
