import assert from 'node:assert/strict';
import {parseEdgeCatalogue,filterVoiceOptions,readEdgeCatalogue,resetEdgeCatalogue} from '../web/rd-audio-voice-picker.mjs';
const rows=[{provider:'edge',voice_id:'pt-BR-AntonioNeural',locale:'pt-BR',name:'Antonio'},
            {provider:'edge',voice_id:'en-US-JennyNeural',locale:'en-US',name:'Jenny'}];
const voices=parseEdgeCatalogue({count:rows.length,voices:rows});
assert.equal(voices[0].id,'edge:pt-BR-AntonioNeural');
assert.equal(filterVoiceOptions(voices,'pt-BR').length,3); // both Piper voices + one Edge
assert.equal(filterVoiceOptions(voices,'Jenny').length,3);
assert.throws(()=>parseEdgeCatalogue({count:2,voices:[rows[0],rows[0]]}),/repetido/);
resetEdgeCatalogue();
let requests=0;
const fetcher=async()=>{requests++;return {count:2,voices:rows}};
await Promise.all([readEdgeCatalogue(fetcher),readEdgeCatalogue(fetcher)]);
assert.equal(requests,1);
console.log('RD-Audio voice catalogue/picker: 5 verificações aprovadas');
