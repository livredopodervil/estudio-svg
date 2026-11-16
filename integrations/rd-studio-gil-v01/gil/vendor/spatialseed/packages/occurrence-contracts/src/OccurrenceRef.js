export const OCCURRENCE_REF_VERSION = "occurrence-ref-v1";

export function createOccurrenceRef({ rootInstanceId, path = [] } = {}) {
  const root = normalizeId(rootInstanceId, "rootInstanceId");
  const normalizedPath = Object.freeze((path ?? []).map((segment, index) =>
    normalizeId(segment, `path[${index}]`)
  ));
  return Object.freeze({
    version: OCCURRENCE_REF_VERSION,
    rootInstanceId: root,
    path: normalizedPath
  });
}

export function normalizeOccurrenceRef(value) {
  if (isOccurrenceRef(value)) return value;
  return createOccurrenceRef(value);
}

export function isOccurrenceRef(value) {
  return Boolean(
    value &&
    typeof value === "object" &&
    value.version === OCCURRENCE_REF_VERSION &&
    typeof value.rootInstanceId === "string" &&
    value.rootInstanceId.length > 0 &&
    Array.isArray(value.path) &&
    value.path.every(segment => typeof segment === "string" && segment.length > 0)
  );
}

export function occurrenceRefKey(ref) {
  const normalized = normalizeOccurrenceRef(ref);
  return JSON.stringify([normalized.rootInstanceId, ...normalized.path]);
}

export function occurrenceRefEquals(left, right) {
  if (left === right) return true;
  const a = normalizeOccurrenceRef(left);
  const b = normalizeOccurrenceRef(right);
  if (a.rootInstanceId !== b.rootInstanceId || a.path.length !== b.path.length) return false;
  return a.path.every((segment, index) => segment === b.path[index]);
}

export function parentOccurrenceRef(ref) {
  const normalized = normalizeOccurrenceRef(ref);
  if (!normalized.path.length) return null;
  return createOccurrenceRef({
    rootInstanceId: normalized.rootInstanceId,
    path: normalized.path.slice(0, -1)
  });
}

export function childOccurrenceRef(ref, slotId) {
  const normalized = normalizeOccurrenceRef(ref);
  return createOccurrenceRef({
    rootInstanceId: normalized.rootInstanceId,
    path: [...normalized.path, normalizeId(slotId, "slotId")]
  });
}

function normalizeId(value, label) {
  const id = String(value ?? "").trim();
  if (!id) throw new TypeError(`${label} deve ser um identificador não vazio.`);
  return id;
}
