export const EVOLUTION_RESULT_VERSION = "evolution-result-v1";

export const EvolutionKind = Object.freeze({
  CHANGED: "changed",
  IDENTITY: "identity",
  FIXED_POINT: "fixed-point",
  SLEEP_UNTIL: "sleep-until"
});

const RESULT_MARKER = Symbol.for("spatialseed.evolution-result");
const EMPTY_LIST = Object.freeze([]);
const IDENTITY_RESULT = freezeResult({
  kind: EvolutionKind.IDENTITY,
  changes: EMPTY_LIST,
  events: EMPTY_LIST,
  value: null,
  dependencyVersions: null,
  wakeLocalTime: null
});

export class EvolutionResult {
  static changed(changes = [], {
    events = EMPTY_LIST,
    value = null
  } = {}) {
    const normalizedChanges = normalizeList(changes, "changes");
    const normalizedEvents = normalizeList(events, "events");
    if (!normalizedChanges.length && !normalizedEvents.length && value === null) {
      return IDENTITY_RESULT;
    }
    return freezeResult({
      kind: EvolutionKind.CHANGED,
      changes: normalizedChanges,
      events: normalizedEvents,
      value,
      dependencyVersions: null,
      wakeLocalTime: null
    });
  }

  static identity() {
    return IDENTITY_RESULT;
  }

  static fixedPoint({
    dependencyVersions = null,
    value = null
  } = {}) {
    return freezeResult({
      kind: EvolutionKind.FIXED_POINT,
      changes: EMPTY_LIST,
      events: EMPTY_LIST,
      value,
      dependencyVersions: normalizeDependencyVersions(dependencyVersions),
      wakeLocalTime: null
    });
  }

  static sleepUntil(wakeLocalTime, { value = null } = {}) {
    const wake = Number(wakeLocalTime);
    if (!Number.isFinite(wake)) {
      throw new RangeError("wakeLocalTime deve ser finito.");
    }
    return freezeResult({
      kind: EvolutionKind.SLEEP_UNTIL,
      changes: EMPTY_LIST,
      events: EMPTY_LIST,
      value,
      dependencyVersions: null,
      wakeLocalTime: wake
    });
  }

  static normalize(candidate) {
    if (candidate?.[RESULT_MARKER] === true) return candidate;
    if (candidate === undefined || candidate === null || candidate === false) {
      return IDENTITY_RESULT;
    }
    if (Array.isArray(candidate)) return EvolutionResult.changed(candidate);
    return EvolutionResult.changed([candidate], { value: candidate });
  }

  static is(candidate) {
    return candidate?.[RESULT_MARKER] === true;
  }
}

export function normalizeEvolutionResult(candidate) {
  return EvolutionResult.normalize(candidate);
}

function freezeResult({
  kind,
  changes,
  events,
  value,
  dependencyVersions,
  wakeLocalTime
}) {
  return Object.freeze({
    [RESULT_MARKER]: true,
    version: EVOLUTION_RESULT_VERSION,
    kind,
    changed: kind === EvolutionKind.CHANGED,
    changes,
    events,
    value,
    dependencyVersions,
    wakeLocalTime
  });
}

function normalizeList(value, label) {
  if (value === undefined || value === null) return EMPTY_LIST;
  if (!Array.isArray(value)) {
    throw new TypeError(`${label} deve ser uma lista.`);
  }
  return Object.freeze([...value]);
}

function normalizeDependencyVersions(value) {
  if (value === undefined || value === null) return null;
  const entries = value instanceof Map
    ? [...value.entries()]
    : Object.entries(value);
  return Object.freeze(Object.fromEntries(
    entries.map(([key, version]) => {
      const normalized = Number(version);
      if (!Number.isInteger(normalized) || normalized < 0) {
        throw new RangeError(`Versão inválida para ${key}.`);
      }
      return [String(key), normalized];
    })
  ));
}
