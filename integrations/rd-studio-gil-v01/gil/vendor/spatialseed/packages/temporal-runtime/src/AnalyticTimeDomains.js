export const ANALYTIC_TIME_DOMAINS_VERSION = "analytic-time-domains-v1";

export class AnalyticTimeDomains {
  #domains = new Map();
  #targetDomains = new Map();
  #nowSeconds;

  constructor({ nowSeconds = monotonicSeconds } = {}) {
    if (typeof nowSeconds !== "function") {
      throw new TypeError("nowSeconds deve ser função.");
    }
    this.#nowSeconds = nowSeconds;
    const now = finiteTime(nowSeconds());
    this.#domains.set("world", freezeDomain({
      id: "world",
      parentId: null,
      rate: 1,
      paused: false,
      anchorParentTime: now,
      anchorLocalTime: now,
      revision: 0
    }));
  }

  has(id) {
    return this.#domains.has(normalizeId(id));
  }

  create({
    id,
    parentId = "world",
    rate = 1,
    localTime = null,
    paused = false
  }) {
    const key = normalizeId(id);
    if (this.#domains.has(key)) {
      throw new Error(`Domínio temporal já existe: ${key}.`);
    }
    const parentKey = normalizeId(parentId);
    if (!this.#domains.has(parentKey)) {
      throw new Error(`Domínio temporal pai inexistente: ${parentKey}.`);
    }
    const globalNow = this.now();
    const parentTime = this.time(parentKey, globalNow);
    const initialLocal = localTime === null
      ? parentTime
      : finiteTime(localTime);
    const domain = freezeDomain({
      id: key,
      parentId: parentKey,
      rate: finiteRate(rate),
      paused: Boolean(paused),
      anchorParentTime: parentTime,
      anchorLocalTime: initialLocal,
      revision: 0
    });
    this.#domains.set(key, domain);
    return this.snapshot(key, globalNow);
  }

  delete(id) {
    const key = normalizeId(id);
    if (key === "world") throw new Error("O domínio world não pode ser removido.");
    if (!this.#domains.has(key)) return false;
    const child = [...this.#domains.values()].find(
      domain => domain.parentId === key
    );
    if (child) {
      throw new Error(`Domínio ${key} ainda possui o filho ${child.id}.`);
    }
    this.#domains.delete(key);
    for (const [targetId, domainId] of this.#targetDomains) {
      if (domainId === key) this.#targetDomains.delete(targetId);
    }
    return true;
  }

  now() {
    return finiteTime(this.#nowSeconds());
  }

  time(id = "world", globalTime = this.now()) {
    const key = normalizeId(id);
    const global = finiteTime(globalTime);
    return this.#timeAt(key, global, new Set());
  }

  tick(id = "world", stepSeconds = 1 / 60, globalTime = this.now()) {
    const step = Number(stepSeconds);
    if (!Number.isFinite(step) || step <= 0) {
      throw new RangeError("stepSeconds deve ser positivo.");
    }
    return Math.floor(this.time(id, globalTime) / step);
  }

  setRate(id, rate, globalTime = this.now()) {
    const key = normalizeId(id);
    const nextRate = finiteRate(rate);
    if (this.#require(key).rate === nextRate) return this.snapshot(key, globalTime);
    return this.#reanchor(key, globalTime, domain => ({
      ...domain,
      rate: nextRate
    }));
  }

  pause(id, globalTime = this.now()) {
    const key = normalizeId(id);
    if (this.#require(key).paused) return this.snapshot(key, globalTime);
    return this.#reanchor(key, globalTime, domain => ({
      ...domain,
      paused: true
    }));
  }

  resume(id, globalTime = this.now()) {
    const key = normalizeId(id);
    if (!this.#require(key).paused) return this.snapshot(key, globalTime);
    return this.#reanchor(key, globalTime, domain => ({
      ...domain,
      paused: false
    }));
  }

  seek(id, localTime, globalTime = this.now()) {
    const key = normalizeId(id);
    const target = finiteTime(localTime);
    if (this.time(key, globalTime) === target) return this.snapshot(key, globalTime);
    return this.#reanchor(key, globalTime, domain => ({
      ...domain,
      anchorLocalTime: target
    }), { preserveLocalTime: false });
  }

  setParent(id, parentId, globalTime = this.now()) {
    const key = normalizeId(id);
    const parentKey = normalizeId(parentId);
    if (key === "world") throw new Error("O domínio world não possui pai.");
    if (this.#require(key).parentId === parentKey) return this.snapshot(key, globalTime);
    if (!this.#domains.has(parentKey)) {
      throw new Error(`Domínio temporal pai inexistente: ${parentKey}.`);
    }
    if (this.#wouldCreateCycle(key, parentKey)) {
      throw new Error("A relação temporal criaria um ciclo.");
    }
    return this.#reanchor(key, globalTime, domain => ({
      ...domain,
      parentId: parentKey
    }));
  }

  assignTarget(targetId, domainId = "world") {
    const target = normalizeId(targetId);
    const domain = normalizeId(domainId);
    if (!this.#domains.has(domain)) {
      throw new Error(`Domínio temporal inexistente: ${domain}.`);
    }
    const previous = this.#targetDomains.get(target) ?? "world";
    if (previous === domain) return false;
    if (domain === "world") this.#targetDomains.delete(target);
    else this.#targetDomains.set(target, domain);
    return true;
  }

  domainForTarget(targetId) {
    return this.#targetDomains.get(normalizeId(targetId)) ?? "world";
  }

  effectiveRate(id = "world") {
    const key = normalizeId(id);
    let current = this.#require(key);
    let result = current.paused ? 0 : current.rate;
    const visited = new Set([current.id]);
    while (current.parentId !== null) {
      current = this.#require(current.parentId);
      if (visited.has(current.id)) throw new Error("Ciclo temporal detectado.");
      visited.add(current.id);
      if (current.paused) return 0;
      result *= current.rate;
    }
    return result;
  }

  globalTimeForLocal(id, wakeLocalTime, globalTime = this.now()) {
    const global = finiteTime(globalTime);
    const wake = finiteTime(wakeLocalTime);
    const current = this.time(id, global);
    const rate = this.effectiveRate(id);
    if (rate === 0) return wake === current ? global : Infinity;
    const delta = (wake - current) / rate;
    if (!Number.isFinite(delta)) return Infinity;
    return delta <= 0 ? global : global + delta;
  }

  snapshot(id = "world", globalTime = this.now()) {
    const key = normalizeId(id);
    const domain = this.#require(key);
    const global = finiteTime(globalTime);
    return Object.freeze({
      version: ANALYTIC_TIME_DOMAINS_VERSION,
      id: domain.id,
      parentId: domain.parentId,
      rate: domain.rate,
      effectiveRate: this.effectiveRate(key),
      paused: domain.paused,
      localTime: this.time(key, global),
      globalTime: global,
      revision: domain.revision
    });
  }

  list(globalTime = this.now()) {
    const global = finiteTime(globalTime);
    return Object.freeze(
      [...this.#domains.keys()].sort().map(id => this.snapshot(id, global))
    );
  }

  status(globalTime = this.now()) {
    const global = finiteTime(globalTime);
    return Object.freeze({
      version: ANALYTIC_TIME_DOMAINS_VERSION,
      globalTime: global,
      domains: this.list(global),
      targetAssignments: Object.freeze(Object.fromEntries(
        [...this.#targetDomains.entries()].sort(([a], [b]) => a.localeCompare(b))
      ))
    });
  }

  #timeAt(id, globalTime, visited) {
    const domain = this.#require(id);
    if (visited.has(id)) throw new Error("Ciclo temporal detectado.");
    visited.add(id);
    if (domain.parentId === null) {
      if (domain.paused) return domain.anchorLocalTime;
      return domain.anchorLocalTime +
        (globalTime - domain.anchorParentTime) * domain.rate;
    }
    const parentTime = this.#timeAt(domain.parentId, globalTime, visited);
    if (domain.paused) return domain.anchorLocalTime;
    return domain.anchorLocalTime +
      (parentTime - domain.anchorParentTime) * domain.rate;
  }

  #reanchor(id, globalTime, transform, { preserveLocalTime = true } = {}) {
    const key = normalizeId(id);
    const global = finiteTime(globalTime);
    const current = this.#require(key);
    const local = preserveLocalTime ? this.time(key, global) : current.anchorLocalTime;
    const parentTime = current.parentId === null
      ? global
      : this.time(current.parentId, global);
    const transformed = transform({
      ...current,
      anchorParentTime: parentTime,
      anchorLocalTime: local,
      revision: current.revision + 1
    });
    const nextParentTime = transformed.parentId === null
      ? global
      : this.time(transformed.parentId, global);
    const next = freezeDomain({
      ...transformed,
      anchorParentTime: nextParentTime,
      anchorLocalTime: preserveLocalTime ? local : transformed.anchorLocalTime,
      revision: current.revision + 1
    });
    if (sameDomain(current, next)) return this.snapshot(key, global);
    this.#domains.set(key, next);
    return this.snapshot(key, global);
  }

  #wouldCreateCycle(id, parentId) {
    let current = parentId;
    while (current !== null) {
      if (current === id) return true;
      current = this.#require(current).parentId;
    }
    return false;
  }

  #require(id) {
    const domain = this.#domains.get(id);
    if (!domain) throw new Error(`Domínio temporal inexistente: ${id}.`);
    return domain;
  }
}

function freezeDomain(domain) {
  return Object.freeze({
    id: normalizeId(domain.id),
    parentId: domain.parentId === null ? null : normalizeId(domain.parentId),
    rate: finiteRate(domain.rate),
    paused: Boolean(domain.paused),
    anchorParentTime: finiteTime(domain.anchorParentTime),
    anchorLocalTime: finiteTime(domain.anchorLocalTime),
    revision: Number(domain.revision ?? 0)
  });
}

function sameDomain(a, b) {
  return a.id === b.id &&
    a.parentId === b.parentId &&
    a.rate === b.rate &&
    a.paused === b.paused &&
    a.anchorParentTime === b.anchorParentTime &&
    a.anchorLocalTime === b.anchorLocalTime;
}

function normalizeId(value) {
  const id = String(value ?? "").trim();
  if (!id) throw new TypeError("Identificador temporal vazio.");
  return id;
}

function finiteRate(value) {
  const rate = Number(value);
  if (!Number.isFinite(rate)) throw new RangeError("Taxa temporal deve ser finita.");
  return rate;
}

function finiteTime(value) {
  const time = Number(value);
  if (!Number.isFinite(time)) throw new RangeError("Tempo deve ser finito.");
  return time;
}

function monotonicSeconds() {
  return (globalThis.performance?.now?.() ?? Date.now()) / 1000;
}
