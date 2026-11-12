// Integração independente, sem alterações na biblioteca SVG-Edit.
// API pública: Editor / setConfig / init / canvas.setSvgString/getSvgString.
const $=id=>document.getElementById(id);
const query=new URLSearchParams(location.search), name=query.get('name'), scene=Number(query.get('scene'));
const ns='http://www.w3.org/2000/svg';
let editor=null,revision=null,loaded=false,dirty=false,working=false;
function info(m,bad=false){$('notice').textContent=m;$('notice').classList.toggle('error',bad);}
function unlock(){loaded=true;$('save').disabled=false;}
const api=async(url,method='GET',obj=null)=>{
 const req=method==='GET'?{}:{method,headers:{'Content-Type':'application/json'},body:JSON.stringify(obj)};
 const r=await fetch(url,req),v=await r.json();if(!r.ok)throw Error(v.error||`HTTP ${r.status}`);return v;
};
function nodeDocument(svg){
 const d=new DOMParser().parseFromString(svg,'image/svg+xml');
 if(d.querySelector('parsererror') || d.documentElement.localName!=='svg')throw Error('SVG inválido');
 return d;
}
function canvasCandidates(){
 // Compatibilidade: SVG-Edit v7 expõe svgCanvas em algumas versões;
 // versões anteriores expunham canvas. Nunca assumir apenas uma propriedade.
 return [editor?.svgCanvas,editor?.canvas,editor?.getCanvas?.(),editor?.svgcanvas].filter(Boolean);
}
function locateSvgDOM(){
 const roots=[document,document.querySelector('#editorHost')].filter(Boolean);
 const seen=new Set();
 for(let i=0;i<roots.length;i++){
  const root=roots[i];if(seen.has(root))continue;seen.add(root);
  for(const selector of ['#svgroot','#svgcontent svg','svg#svgroot','svg[data-type="svgroot"]']){
   const node=root.querySelector?.(selector);
   if(node&&node.localName==='svg')return node;
  }
  for(const element of root.querySelectorAll?.('*')||[]){if(element.shadowRoot)roots.push(element.shadowRoot);}
 }
 return null;
}
async function getText(){
 if(!editor)throw Error('Editor SVG-Edit não inicializado');
 for(const canvas of canvasCandidates()){
  if(typeof canvas.getSvgString==='function'){
   const result=await canvas.getSvgString();
   if(typeof result==='string'&&result.includes('<svg'))return result;
  }
  if(typeof canvas.getContentElem==='function'){
   const node=canvas.getContentElem();
   if(node&&node.localName==='svg')return new XMLSerializer().serializeToString(node);
  }
 }
 const node=locateSvgDOM();
 if(node)return new XMLSerializer().serializeToString(node);
 throw Error('SVG-Edit não disponibilizou o SVG para exportação. Use o Ateliê principal ou o editor de código.');
}
async function setText(svg){
 if(!editor)throw Error('Editor não está pronto');
 nodeDocument(svg);
 if(typeof editor.loadFromString==='function'){
  await editor.loadFromString(svg);return;
 }
 for(const canvas of canvasCandidates()){
  if(typeof canvas.setSvgString==='function'){
   const ok=await canvas.setSvgString(svg,true);
   if(ok===false)throw Error('O SVG-Edit recusou o desenho');
   return;
  }
 }
 throw Error('Esta versão do SVG-Edit não possui API de importação compatível');
}
async function readCurrent(){return await getText();}
async function openScene(){
 if(!name||!Number.isInteger(scene)||scene<1)throw Error('Abra o editor a partir de uma cena do Estúdio');
 const data=await api(`/api/svg/document?name=${encodeURIComponent(name)}&scene=${scene}`);
 await setText(data.svg);revision=data.revision;dirty=false;unlock();
 $('sceneTag').textContent=`${name} · cena ${scene} · ${data.title||'sem título'}`;
 info('Documento carregado. Edite as camadas e salve para atualizar a cena do vídeo.');
}
async function save(){
 if(working)return;working=true;$('save').disabled=true;
 try{
  const svg=await readCurrent();
  const r=await api('/api/svg/document','POST',{name,scene,svg,revision});
  revision=r.revision;dirty=false;localStorage.setItem('estudioSvgVectorSave',JSON.stringify({name,scene,ts:Date.now()}));info('Cena salva. O vídeo e o cache das demais cenas foram preservados.');
 }catch(e){info('Falha ao salvar: '+e.message,true);}
 finally{working=false;$('save').disabled=false;}
}
function download(blob,filename){
 const a=document.createElement('a'),u=URL.createObjectURL(blob);a.href=u;a.download=filename;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(u),3500);
}
async function exportFile(){
 try{
  const format=$('exportType').value,svg=await readCurrent();nodeDocument(svg);
  const base=`${name||'desenho'}_cena_${scene||1}`;
  if(format==='svg'){download(new Blob([svg],{type:'image/svg+xml;charset=utf-8'}),base+'.svg');return;}
  const image=new Image(),u=URL.createObjectURL(new Blob([svg],{type:'image/svg+xml;charset=utf-8'}));
  try{
   await new Promise((resolve,reject)=>{image.onload=resolve;image.onerror=()=>reject(Error('Falha ao rasterizar SVG'));image.src=u;});
   const cv=document.createElement('canvas');cv.width=1280;cv.height=720;const ctx=cv.getContext('2d');
   if(format==='jpeg'){ctx.fillStyle='#ffffff';ctx.fillRect(0,0,cv.width,cv.height);}
   ctx.drawImage(image,0,0,cv.width,cv.height);
   const mime=format==='jpeg'?'image/jpeg':format==='webp'?'image/webp':'image/png';
   const blob=await new Promise(resolve=>cv.toBlob(resolve,mime,.93));if(!blob)throw Error('Formato não suportado neste navegador');
   download(blob,base+'.'+(format==='jpeg'?'jpg':format));
  }finally{URL.revokeObjectURL(u);}
 }catch(e){info('Falha ao exportar: '+e.message,true);}
}
async function loadFile(file){
 if(!file)return;if(file.size>4_000_000)throw Error('SVG máximo: 4 MB');
 const svg=await file.text();nodeDocument(svg);const cleaned=await api('/api/svg/clean','POST',{svg});await setText(cleaned.svg);dirty=true;info('SVG importado. Use Salvar na cena para aplicar.');
}
async function importImage(file){
 if(!file)return;if(file.size>6_000_000)throw Error('Imagem máxima: 6 MB');
 const url=await new Promise((resolve,reject)=>{const fr=new FileReader();fr.onload=()=>resolve(fr.result);fr.onerror=()=>reject(Error('Falha ao ler imagem'));fr.readAsDataURL(file);});
 if(!/^data:image\/(png|jpeg|webp|gif|bmp);base64,/.test(url))throw Error('Formato de imagem inválido');
 const bitmap=new Image();await new Promise((yes,no)=>{bitmap.onload=yes;bitmap.onerror=()=>no(Error('Imagem corrompida'));bitmap.src=url;});
 // Normalize BMP/GIF/WebP/JPEG to a bounded PNG; the Android renderer then uses
 // local asset files, rather than accumulating huge base64 data in every frame.
 const cv=document.createElement('canvas');const scale=Math.min(1,1600/Math.max(bitmap.naturalWidth,bitmap.naturalHeight));
 cv.width=Math.max(1,Math.round(bitmap.naturalWidth*scale));cv.height=Math.max(1,Math.round(bitmap.naturalHeight*scale));
 cv.getContext('2d').drawImage(bitmap,0,0,cv.width,cv.height);
 const localPng=cv.toDataURL('image/png');
 const svg=await readCurrent(),doc=nodeDocument(svg),root=doc.documentElement;
 const g=doc.createElementNS(ns,'g');g.setAttribute('class','layer');g.setAttribute('id','imagem_'+Date.now());
 const title=doc.createElementNS(ns,'title');title.textContent='Imagem '+file.name;g.appendChild(title);
 const img=doc.createElementNS(ns,'image');const k=Math.min(900/bitmap.naturalWidth,550/bitmap.naturalHeight,1);
 const w=Math.max(1,Math.round(bitmap.naturalWidth*k)),h=Math.max(1,Math.round(bitmap.naturalHeight*k));
 img.setAttribute('x',String((1280-w)/2));img.setAttribute('y',String((720-h)/2));img.setAttribute('width',String(w));img.setAttribute('height',String(h));img.setAttribute('href',localPng);
 g.appendChild(img);root.appendChild(g);
 await setText(new XMLSerializer().serializeToString(doc));dirty=true;info('Imagem adicionada em camada própria. Salve a cena para armazenar a mídia no Termux.');
}
async function main(){
 $('save').onclick=save;$('exportFile').onclick=exportFile;
 $('importSvg').onclick=()=>$('svgUpload').click();$('importImage').onclick=()=>$('imageUpload').click();
 $('svgUpload').onchange=async e=>{try{await loadFile(e.target.files[0]);}catch(e){info(e.message,true);}e.target.value='';};
 $('imageUpload').onchange=async e=>{try{await importImage(e.target.files[0]);}catch(e){info(e.message,true);}e.target.value='';};
 $('back').onclick=()=>{if(dirty&&!confirm('Existem alterações não salvas. Voltar mesmo assim?'))return;location.href='/';};
 window.addEventListener('beforeunload',e=>{if(dirty){e.preventDefault();e.returnValue='';}});
 document.addEventListener('keydown',e=>{if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='s'){e.preventDefault();save();}});
 if(!name||!scene)throw Error('Parâmetros da cena ausentes');
 // SVG-Edit 7 ships a precompiled ESM distribution. No Node.js runs on Android.
 let Editor;
 try{({default:Editor}=await import('/vendor/svgedit/editor/Editor.js'));}
 catch(e){throw Error('SVG-Edit não está instalado. Execute bash instalar_svg_edit.sh no Termux. Detalhes: '+e.message);}
 editor=new Editor($('editorHost'));
 editor.setConfig({allowInitialUserOverride:true,extensions:[],noDefaultExtensions:false,userExtensions:[]});
 await editor.init();
 for(let i=0;i<45;i++){
   if(canvasCandidates().some(x=>typeof x.getSvgString==='function'&&typeof x.setSvgString==='function')||editor.loadFromString)break;
   await new Promise(done=>setTimeout(done,160));
 }
 await openScene();
 $('editorHost').addEventListener('pointerup',()=>{if(loaded)dirty=true;},{passive:true});
 $('editorHost').addEventListener('keyup',()=>{if(loaded)dirty=true;});
}
main().catch(e=>{console.error(e);info(e.message,true);});
