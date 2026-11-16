export class RuntimeCapabilities {
  #providers = new Map();

  register(id, describe) {
    const key = String(id ?? "").trim();

    if (!key) {
      throw new TypeError("Capability id must be a non-empty string.");
    }

    if (this.#providers.has(key)) {
      throw new Error(`Capability already registered: ${key}`);
    }

    const provider =
      typeof describe === "function"
        ? describe
        : () => structuredClone(describe);

    this.#providers.set(key, provider);
    return this;
  }

  describe() {
    return Object.freeze(
      Object.fromEntries(
        [...this.#providers].map(([id, provider]) => [
          id,
          structuredClone(provider())
        ])
      )
    );
  }
}
