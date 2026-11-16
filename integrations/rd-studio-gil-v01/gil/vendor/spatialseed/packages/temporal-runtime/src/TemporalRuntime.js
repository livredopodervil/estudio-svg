import {
  EvolutionKind,
  EvolutionResult
} from "./EvolutionResult.js?build=20260806-0050a1";
import {
  DependencyVersions
} from "./DependencyVersions.js?build=20260806-0050a1";
import {
  AnalyticTimeDomains
} from "./AnalyticTimeDomains.js?build=20260806-0050a1";

export const TEMPORAL_RUNTIME_VERSION = "temporal-runtime-v2";

export class TemporalRuntime {
  #domains;
  #dependencies;
  #operations = new Map();
  #listeners = new Set();
  #sequence = 0;
  #statistics = initialStatistics();

  constructor({
    domains = new AnalyticTimeDomains(),
    dependencies = new DependencyVersions()
  } = {}) {
    if (!domains?.time || !domains?.globalTimeForLocal) {
      throw new TypeError("TemporalRuntime exige domínios temporais analíticos.");
    }
    if (!dependencies?.versionOf || !dependencies?.changedSince) {
      throw new TypeError("TemporalRuntime exige versões de dependências.");
    }
    this.#domains = domains;
    this.#dependencies = dependencies;
  }

  get domains() {
    return this.#domains;
  }

  get dependencies() {
    return this.#dependencies;
  }

  subscribe(listener) {
    if (typeof listener !== "function") {
      throw new TypeError("Listener temporal deve ser função.");
    }
    this.#listeners.add(listener);
    return () => this.#listeners.delete(listener);
  }

  register({
    id,
    evaluate,
    phase = "behavior",
    order = 0,
    timeDomainId = "world",
    targetId = null,
    dependencyIds = [],
    enabled = true,
    idempotent = false
  }) {
    const key = normalizeId(id);
    if (this.#operations.has(key)) {
      throw new Error(`Operação temporal já registrada: ${key}.`);
    }
    if (typeof evaluate !== "function") {
      throw new TypeError("Operação temporal exige evaluate().");
    }
    const domainId = normalizeId(timeDomainId);
    if (!this.#domains.has(domainId)) {
      throw new Error(`Domínio temporal inexistente: ${domainId}.`);
    }
    const normalizedDependencies = Object.freeze(
      [...new Set(dependencyIds.map(normalizeId))].sort()
    );
    const operation = {
      id: key,
      evaluate,
      phase: normalizeId(phase),
      order: finiteOrder(order),
      sequence: this.#sequence++,
      timeDomainId: domainId,
      targetId: targetId === null ? null : normalizeId(targetId),
      dependencyIds: normalizedDependencies,
      enabled: Boolean(enabled),
      idempotent: Boolean(idempotent),
      fixedPointVersions: null,
      wakeLocalTime: null,
      lastEvaluationLocalTime: null,
      lastEvaluationDependencyVersions: this.#dependencies.snapshot(
        normalizedDependencies
      ),
      evaluations: 0,
      identities: 0,
      changes: 0,
      skips: 0
    };
    this.#operations.set(key, operation);
    this.#notify("registered", { operationId: key });
    return this.describe(key);
  }

  unregister(id) {
    const key = normalizeId(id);
    const changed = this.#operations.delete(key);
    if (changed) this.#notify("unregistered", { operationId: key });
    return changed;
  }

  enable(id, enabled = true) {
    const operation = this.#require(id);
    const next = Boolean(enabled);
    if (operation.enabled === next) return false;
    operation.enabled = next;
    if (next) this.#wakeOperation(operation);
    this.#notify(next ? "enabled" : "disabled", {
      operationId: operation.id
    });
    return true;
  }

  wake(id) {
    const operation = this.#require(id);
    const changed = this.#wakeOperation(operation);
    if (changed) this.#notify("woken", { operationId: operation.id });
    return changed;
  }

  wakeAll() {
    let count = 0;
    for (const operation of this.#operations.values()) {
      if (this.#wakeOperation(operation)) count += 1;
    }
    if (count > 0) this.#notify("wake-all", { count });
    return count;
  }

  wakeByDependency(dependencyId) {
    const id = normalizeId(dependencyId);
    let count = 0;
    for (const operation of this.#operations.values()) {
      if (!operation.dependencyIds.includes(id)) continue;
      if (this.#wakeOperation(operation)) count += 1;
    }
    if (count > 0) {
      this.#notify("dependency-wake", { dependencyId: id, count });
    }
    return count;
  }

  bumpDependency(dependencyId) {
    const id = normalizeId(dependencyId);
    const version = this.#dependencies.bump(id);
    const count = this.#wakeByDependencyInternal(id);
    this.#notify("dependency-bumped", {
      dependencyId: id,
      version,
      wakeCount: count
    });
    return version;
  }

  bumpDependencies(dependencyIds = []) {
    const ids = [...new Set(dependencyIds.map(normalizeId))].sort();
    if (!ids.length) return Object.freeze({ changed: false, versions: {} });
    const versions = {};
    const affected = new Set();
    for (const id of ids) {
      versions[id] = this.#dependencies.bump(id);
      for (const operation of this.#operations.values()) {
        if (operation.dependencyIds.includes(id)) affected.add(operation);
      }
    }
    let wakeCount = 0;
    for (const operation of affected) {
      if (this.#wakeOperation(operation)) wakeCount += 1;
    }
    this.#notify("dependencies-bumped", {
      dependencyIds: Object.freeze(ids),
      versions: Object.freeze({ ...versions }),
      wakeCount
    });
    return Object.freeze({
      changed: true,
      dependencyIds: Object.freeze(ids),
      versions: Object.freeze({ ...versions }),
      wakeCount
    });
  }

  setTimeDomain(id, timeDomainId) {
    const operation = this.#require(id);
    const domainId = normalizeId(timeDomainId);
    if (!this.#domains.has(domainId)) {
      throw new Error(`Domínio temporal inexistente: ${domainId}.`);
    }
    if (operation.timeDomainId === domainId) return false;
    operation.timeDomainId = domainId;
    this.#wakeOperation(operation);
    this.#notify("time-domain-changed", {
      operationId: operation.id,
      timeDomainId: domainId
    });
    return true;
  }

  readiness(globalTime = this.#domains.now(), phases = null) {
    const global = finiteTime(globalTime);
    const phaseFilter = phases === null
      ? null
      : new Set(phases.map(normalizeId));
    let readyCount = 0;
    let disabledCount = 0;
    let sleepingCount = 0;
    let fixedPointCount = 0;
    let unchangedTimeCount = 0;
    let pendingTimeAdvanceCount = 0;
    let nextWakeGlobalTime = Infinity;

    for (const operation of this.#operations.values()) {
      if (!operation.enabled || (phaseFilter && !phaseFilter.has(operation.phase))) {
        disabledCount += 1;
        continue;
      }
      if (operation.fixedPointVersions !== null) {
        if (!this.#dependencies.changedSince(operation.fixedPointVersions)) {
          fixedPointCount += 1;
          continue;
        }
      }

      const localTime = this.#domains.time(operation.timeDomainId, global);
      if (operation.wakeLocalTime !== null) {
        if (!hasReachedWake(
          localTime,
          operation.wakeLocalTime,
          this.#domains.effectiveRate(operation.timeDomainId)
        )) {
          sleepingCount += 1;
          const wake = this.#domains.globalTimeForLocal(
            operation.timeDomainId,
            operation.wakeLocalTime,
            global
          );
          if (wake < nextWakeGlobalTime) nextWakeGlobalTime = wake;
          continue;
        }
      }

      if (
        operation.lastEvaluationLocalTime !== null &&
        Object.is(localTime, operation.lastEvaluationLocalTime) &&
        !this.#dependencies.changedSince(
          operation.lastEvaluationDependencyVersions
        )
      ) {
        if (this.#domains.effectiveRate(operation.timeDomainId) !== 0) {
          pendingTimeAdvanceCount += 1;
          readyCount += 1;
        } else {
          unchangedTimeCount += 1;
        }
        continue;
      }
      readyCount += 1;
    }

    return Object.freeze({
      globalTime: global,
      readyCount,
      disabledCount,
      sleepingCount,
      fixedPointCount,
      unchangedTimeCount,
      pendingTimeAdvanceCount,
      nextWakeGlobalTime
    });
  }

  evaluate({
    snapshot,
    globalTime = this.#domains.now(),
    phases = null
  } = {}) {
    const plan = this.#plan(globalTime, phases);
    const accumulated = createAccumulator(plan.globalTime);
    for (const phase of plan.phases) {
      for (const entry of phase.operations) {
        const result = entry.operation.evaluate(
          createContext(entry, snapshot, this)
        );
        if (isPromiseLike(result)) {
          throw new TypeError(
            `Operação ${entry.operation.id} retornou Promise em evaluate(); ` +
            "use evaluateParallel()."
          );
        }
        this.#collect(entry, EvolutionResult.normalize(result), accumulated);
      }
    }
    return this.#finish(accumulated, plan);
  }

  async evaluateParallel({
    snapshot,
    globalTime = this.#domains.now(),
    phases = null
  } = {}) {
    const plan = this.#plan(globalTime, phases);
    const accumulated = createAccumulator(plan.globalTime);
    for (const phase of plan.phases) {
      const results = await Promise.all(
        phase.operations.map(async entry => ({
          entry,
          result: EvolutionResult.normalize(
            await entry.operation.evaluate(
              createContext(entry, snapshot, this)
            )
          )
        }))
      );
      for (const { entry, result } of results) {
        this.#collect(entry, result, accumulated);
      }
    }
    return this.#finish(accumulated, plan);
  }

  nextWakeGlobalTime(globalTime = this.#domains.now()) {
    return this.readiness(globalTime).nextWakeGlobalTime;
  }

  describe(id) {
    const operation = this.#require(id);
    return Object.freeze({
      id: operation.id,
      phase: operation.phase,
      order: operation.order,
      timeDomainId: operation.timeDomainId,
      targetId: operation.targetId,
      dependencyIds: operation.dependencyIds,
      enabled: operation.enabled,
      idempotent: operation.idempotent,
      state: operation.fixedPointVersions !== null
        ? "fixed-point"
        : operation.wakeLocalTime !== null
          ? "sleeping"
          : "ready",
      wakeLocalTime: operation.wakeLocalTime,
      lastEvaluationLocalTime: operation.lastEvaluationLocalTime,
      evaluations: operation.evaluations,
      identities: operation.identities,
      changes: operation.changes,
      skips: operation.skips
    });
  }

  status(globalTime = this.#domains.now()) {
    const global = finiteTime(globalTime);
    return Object.freeze({
      version: TEMPORAL_RUNTIME_VERSION,
      globalTime: global,
      readiness: this.readiness(global),
      nextWakeGlobalTime: this.nextWakeGlobalTime(global),
      operationCount: this.#operations.size,
      operations: Object.freeze(
        [...this.#operations.keys()].sort().map(id => this.describe(id))
      ),
      statistics: Object.freeze({ ...this.#statistics }),
      domains: this.#domains.status(global),
      dependencies: this.#dependencies.status()
    });
  }

  #plan(globalTime, phases) {
    const global = finiteTime(globalTime);
    const phaseFilter = phases === null
      ? null
      : new Set(phases.map(normalizeId));
    const grouped = new Map();
    let skipped = 0;

    for (const operation of this.#operations.values()) {
      if (!operation.enabled || (phaseFilter && !phaseFilter.has(operation.phase))) {
        operation.skips += 1;
        skipped += 1;
        continue;
      }
      if (
        operation.fixedPointVersions !== null &&
        !this.#dependencies.changedSince(operation.fixedPointVersions)
      ) {
        operation.skips += 1;
        skipped += 1;
        continue;
      }
      if (
        operation.fixedPointVersions !== null &&
        this.#dependencies.changedSince(operation.fixedPointVersions)
      ) {
        operation.fixedPointVersions = null;
      }

      const localTime = this.#domains.time(operation.timeDomainId, global);
      if (
        operation.wakeLocalTime !== null &&
        !hasReachedWake(
          localTime,
          operation.wakeLocalTime,
          this.#domains.effectiveRate(operation.timeDomainId)
        )
      ) {
        operation.skips += 1;
        skipped += 1;
        continue;
      }
      if (operation.wakeLocalTime !== null) operation.wakeLocalTime = null;

      if (
        operation.lastEvaluationLocalTime !== null &&
        Object.is(localTime, operation.lastEvaluationLocalTime) &&
        !this.#dependencies.changedSince(
          operation.lastEvaluationDependencyVersions
        )
      ) {
        operation.skips += 1;
        skipped += 1;
        continue;
      }

      const list = grouped.get(operation.phase) ?? [];
      list.push(Object.freeze({ operation, localTime, globalTime: global }));
      grouped.set(operation.phase, list);
    }

    const orderedPhases = [...grouped.entries()]
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([phase, operations]) => Object.freeze({
        phase,
        operations: Object.freeze(operations.sort(compareEntries))
      }));

    return Object.freeze({
      globalTime: global,
      phases: Object.freeze(orderedPhases),
      skipped
    });
  }

  #collect(entry, result, accumulated) {
    const operation = entry.operation;
    operation.evaluations += 1;
    operation.lastEvaluationLocalTime = entry.localTime;
    operation.lastEvaluationDependencyVersions = this.#dependencies.snapshot(
      operation.dependencyIds
    );
    this.#statistics.evaluations += 1;
    accumulated.evaluated += 1;

    switch (result.kind) {
      case EvolutionKind.CHANGED:
        operation.changes += 1;
        operation.fixedPointVersions = null;
        operation.wakeLocalTime = null;
        accumulated.changes.push(...result.changes);
        accumulated.events.push(...result.events);
        accumulated.results.push(result);
        this.#statistics.changedResults += 1;
        break;

      case EvolutionKind.IDENTITY:
        operation.identities += 1;
        if (operation.idempotent) {
          operation.fixedPointVersions = this.#dependencies.snapshot(
            operation.dependencyIds
          );
          operation.wakeLocalTime = null;
          this.#statistics.fixedPoints += 1;
        }
        accumulated.results.push(result);
        this.#statistics.identityResults += 1;
        break;

      case EvolutionKind.FIXED_POINT:
        operation.fixedPointVersions = result.dependencyVersions ??
          this.#dependencies.snapshot(operation.dependencyIds);
        operation.wakeLocalTime = null;
        accumulated.results.push(result);
        this.#statistics.fixedPoints += 1;
        break;

      case EvolutionKind.SLEEP_UNTIL:
        operation.fixedPointVersions = null;
        operation.wakeLocalTime = result.wakeLocalTime;
        accumulated.results.push(result);
        this.#statistics.sleeps += 1;
        break;

      default:
        throw new Error(`Resultado temporal desconhecido: ${result.kind}.`);
    }
  }

  #finish(accumulated, plan) {
    this.#statistics.cycles += 1;
    this.#statistics.skipped += plan.skipped;
    const nextWakeGlobalTime = this.nextWakeGlobalTime(plan.globalTime);
    const result = Object.freeze({
      version: TEMPORAL_RUNTIME_VERSION,
      changed: accumulated.changes.length > 0 || accumulated.events.length > 0,
      globalTime: plan.globalTime,
      evaluated: accumulated.evaluated,
      skipped: plan.skipped,
      changes: Object.freeze(accumulated.changes),
      events: Object.freeze(accumulated.events),
      results: Object.freeze(accumulated.results),
      nextWakeGlobalTime
    });
    this.#notify("evaluated", {
      evaluated: result.evaluated,
      changed: result.changed,
      nextWakeGlobalTime
    });
    return result;
  }

  #wakeOperation(operation) {
    const changed = operation.fixedPointVersions !== null ||
      operation.wakeLocalTime !== null ||
      operation.lastEvaluationLocalTime !== null;
    operation.fixedPointVersions = null;
    operation.wakeLocalTime = null;
    operation.lastEvaluationLocalTime = null;
    operation.lastEvaluationDependencyVersions = this.#dependencies.snapshot(
      operation.dependencyIds
    );
    return changed;
  }

  #wakeByDependencyInternal(dependencyId) {
    let count = 0;
    for (const operation of this.#operations.values()) {
      if (!operation.dependencyIds.includes(dependencyId)) continue;
      if (this.#wakeOperation(operation)) count += 1;
    }
    return count;
  }

  #notify(reason, details = {}) {
    if (!this.#listeners.size) return;
    const event = Object.freeze({
      version: TEMPORAL_RUNTIME_VERSION,
      reason: String(reason),
      ...details
    });
    for (const listener of [...this.#listeners]) {
      try {
        listener(event);
      } catch (error) {
        console.error("Temporal runtime listener failed", error);
      }
    }
  }

  #require(id) {
    const key = normalizeId(id);
    const operation = this.#operations.get(key);
    if (!operation) throw new Error(`Operação temporal inexistente: ${key}.`);
    return operation;
  }
}

function createContext(entry, snapshot, runtime) {
  const { operation, localTime, globalTime } = entry;
  return Object.freeze({
    operationId: operation.id,
    phase: operation.phase,
    targetId: operation.targetId,
    timeDomainId: operation.timeDomainId,
    t: localTime,
    globalTime,
    snapshot,
    dependencies: runtime.dependencies,
    domains: runtime.domains,
    result: EvolutionResult
  });
}

function createAccumulator(globalTime) {
  return {
    globalTime,
    evaluated: 0,
    changes: [],
    events: [],
    results: []
  };
}

function compareEntries(a, b) {
  return a.operation.order - b.operation.order ||
    a.operation.sequence - b.operation.sequence ||
    a.operation.id.localeCompare(b.operation.id);
}

function hasReachedWake(localTime, wakeLocalTime, effectiveRate) {
  if (effectiveRate < 0) return localTime <= wakeLocalTime;
  return localTime >= wakeLocalTime;
}

function isPromiseLike(value) {
  return value !== null && typeof value === "object" &&
    typeof value.then === "function";
}

function normalizeId(value) {
  const id = String(value ?? "").trim();
  if (!id) throw new TypeError("Identificador vazio.");
  return id;
}

function finiteOrder(value) {
  const order = Number(value);
  if (!Number.isFinite(order)) throw new RangeError("Ordem deve ser finita.");
  return order;
}

function finiteTime(value) {
  const time = Number(value);
  if (!Number.isFinite(time)) throw new RangeError("Tempo global deve ser finito.");
  return time;
}

function initialStatistics() {
  return {
    cycles: 0,
    evaluations: 0,
    changedResults: 0,
    identityResults: 0,
    fixedPoints: 0,
    sleeps: 0,
    skipped: 0
  };
}
