// Adaptador: nenhuma implementação matemática ou temporal duplicada.
export {compileAffineExpression, evaluateCompiledAffineExpression, compileAffineProgram, evaluateAffineProgram, createAffineEvaluationContext} from '../vendor/spatialseed/packages/selection-operations/src/AffineProgram.js';
export {composeTransform, eulerQuaternion, multiplyMatrices, invertAffineMatrix, identityMatrix} from '../vendor/spatialseed/packages/math-affine/src/Matrix4.js';
export {TemporalRuntime} from '../vendor/spatialseed/packages/temporal-runtime/src/TemporalRuntime.js';
export {AnalyticTimeDomains} from '../vendor/spatialseed/packages/temporal-runtime/src/AnalyticTimeDomains.js';
export {createOccurrenceRef, childOccurrenceRef, occurrenceRefKey} from '../vendor/spatialseed/packages/occurrence-contracts/src/OccurrenceRef.js';
export {PropertyRegistry} from '../vendor/spatialseed/packages/property-registry/src/PropertyRegistry.js';
export {RuntimeCapabilities} from '../vendor/spatialseed/packages/runtime-api/src/RuntimeCapabilities.js';
