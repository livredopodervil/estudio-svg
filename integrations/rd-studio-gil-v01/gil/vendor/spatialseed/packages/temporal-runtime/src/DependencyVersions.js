export const DEPENDENCY_VERSIONS_VERSION = "dependency-versions-v1";

export class DependencyVersions {
  #versions = new Map();

  versionOf(id) {
    return this.#versions.get(normalizeId(id)) ?? 0;
  }

  bump(id) {
    const key = normalizeId(id);
    const next = this.versionOf(key) + 1;
    this.#versions.set(key, next);
    return next;
  }

  set(id, version) {
    const key = normalizeId(id);
    const next = Number(version);
    if (!Number.isInteger(next) || next < 0) {
      throw new RangeError("Versão deve ser inteira e não negativa.");
    }
    const previous = this.versionOf(key);
    if (previous === next) return false;
    this.#versions.set(key, next);
    return true;
  }

  snapshot(ids = null) {
    const keys = ids === null
      ? [...this.#versions.keys()].sort()
      : [...new Set(ids.map(normalizeId))].sort();
    return Object.freeze(Object.fromEntries(
      keys.map(key => [key, this.versionOf(key)])
    ));
  }

  changedSince(snapshot = null) {
    if (!snapshot) return true;
    return Object.entries(snapshot).some(
      ([id, version]) => this.versionOf(id) !== Number(version)
    );
  }

  status() {
    return Object.freeze({
      version: DEPENDENCY_VERSIONS_VERSION,
      entries: this.snapshot()
    });
  }
}

function normalizeId(value) {
  const id = String(value ?? "").trim();
  if (!id) throw new TypeError("Identificador de dependência vazio.");
  return id;
}
