import assert from 'node:assert/strict';
import {normalizeVoice,resolveVoice,EDGE_PRESETS} from '../rd_voices/controls.mjs';
assert.deepEqual(normalizeVoice('edge:pt-BR-AntonioNeural'),{provider:'edge',voice_id:'pt-BR-AntonioNeural'});
assert.deepEqual(normalizeVoice('piper:pt_BR-faber-medium'),{provider:'piper',voice_id:'pt_BR-faber-medium'});
assert.equal(resolveVoice({project:{voice:'edge:pt-BR-AntonioNeural'},scene:{voice:'edge:pt-BR-FranciscaNeural'}}).voice_id,'pt-BR-FranciscaNeural');
assert.equal(EDGE_PRESETS.alegre.length,3);
console.log('JS contract: 4 verificações aprovadas');
