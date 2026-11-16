import {compile} from './model.mjs';
import {Timeline} from './timeline.mjs';
import {digest,zipStore,MAX_VIDEO,MAX_ZIP} from './page-export.mjs';
const enc=new TextEncoder();
function b64(bytes){let s='';for(let i=0;i<bytes.length;i+=8192)s+=String.fromCharCode(...bytes.subarray(i,i+8192));return btoa(s);}
export async function buildNative({source,template,slug}){
 if(!/^[a-z][a-z0-9-]{2,44}$/.test(slug))throw Error('ID: 3–45 letras/números/hífens');
 if(typeof template!=='string'||template.split('__GIL_TAG__').length!==2||template.split('__GIL_SOURCE__').length!==2)throw Error('Template inválido');
 const doc=compile(source),timeline=new Timeline(doc);timeline.sample(0);timeline.sample(doc.spec.stage.duration);
 const bytes=enc.encode(source),hash=await digest(bytes),tag='gil-'+slug+'-'+hash.slice(0,8),base='projetos/'+slug+'-nativo',ratio=doc.spec.stage.width/doc.spec.stage.height;
 const snippet=`<script type="module" src="/${base}/native.js"></script>\n<${tag} style="width: min(100%, 480px); aspect-ratio: ${ratio}"></${tag}>`;
 const html=`<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Componente GIL</title><script type="module" src="./native.js"></script><style>body{background:#101c29;color:#ecf2f5;font:16px system-ui;max-width:980px;margin:30px auto;padding:16px}section{position:relative;background:linear-gradient(120deg,#17364b,#101c29);padding:24px;min-height:250px;border-radius:16px;overflow:hidden}h1,p{position:relative;z-index:2;max-width:17em} ${tag}{width:min(100%,440px);aspect-ratio:${ratio};position:absolute;right:0;top:0;opacity:.8;pointer-events:none}code{overflow-wrap:anywhere}a{color:#85d1db}</style></head><body><section><h1>Objetos em movimento</h1><p>Componente HTML nativo, sem controles ou iframe.</p><${tag}></${tag}></section><p><a href="./projeto.gil.txt">Fonte GIL</a> · <a href="./component.json">Manifesto</a></p><p>Elemento: <code>${tag}</code>. Adicione o módulo e o elemento à página de destino.</p></body></html>`;
 const files=new Map([['native.js',enc.encode(template.replace('__GIL_TAG__',tag).replace('__GIL_SOURCE__',b64(bytes)))],['index.html',enc.encode(html)],['projeto.gil.txt',bytes],['inserir.txt',enc.encode(snippet+'\n')]]);
 const artifacts=[];for(const [path,b] of files){if(b.length>MAX_VIDEO)throw Error('Componente excede limite de arquivo');artifacts.push({path,role:path==='projeto.gil.txt'?'source':path==='native.js'?'native-runtime':path==='index.html'?'example':'instructions',sha256:await digest(b),bytes:b.length});}
 files.set('component.json',enc.encode(JSON.stringify({schema:1,id:slug+'-nativo',tag,language:'gil-timeline-0.1',source_sha256:hash,autoplay:'silent',transparent:true,artifacts},null,2)+'\n'));
 const descriptors=[];for(const [path,b] of files)descriptors.push({path:base+'/'+path,operation:'add',sha256:await digest(b)});
 const manifest={schema:1,id:`gil-${slug}-native-${hash.slice(0,12)}`,title:'Componente nativo '+slug,version:'0.2.1',notes:'JavaScript nativo para página pública. Sem iframe, áudio ou API administrativa. Revisar fonte e direitos antes de publicar.',files:descriptors};
 const zip=zipStore([['patch.json',enc.encode(JSON.stringify(manifest,null,2))],...[...files].map(([path,b])=>['files/'+base+'/'+path,b])]);if(zip.length>MAX_ZIP)throw Error('Pacote excede 12 MiB');return {zip,name:manifest.id+'.rdpatch.zip',tag,snippet,files};
}
