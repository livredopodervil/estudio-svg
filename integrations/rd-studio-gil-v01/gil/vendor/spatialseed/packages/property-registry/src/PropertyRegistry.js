export class PropertyRegistry {
  static apiVersion = "property-registry-v1";
  #descriptors = new Map();

  register(input) {
    const descriptor = normalizeDescriptor(input);

    if (this.#descriptors.has(descriptor.id)) {
      throw new Error(`Propriedade já registrada: ${descriptor.id}.`);
    }

    this.#descriptors.set(descriptor.id, descriptor);
    return this;
  }

  get(id) {
    return this.#descriptors.get(String(id)) ?? null;
  }

  require(id) {
    const descriptor = this.get(id);

    if (!descriptor) {
      throw new Error(`Propriedade desconhecida: ${id}.`);
    }

    return descriptor;
  }

  list() {
    return [...this.#descriptors.values()];
  }

  describe() {
    return Object.freeze({
      apiVersion: PropertyRegistry.apiVersion,
      properties: Object.freeze(this.list().map(descriptor =>
        Object.freeze({
          id: descriptor.id,
          label: descriptor.label,
          group: descriptor.group,
          scope: descriptor.scope,
          valueType: descriptor.valueType,
          nullable: descriptor.nullable,
          editableMany: descriptor.editableMany,
          procedural: descriptor.procedural,
          writable: descriptor.writable,
          values: descriptor.values,
          minimum: descriptor.minimum,
          maximum: descriptor.maximum,
          step: descriptor.step,
          unit: descriptor.unit,
          integer: descriptor.integer
        })
      ))
    });
  }

  inspect(objects, context = {}) {
    const members = Array.isArray(objects) ? objects : [];
    const properties = {};

    for (const descriptor of this.#descriptors.values()) {
      if (
        !members.length ||
        members.some(object => !descriptor.supports(object, context))
      ) {
        properties[descriptor.id] = Object.freeze({
          id: descriptor.id,
          status: "unsupported",
          editable: false,
          value: null
        });
        continue;
      }

      const value = clonePropertyValue(
        descriptor.read(members[0], context)
      );
      let uniform = true;

      for (let index = 1; index < members.length; index += 1) {
        if (!equalValue(
          descriptor.read(members[index], context),
          value
        )) {
          uniform = false;
          break;
        }
      }

      properties[descriptor.id] = Object.freeze({
        id: descriptor.id,
        status: uniform ? "uniform" : "mixed",
        editable: descriptor.writable && (
          members.length === 1 || descriptor.editableMany
        ),
        value: uniform ? value : null
      });
    }

    return Object.freeze(properties);
  }
}

function normalizeDescriptor(input) {
  if (!input || typeof input !== "object") {
    throw new TypeError("Descritor de propriedade inválido.");
  }

  const id = String(input.id ?? "").trim();

  if (!id || typeof input.read !== "function" || typeof input.normalize !== "function") {
    throw new TypeError(
      "Descritor exige id, read e normalize."
    );
  }

  return Object.freeze({
    id,
    label: String(input.label ?? id),
    group: String(input.group ?? "general"),
    scope: String(input.scope ?? "object"),
    path: Object.freeze([...(input.path ?? [])]),
    valueType: String(input.valueType ?? "unknown"),
    nullable: Boolean(input.nullable),
    editableMany: Boolean(input.editableMany),
    procedural: Boolean(input.procedural),
    writable: input.writable !== false,
    values: input.values
      ? Object.freeze([...input.values])
      : null,
    minimum: finiteMetadata(input.minimum),
    maximum: finiteMetadata(input.maximum),
    step: positiveMetadata(input.step),
    unit: input.unit == null ? null : String(input.unit),
    integer: Boolean(input.integer),
    normalize: input.normalize,
    write: typeof input.write === "function"
      ? input.write
      : null,
    read: input.read,
    supports: typeof input.supports === "function"
      ? input.supports
      : () => true
  });
}

function finiteMetadata(value) {
  if (value === undefined || value === null) return null;
  const number = Number(value);
  if (!Number.isFinite(number)) {
    throw new TypeError(`Metadado numérico inválido: ${value}.`);
  }
  return number;
}

function positiveMetadata(value) {
  const number = finiteMetadata(value);
  if (number === null) return null;
  if (!(number > 0)) throw new RangeError("O passo deve ser positivo.");
  return number;
}

function equalValue(left, right) {
  if (Object.is(left, right)) return true;
  if (
    left === null || right === null ||
    typeof left !== "object" || typeof right !== "object"
  ) {
    return false;
  }
  return JSON.stringify(left) === JSON.stringify(right);
}

function clonePropertyValue(value) {
  return value === null || typeof value !== "object"
    ? value
    : structuredClone(value);
}
