export const AFFINE_AST_VERSION = "spatialseed-affine-ast-v1";
export const AFFINE_LANGUAGE_ID = "spatialseed-math";
export const AFFINE_LANGUAGE_VERSION = "spatialseed-math-v1";

const OPERATION_IDS = Object.freeze({
  move: "transform.translation.delta",
  rotate: "transform.rotation.delta",
  scale: "transform.scale.factor-at",
  pivot: "transform.pivot.set",
  matrix: "transform.matrix.compose"
});

const LEGACY_TYPES = Object.freeze(
  Object.fromEntries(
    Object.entries(OPERATION_IDS).map(([type, id]) => [id, type])
  )
);

export function canonicalizeAffineOperations(operations, {
  mode = "indexed",
  translationSpace = "world",
  sourceLanguage = AFFINE_LANGUAGE_ID,
  sourceLanguageVersion = AFFINE_LANGUAGE_VERSION
} = {}) {
  if (!Array.isArray(operations)) {
    throw new TypeError("operations deve ser um array.");
  }

  if (!["indexed", "recursive"].includes(mode)) {
    throw new Error(`Modo afim desconhecido: ${mode}.`);
  }

  if (!["world", "local"].includes(translationSpace)) {
    throw new Error(
      `Espaço de translação desconhecido: ${translationSpace}.`
    );
  }

  const nodes = operations.map((operation, index) => {
    const legacyType = String(operation?.type ?? "").toLowerCase();
    const operationId = OPERATION_IDS[legacyType];

    if (!operationId) {
      throw new Error(
        `Operação afim desconhecida: ${legacyType || "(vazia)"}.`
      );
    }

    return deepFreeze({
      nodeType: "affine.operation",
      operationId,
      ordinal: index,
      arguments: structuredClone(operation.value),
      metadata: {
        sourceKeyword: legacyType
      }
    });
  });

  const tree = {
    nodeType: "affine.program",
    astVersion: AFFINE_AST_VERSION,
    source: {
      languageId: sourceLanguage,
      languageVersion: sourceLanguageVersion
    },
    semantics: {
      mode,
      translationSpace,
      seedResolution: "once-at-start",
      pivotResolution: "once-at-start",
      scaleSemantics:
        mode === "indexed" ? "factor-at-index" : "recursive-factor"
    },
    body: nodes
  };

  const canonical = stableStringify(tree);
  return deepFreeze({
    ...tree,
    hash: `fnv1a64:${fnv1a64(canonical)}`
  });
}

export function lowerCanonicalAffineAst(ast) {
  if (ast?.astVersion !== AFFINE_AST_VERSION) {
    throw new Error(
      `AST afim incompatível: ${ast?.astVersion ?? "ausente"}.`
    );
  }

  return deepFreeze({
    source: {
      languageId: ast.source?.languageId ?? AFFINE_LANGUAGE_ID,
      languageVersion:
        ast.source?.languageVersion ?? AFFINE_LANGUAGE_VERSION
    },
    operations: ast.body.map(node => {
      const type = LEGACY_TYPES[node.operationId];
      if (!type) {
        throw new Error(
          `ID semântico desconhecido: ${node.operationId}.`
        );
      }
      return { type, value: structuredClone(node.arguments) };
    })
  });
}

export function isCanonicalAffineAst(value) {
  return value?.astVersion === AFFINE_AST_VERSION &&
    value?.nodeType === "affine.program";
}

function stableStringify(value) {
  if (Array.isArray(value)) {
    return `[${value.map(stableStringify).join(",")}]`;
  }
  if (value && typeof value === "object") {
    return `{${Object.keys(value).sort().map(key =>
      `${JSON.stringify(key)}:${stableStringify(value[key])}`
    ).join(",")}}`;
  }
  return JSON.stringify(value);
}

function fnv1a64(text) {
  let hash = 0xcbf29ce484222325n;
  const prime = 0x100000001b3n;
  for (const byte of new TextEncoder().encode(text)) {
    hash ^= BigInt(byte);
    hash = BigInt.asUintN(64, hash * prime);
  }
  return hash.toString(16).padStart(16, "0");
}

function deepFreeze(value) {
  if (!value || typeof value !== "object") return value;
  Object.freeze(value);
  for (const child of Object.values(value)) deepFreeze(child);
  return value;
}
