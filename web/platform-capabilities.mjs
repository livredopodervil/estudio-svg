// Feature detection and backend selection are separate: an available API is not an implemented adapter.
export function detect(host=globalThis){const doc=host.document,nav=host.navigator||{},make=()=>doc?.createElement('canvas');const context=k=>{try{const c=make()?.getContext(k);if(k==='webgl2')c?.getExtension('WEBGL_lose_context')?.loseContext();return !!c;}catch{return false;}};
 let opfs=false,indexedDB=false;try{opfs=typeof nav.storage?.getDirectory==='function';}catch{}try{indexedDB=!!host.indexedDB;}catch{}
 return {dom:!!doc,svg:!!doc?.createElementNS,canvas2d:context('2d'),webgl2:context('webgl2'),webgpu:!!nav.gpu,domMatrix:typeof host.DOMMatrix==='function',pointerEvents:typeof host.PointerEvent==='function',webAudio:!!(host.AudioContext||host.webkitAudioContext),mediaRecorder:typeof host.MediaRecorder==='function',captureStream:typeof host.HTMLCanvasElement?.prototype?.captureStream==='function',webCodecs:typeof host.VideoEncoder==='function'&&typeof host.VideoDecoder==='function',indexedDB,opfs};}
export const adapters=Object.freeze({
 preview:[{id:'dom-svg',requires:['dom','svg'],ready:true},{id:'canvas2d',requires:['canvas2d'],ready:false},{id:'webgl2',requires:['webgl2'],ready:false},{id:'webgpu',requires:['webgpu'],ready:false}],
 export:[{id:'canvas-mediarecorder',requires:['canvas2d','captureStream','mediaRecorder','webAudio'],ready:true},{id:'webcodecs',requires:['webCodecs'],ready:false},{id:'ffmpeg-termux',requires:['server'],ready:true}],
 math:[{id:'affine-js',requires:[],ready:true},{id:'dom-matrix',requires:['domMatrix'],ready:false}],
 input:[{id:'pointer-events',requires:['pointerEvents'],ready:true}],
 audio:[{id:'termux-web-audio',requires:['server','webAudio'],ready:true},{id:'browser-audio',requires:['webAudio'],ready:false}],
 storage:[{id:'termux-files',requires:['server'],ready:true},{id:'indexeddb',requires:['indexedDB'],ready:false},{id:'opfs-projects',requires:['opfs'],ready:false}],
 recordingStorage:[{id:'opfs',requires:['opfs'],ready:true},{id:'memory-short',requires:[],ready:true}]
});
export function resolve(service,caps,{allow=()=>true,registry=adapters}={}){return (registry[service]||[]).find(a=>a.ready&&allow(a)&&a.requires.every(k=>caps[k]))?.id??null;}
export function metrics(limit=180){const buckets=new Map();return {record(name,ms){if(!Number.isFinite(ms)||ms<0)return;let a=buckets.get(name);if(!a)buckets.set(name,a=[]);a.push(ms);if(a.length>limit)a.shift();},snapshot(){return Object.fromEntries([...buckets].map(([k,v])=>{const a=[...v].sort((x,y)=>x-y);return [k,{n:a.length,mean:a.reduce((s,x)=>s+x,0)/a.length,p95:a[Math.ceil(.95*a.length)-1]}];}));}};}
export const codecCandidates=()=>['video/mp4;codecs=avc1.420028,mp4a.40.2','video/mp4','video/webm;codecs=vp8,opus','video/webm;codecs=vp9,opus','video/webm'];
export function codecs(Recorder=globalThis.MediaRecorder){return codecCandidates().filter(x=>{try{return !!Recorder?.isTypeSupported(x);}catch{return false;}});}

// Backends register real factories. Initialization failure advances to the next
// compatible implementation; callers decide which loss of capability is acceptable.
export async function openBackend(service,caps,factories,{registry=adapters,allow=()=>true}={}){const failures=[];for(const a of registry[service]||[]){if(!a.ready||!allow(a)||!a.requires.every(k=>caps[k])||typeof factories[a.id]!=='function')continue;try{return {id:a.id,backend:await factories[a.id](),failures};}catch(e){failures.push({id:a.id,error:String(e?.message||e)});}}return {id:null,backend:null,failures};}
