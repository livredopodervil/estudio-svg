import {
  AFFINE_AST_VERSION,
  AFFINE_LANGUAGE_ID,
  AFFINE_LANGUAGE_VERSION,
  canonicalizeAffineOperations,
  lowerCanonicalAffineAst
} from "./AffineAst.js?build=20260715-0021d";

const FUNCTION_NAMES = Object.freeze(new Set([
  "sin", "cos", "tan",
  "sind", "cosd", "tand",
  "asin", "acos", "atan", "atan2",
  "sqrt", "cbrt", "abs", "exp",
  "log", "log10", "min", "max",
  "floor", "ceil", "round", "trunc",
  "sign", "hypot", "clamp", "mix", "step",
  "smoothstep", "smootherstep", "fract"
]));

export const NativeAffineMathBackend = Object.freeze({
  id: "native-number-v1",

  literal(value) {
    return finite(value);
  },

  variable(value, name) {
    if (typeof value !== "number") {
      throw new TypeError(
        `Variável não escalar usada como número: ${name}.`
      );
    }

    return finite(value);
  },

  unary(operator, value) {
    if (operator === "+") return value;
    if (operator === "-") return -value;
    throw new Error(`Operador unário desconhecido: ${operator}.`);
  },

  binary(operator, left, right) {
    if (operator === "+") return left + right;
    if (operator === "-") return left - right;
    if (operator === "*") return left * right;
    if (operator === "/") return left / right;
    if (operator === "%") return left % right;
    if (operator === "**") return left ** right;

    throw new Error(`Operador binário desconhecido: ${operator}.`);
  },

  call(name, args) {
    const operation = NATIVE_FUNCTIONS[name];

    if (!operation) {
      throw new Error(`Função desconhecida: ${name}.`);
    }

    return operation(...args);
  },

  toNumber(value) {
    return finite(value);
  }
});

export function compileAffineProgram(operations = [], options = {}) {
  if (!Array.isArray(operations)) {
    throw new TypeError("operations deve ser um array.");
  }

  const ast = canonicalizeAffineOperations(operations, {
    mode: options.mode ?? "indexed",
    translationSpace: options.translationSpace ?? "world",
    sourceLanguage: options.sourceLanguage ?? AFFINE_LANGUAGE_ID,
    sourceLanguageVersion:
      options.sourceLanguageVersion ?? AFFINE_LANGUAGE_VERSION
  });

  return compileCanonicalAffineAst(ast);
}

export function compileCanonicalAffineAst(ast) {
  if (ast?.astVersion !== AFFINE_AST_VERSION) {
    throw new Error(
      `AST afim incompatível: ${ast?.astVersion ?? "ausente"}.`
    );
  }

  const lowered = lowerCanonicalAffineAst(ast);
  const operations = Object.freeze(
    lowered.operations.map(operation =>
      deepFreeze(compileOperation(operation))
    )
  );

  return Object.freeze({
    type: "affine-program",
    syntax: lowered.source.languageVersion,
    astVersion: ast.astVersion,
    astHash: ast.hash,
    ast,
    semantics: ast.semantics,
    source: lowered.source,
    operations
  });
}

export function compileAffineExpression(expression) {
  return compileValue(expression);
}

export function evaluateAffineProgram(
  program,
  context = {},
  { backend = NativeAffineMathBackend } = {}
) {
  validateBackend(backend);

  const compiled =
    program?.type === "affine-program"
      ? program
      : program?.astVersion === AFFINE_AST_VERSION
        ? compileCanonicalAffineAst(program)
        : compileAffineProgram(program);

  return compiled.operations.map(operation => {
    const type = operation.type;

    if (["pivot", "move", "rotate", "scale"].includes(type)) {
      return {
        type,
        value: evaluateAffineVector(
          operation.value,
          context,
          type,
          backend
        )
      };
    }

    if (type === "matrix") {
      return {
        type,
        value: operation.value.map(value =>
          evaluateCompiled(value, context, backend)
        )
      };
    }

    throw new Error(
      `Operação afim desconhecida: ${type || "(vazia)"}.`
    );
  });
}

export function evaluateAffineExpression(
  expression,
  context = {},
  { backend = NativeAffineMathBackend } = {}
) {
  return evaluateCompiledAffineExpression(
    compileValue(expression),
    context,
    { backend }
  );
}

export function evaluateCompiledAffineExpression(
  compiled,
  context = {},
  { backend = NativeAffineMathBackend } = {}
) {
  validateBackend(backend);

  const evaluationContext = createAffineEvaluationContext({
    variables: context,
    index: context.i ?? 0,
    count: context.count ?? 1,
    time: context.t ?? context.time ?? 0,
    deltaTime: context.dt ?? context.deltaTime ?? 0,
    normalizedProgress: Object.hasOwn(context, "u")
      ? context.u
      : undefined,
    transform: {
      position: context.position ?? [
        context.x ?? 0,
        context.y ?? 0,
        context.z ?? 0
      ],
      rotation: context.rotation ?? [0, 0, 0, 1],
      scale: context.scale ?? [
        context.sx ?? 1,
        context.sy ?? 1,
        context.sz ?? 1
      ]
    }
  });

  return backend.toNumber(
    evaluateCompiled(
      compiled,
      evaluationContext,
      backend
    )
  );
}

export function evaluateAffineVector(
  value,
  context,
  label,
  backend = NativeAffineMathBackend
) {
  validateBackend(backend);

  if (!Array.isArray(value) || value.length !== 3) {
    throw new TypeError(`${label} exige 3 valores.`);
  }

  return value.map(item =>
    backend.toNumber(
      evaluateCompiled(item, context, backend)
    )
  );
}

export function createAffineEvaluationContext({
  index = 0,
  count = 1,
  time = 0,
  deltaTime = 0,
  normalizedProgress = undefined,
  transform = {},
  variables = {}
} = {}) {
  const position = vector3(
    transform.position ?? [0, 0, 0],
    "position"
  );
  const scale = vector3(
    transform.scale ?? [1, 1, 1],
    "scale"
  );
  const rotation =
    Array.isArray(transform.rotation) &&
    transform.rotation.length === 4
      ? transform.rotation.map(finite)
      : [0, 0, 0, 1];

  const safeCount = Math.max(1, Number(count) || 1);
  const safeIndex = Number(index) || 0;
  const progress = normalizedProgress === undefined
    ? (
        safeCount <= 1
          ? 0
          : (safeIndex - 1) / (safeCount - 1)
      )
    : finite(normalizedProgress);

  return Object.freeze({
    ...sanitizeVariables(variables),
    i: safeIndex,
    index: safeIndex,
    count: safeCount,
    u: progress,
    t: finite(time),
    time: finite(time),
    dt: finite(deltaTime),
    deltaTime: finite(deltaTime),
    x: position[0],
    y: position[1],
    z: position[2],
    sx: scale[0],
    sy: scale[1],
    sz: scale[2],
    position: Object.freeze([...position]),
    scale: Object.freeze([...scale]),
    rotation: Object.freeze([...rotation]),
    pi: Math.PI,
    e: Math.E,
    tau: Math.PI * 2,
    phi: (1 + Math.sqrt(5)) / 2,
    /*
     * Operações rotate do runtime recebem graus. Estas constantes convertem
     * unidades explícitas para esse formato sem mudar a trigonometria,
     * que permanece convencionalmente em radianos.
     */
    deg: 1,
    rad: 180 / Math.PI,
    turn: 360
  });
}

function compileOperation(operation = {}) {
  const type = String(operation?.type ?? "").toLowerCase();

  if (["move", "rotate", "scale", "pivot"].includes(type)) {
    return {
      type,
      value: compileVector(operation.value, type)
    };
  }

  if (type === "matrix") {
    if (!Array.isArray(operation.value) ||
        operation.value.length !== 16) {
      throw new TypeError("matrix exige 16 valores.");
    }

    return {
      type,
      value: operation.value.map(compileValue)
    };
  }

  throw new Error(
    `Operação afim desconhecida: ${type || "(vazia)"}.`
  );
}

function compileVector(value, label) {
  if (!Array.isArray(value) || value.length !== 3) {
    throw new TypeError(`${label} exige 3 valores.`);
  }

  return value.map(compileValue);
}

function compileValue(value) {
  if (typeof value === "number") {
    return deepFreeze({
      type: "literal",
      value: finite(value),
      source: String(value),
      normalized: String(value)
    });
  }

  if (typeof value !== "string") {
    const converted = Number(value);

    if (Number.isFinite(converted)) {
      return deepFreeze({
        type: "literal",
        value: converted,
        source: String(value),
        normalized: String(converted)
      });
    }

    throw new TypeError(
      `Expressão inválida: ${String(value)}.`
    );
  }

  const source = String(value).trim();
  const normalized = normalizeExpressionSource(source);
  const numeric = Number(normalized);

  if (Number.isFinite(numeric)) {
    return deepFreeze({
      type: "literal",
      value: numeric,
      source,
      normalized: String(numeric)
    });
  }

  const parser = new ExpressionParser(normalized);
  const ast = parser.parse();

  return deepFreeze({
    type: "expression",
    source,
    normalized,
    ast
  });
}

function evaluateCompiled(compiled, context, backend) {
  if (typeof compiled === "number") {
    return backend.literal(compiled);
  }

  if (typeof compiled === "string") {
    return evaluateCompiled(
      compileValue(compiled),
      context,
      backend
    );
  }

  if (compiled?.type === "literal") {
    return backend.literal(compiled.value);
  }

  if (compiled?.type === "expression") {
    return evaluateAst(compiled.ast, context, backend);
  }

  throw new TypeError("Valor compilado inválido.");
}

function normalizeExpressionSource(source) {
  const explicitUnits = String(source)
    .trim()
    .replace(
      /(\d|\)|[A-Za-z_][A-Za-z0-9_]*)\s+(deg|rad|turn)\b/g,
      "$1*$2"
    )
    .replace(
      /((?:\d+(?:\.\d*)?|\.\d+)|\))d\b/g,
      "$1*deg"
    )
    .replace(
      /((?:\d+(?:\.\d*)?|\.\d+)|\))r\b/g,
      "$1*rad"
    )
    .replace(
      /((?:\d+(?:\.\d*)?|\.\d+)|\))turn\b/g,
      "$1*turn"
    );

  /*
   * ** é a forma canônica, como Python/SymPy.
   * ^ permanece como alias temporário e é normalizado imediatamente.
   */
  return explicitUnits.replace(
    /(?<!\*)\^(?!\*)/g,
    "**"
  );
}

class ExpressionParser {
  constructor(source) {
    this.tokens = tokenize(source);
    this.index = 0;
  }

  parse() {
    const expression = this.parseExpression();

    if (!this.at("eof")) {
      throw new Error(
        `Token inesperado: ${this.peek().value}.`
      );
    }

    return deepFreeze(expression);
  }

  parseExpression() {
    return this.parseAdditive();
  }

  parseAdditive() {
    let node = this.parseMultiplicative();

    while (this.at("+") || this.at("-")) {
      node = {
        type: "binary",
        operator: this.consume().type,
        left: node,
        right: this.parseMultiplicative()
      };
    }

    return node;
  }

  parseMultiplicative() {
    let node = this.parseUnary();

    while (
      this.at("*") ||
      this.at("/") ||
      this.at("%")
    ) {
      node = {
        type: "binary",
        operator: this.consume().type,
        left: node,
        right: this.parseUnary()
      };
    }

    return node;
  }

  /*
   * Precedência compatível com Python:
   * -2 ** 2 = -(2 ** 2)
   * 2 ** -2 = 2 ** (-2)
   */
  parseUnary() {
    if (this.at("+") || this.at("-")) {
      return {
        type: "unary",
        operator: this.consume().type,
        value: this.parseUnary()
      };
    }

    return this.parsePower();
  }

  parsePower() {
    const left = this.parsePrimary();

    if (!this.at("**")) return left;

    this.consume("**");

    return {
      type: "binary",
      operator: "**",
      left,
      right: this.parseUnary()
    };
  }

  parsePrimary() {
    if (this.at("number")) {
      return {
        type: "literal",
        value: Number(this.consume().value)
      };
    }

    if (this.at("identifier")) {
      const name = this.consume().value;

      if (!this.at("(")) {
        return { type: "variable", name };
      }

      if (!FUNCTION_NAMES.has(name)) {
        throw new Error(`Função desconhecida: ${name}.`);
      }

      this.consume("(");
      const args = [];

      if (!this.at(")")) {
        do {
          args.push(this.parseExpression());

          if (!this.at(",")) break;
          this.consume(",");
        } while (true);
      }

      this.consume(")");

      return {
        type: "call",
        name,
        args
      };
    }

    if (this.at("(")) {
      this.consume("(");
      const expression = this.parseExpression();
      this.consume(")");
      return expression;
    }

    throw new Error(
      `Expressão esperada antes de ${this.peek().value}.`
    );
  }

  at(type) {
    return this.peek().type === type;
  }

  peek() {
    return this.tokens[this.index];
  }

  consume(expected = null) {
    const token = this.peek();

    if (expected && token.type !== expected) {
      throw new Error(
        `Esperado ${expected}, recebido ${token.value}.`
      );
    }

    this.index += 1;
    return token;
  }
}

function tokenize(source) {
  const tokens = [];
  let index = 0;

  while (index < source.length) {
    const character = source[index];

    if (/\s/.test(character)) {
      index += 1;
      continue;
    }

    if (source.startsWith("**", index)) {
      tokens.push({ type: "**", value: "**" });
      index += 2;
      continue;
    }

    if (/[0-9.]/.test(character)) {
      const match = source
        .slice(index)
        .match(
          /^(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?/
        );

      if (!match) {
        throw new Error(
          `Número inválido próximo de ${source.slice(index)}.`
        );
      }

      tokens.push({
        type: "number",
        value: match[0]
      });
      index += match[0].length;
      continue;
    }

    if (/[A-Za-z_]/.test(character)) {
      const match = source
        .slice(index)
        .match(/^[A-Za-z_][A-Za-z0-9_]*/);

      tokens.push({
        type: "identifier",
        value: match[0]
      });
      index += match[0].length;
      continue;
    }

    if ("+-*/%(),".includes(character)) {
      tokens.push({
        type: character,
        value: character
      });
      index += 1;
      continue;
    }

    throw new Error(
      `Caractere inválido na expressão: ${character}.`
    );
  }

  tokens.push({ type: "eof", value: "(fim)" });
  return tokens;
}

function evaluateAst(node, context, backend) {
  if (node.type === "literal") {
    return backend.literal(node.value);
  }

  if (node.type === "variable") {
    return backend.variable(
      resolveVariable(context, node.name),
      node.name
    );
  }

  if (node.type === "unary") {
    return backend.unary(
      node.operator,
      evaluateAst(node.value, context, backend)
    );
  }

  if (node.type === "binary") {
    return backend.binary(
      node.operator,
      evaluateAst(node.left, context, backend),
      evaluateAst(node.right, context, backend)
    );
  }

  if (node.type === "call") {
    return backend.call(
      node.name,
      node.args.map(argument =>
        evaluateAst(argument, context, backend)
      )
    );
  }

  throw new Error(`Nó de expressão inválido: ${node.type}.`);
}

function resolveVariable(context, name) {
  if (
    !Object.prototype.hasOwnProperty.call(context, name)
  ) {
    throw new Error(`Variável desconhecida: ${name}.`);
  }

  return context[name];
}

function validateBackend(backend) {
  for (const method of [
    "literal",
    "variable",
    "unary",
    "binary",
    "call",
    "toNumber"
  ]) {
    if (typeof backend?.[method] !== "function") {
      throw new TypeError(
        `Backend matemático sem método ${method}().`
      );
    }
  }
}

function sanitizeVariables(variables) {
  const result = {};

  for (const [key, value] of Object.entries(
    variables ?? {}
  )) {
    if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(key)) {
      throw new Error(`Nome de variável inválido: ${key}.`);
    }

    if (
      typeof value !== "number" &&
      !Array.isArray(value)
    ) {
      throw new TypeError(
        `Variável deve ser número ou vetor: ${key}.`
      );
    }

    result[key] = Array.isArray(value)
      ? Object.freeze(value.map(finite))
      : finite(value);
  }

  return result;
}

function vector3(value, label) {
  if (!Array.isArray(value) || value.length !== 3) {
    throw new TypeError(`${label} exige 3 valores.`);
  }

  return value.map(finite);
}

function finite(value) {
  const number = Number(value);

  if (!Number.isFinite(number)) {
    throw new TypeError(
      `Valor numérico inválido: ${value}.`
    );
  }

  return number;
}

const NATIVE_FUNCTIONS = Object.freeze({
  sin: Math.sin,
  cos: Math.cos,
  tan: Math.tan,
  sind: value => Math.sin(value * Math.PI / 180),
  cosd: value => Math.cos(value * Math.PI / 180),
  tand: value => Math.tan(value * Math.PI / 180),
  asin: Math.asin,
  acos: Math.acos,
  atan: Math.atan,
  atan2: Math.atan2,
  sqrt: Math.sqrt,
  cbrt: Math.cbrt,
  abs: Math.abs,
  exp: Math.exp,
  log: Math.log,
  log10: Math.log10,
  min: Math.min,
  max: Math.max,
  floor: Math.floor,
  ceil: Math.ceil,
  round: Math.round,
  trunc: Math.trunc,
  sign: Math.sign,
  hypot: Math.hypot,
  clamp: (value, minimum, maximum) =>
    Math.min(maximum, Math.max(minimum, value)),
  mix: (left, right, amount) => left + (right - left) * amount,
  step: (edge, value) => value < edge ? 0 : 1,
  smoothstep: (edge0, edge1, value) => {
    if (edge0 === edge1) return value < edge0 ? 0 : 1;
    const t = Math.min(1, Math.max(0, (value - edge0) / (edge1 - edge0)));
    return t * t * (3 - 2 * t);
  },
  smootherstep: (edge0, edge1, value) => {
    if (edge0 === edge1) return value < edge0 ? 0 : 1;
    const t = Math.min(1, Math.max(0, (value - edge0) / (edge1 - edge0)));
    return t * t * t * (t * (t * 6 - 15) + 10);
  },
  fract: value => value - Math.floor(value)
});

function deepFreeze(value) {
  if (!value || typeof value !== "object") {
    return value;
  }

  Object.freeze(value);

  for (const child of Object.values(value)) {
    deepFreeze(child);
  }

  return value;
}

export {
  AFFINE_AST_VERSION,
  AFFINE_LANGUAGE_ID,
  AFFINE_LANGUAGE_VERSION,
  canonicalizeAffineOperations,
  lowerCanonicalAffineAst
} from "./AffineAst.js";
