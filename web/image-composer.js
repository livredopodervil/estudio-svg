/* Editor não destrutivo de atlas de imagens e enquadramento por cena.
   Crop e geometria normalizados são persistidos no JSON do projeto. */
(()=>{'use strict';
const clamp=(x,min=0,max=1)=>Math.max(min,Math.min(max,Number(x)||0));
const ui=`<dialog id="imageComposer" aria-labelledby="icTitle">
 <header class="icTop"><div><strong id="icTitle">Imagem da cena · recorte e composição</strong><small>Recorte uma foto da prancha, arraste e redimensione no quadro</small></div><button id="icClose" type="button">Fechar</button></header>
 <div class="icContent">
  <section><h3>1. Selecionar região da imagem</h3><p>Arraste sobre a imagem para marcar a foto desejada. Pode reutilizar a mesma prancha em outras cenas.</p>
   <div class="icCanvasWrap"><canvas id="icSource" aria-label="Escolher recorte da imagem"></canvas></div>
   <div class="icButtons"><button id="icAll">Imagem inteira</button><button id="icCenter">Centro 80%</button></div><p class="icHint">Arraste as arestas, os cantos ou o interior do retângulo. Fora dele, arraste para criar outro recorte.</p><div class="icButtons"><input id="icImportFile" type="file" accept="image/png,image/jpeg,image/webp" aria-label="Importar prancha"><input id="icFileName" type="text" maxlength="75" placeholder="Nome da prancha" aria-label="Nome da prancha"></div><div class="icButtons"><button id="icImport">Importar prancha</button><button id="icRename">Criar nome para imagem atual</button></div>
  </section>
  <section><h3>2. Posição no vídeo</h3><p>Arraste o fragmento para mover; arraste qualquer canto para mudar altura e largura.</p>
   <div class="icButtons"><label>Exibição <select id="icMode"><option value="quadro">Quadro móvel / ajustável</option><option value="fundo">Fundo inteiro</option></select></label><button id="icFillCenter">Centralizar fragmento</button></div>
   <div class="icCanvasWrap"><canvas id="icTarget" aria-label="Posicionar foto na cena"></canvas></div>
   <div class="icControls">
    <label>Centro X (%)<input id="icX" type="number" min="0" max="100" step="1"></label>
    <label>Centro Y (%)<input id="icY" type="number" min="0" max="100" step="1"></label>
    <label>Largura (%)<input id="icW" type="number" min="8" max="100" step="1"></label>
    <label>Altura (%)<input id="icH" type="number" min="8" max="100" step="1"></label>
   </div>
   <p class="icHint">A prévia indica o enquadramento da fotografia. A cena completa aparece na prévia principal do Estúdio.</p>
  </section>
 </div>
 <footer class="icFooter"><span id="icStatus">Nenhuma alteração aplicada.</span><div><button id="icCancel">Cancelar</button><button id="icApply" class="primary">Aplicar à cena</button></div></footer>
 </dialog>`;
const css=document.createElement('style');css.textContent=`
#imageComposer{width:min(98vw,1160px);max-width:1160px;max-height:94dvh;overflow:auto;padding:0;border:1px solid #8c6851;border-radius:16px;background:#231d1b;color:#fff1da;box-shadow:0 15px 55px #0009}
#imageComposer::backdrop{background:#080606cc}#imageComposer .icTop{display:flex;justify-content:space-between;gap:12px;align-items:center;padding:12px 16px;background:#30251e;position:sticky;top:0;z-index:2;border-bottom:1px solid #75533f}#imageComposer .icTop strong{display:block;font-size:16px}#imageComposer .icTop small{display:block;font-size:11px;color:#d6b99e}#imageComposer .icContent{display:grid;grid-template-columns:1fr 1fr;gap:12px;padding:12px}#imageComposer section{min-width:0;border:1px solid #5c4439;border-radius:12px;background:#2d2420;padding:10px;display:flex;flex-direction:column;align-items:stretch}
#imageComposer h3{font-size:14px;color:#ffcc99;margin:3px 0}#imageComposer p{font-size:12px;color:#e1c8b1;margin:3px 0 12px}#imageComposer .icCanvasWrap{min-height:150px;display:flex;align-items:center;justify-content:center;flex:1;background:#131010;border-radius:10px;overflow:hidden;padding:7px}#imageComposer canvas{display:block;width:auto;height:auto;max-width:100%;max-height:52dvh;touch-action:none;cursor:crosshair;box-shadow:0 0 0 1px #a07c5d}
#imageComposer .icControls{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:6px;padding:10px 0 0}#imageComposer .icControls label{font-size:10px;color:#d7bfa7}#imageComposer .icControls input{width:100%;font-size:14px;padding:6px;margin-top:4px}#imageComposer .icButtons{display:flex;gap:8px;padding-top:9px}#imageComposer .icFooter{display:flex;justify-content:space-between;align-items:center;gap:10px;padding:11px 16px;position:sticky;bottom:0;background:#30251e;border-top:1px solid #75533f}#imageComposer .icFooter div{display:flex;gap:8px}#imageComposer .icHint{margin-top:8px;color:#bda893}#imageComposer button{white-space:normal}#imageComposer .icButtons input[type=text]{min-width:90px;flex:1}#imageComposer .icButtons input[type=file]{max-width:50%;font-size:11px;min-width:0}
@media(max-width:740px), (max-height:600px){#imageComposer .icContent{display:block;padding:8px}#imageComposer section{margin-bottom:10px}#imageComposer canvas{max-height:44dvh}#imageComposer .icFooter{align-items:flex-start;flex-wrap:wrap}#imageComposer .icTop{padding:9px}#imageComposer h3{margin-bottom:4px}}
`;
document.head.appendChild(css);
const host=document.createElement('div');host.innerHTML=ui;document.body.appendChild(host.firstElementChild);
const $=id=>document.getElementById(id),dlg=$('imageComposer');
let pic=null,model=null,onApply=null,interaction=null,imageFile="",onFile=null;
const copy=o=>JSON.parse(JSON.stringify(o));
const rect=(event,canvas)=>{const r=canvas.getBoundingClientRect();return {x:clamp((event.clientX-r.left)/r.width),y:clamp((event.clientY-r.top)/r.height)};};
function drawSource(){if(!pic||!model)return;const c=$('icSource'),cx=c.getContext('2d'),w=c.width,h=c.height;cx.clearRect(0,0,w,h);cx.drawImage(pic,0,0,w,h);const [x,y,cw,ch]=model.crop;cx.fillStyle='#0008';cx.fillRect(0,0,w,h);cx.drawImage(pic,x*pic.width,y*pic.height,cw*pic.width,ch*pic.height,x*w,y*h,cw*w,ch*h);cx.strokeStyle='#ffda9c';cx.lineWidth=Math.max(2,w/350);cx.strokeRect(x*w,y*h,cw*w,ch*h);cx.fillStyle='#ffda9c';for(const [hx,hy] of [[x,y],[x+cw,y],[x,y+ch],[x+cw,y+ch],[x+cw/2,y],[x+cw/2,y+ch],[x,y+ch/2],[x+cw,y+ch/2]]){cx.beginPath();cx.arc(hx*w,hy*h,Math.max(7,w/100),0,2*Math.PI);cx.fill();}}
function drawCover(cx,image,sx,sy,sw,sh,dx,dy,dw,dh){
 const ratio=Math.max(dw/sw,dh/sh),mw=dw/ratio,mh=dh/ratio;
 const left=sx+(sw-mw)*clamp(model.align_x??.5),top=sy+(sh-mh)*clamp(model.align_y??.5);
 cx.drawImage(image,left,top,mw,mh,dx,dy,dw,dh);
}
function drawTarget(){if(!pic||!model)return;const c=$('icTarget'),cx=c.getContext('2d'),w=c.width,h=c.height;
 cx.fillStyle=model.bg||'#241b1a';cx.fillRect(0,0,w,h);cx.fillStyle='#ffffff22';
 for(let i=1;i<3;i++){cx.fillRect(i*w/3,0,1,h);cx.fillRect(0,i*h/3,w,1);}
 const [sx,sy,sw,sh]=model.crop;
 const x=model.x*w-model.w*w/2,y=model.y*h-model.h*h/2,dw=model.w*w,dh=model.h*h;
 if(model.modo==='fundo'){
  drawCover(cx,pic,sx*pic.width,sy*pic.height,sw*pic.width,sh*pic.height,0,0,w,h);
 }else{
  cx.save();cx.beginPath();cx.rect(x,y,dw,dh);cx.clip();
  if(model.fit==='contain'||model.fit==='pad'){
   const rr=Math.min(dw/(sw*pic.width),dh/(sh*pic.height));const iw=sw*pic.width*rr,ih=sh*pic.height*rr;
   cx.drawImage(pic,sx*pic.width,sy*pic.height,sw*pic.width,sh*pic.height,x+(dw-iw)*clamp(model.align_x??.5),y+(dh-ih)*clamp(model.align_y??.5),iw,ih);
  }else if(model.fit==='stretch')cx.drawImage(pic,sx*pic.width,sy*pic.height,sw*pic.width,sh*pic.height,x,y,dw,dh);
  else drawCover(cx,pic,sx*pic.width,sy*pic.height,sw*pic.width,sh*pic.height,x,y,dw,dh);
  cx.restore();cx.lineWidth=Math.max(3,w/180);cx.strokeStyle='#ffda9c';cx.strokeRect(x,y,dw,dh);
  cx.fillStyle='#ffda9c';for(const px of [x,x+dw])for(const py of [y,y+dh])cx.fillRect(px-10,py-10,20,20);
 }
}
function redraw(){drawSource();drawTarget();$('icMode').value=model.modo||'quadro';for(const k of ['x','y','w','h'])$('ic'+k.toUpperCase()).value=Math.round(model[k]*100);}
function setCrop(x,y,w,h){const left=clamp(x),top=clamp(y);model.crop=[left,top,Math.max(.01,Math.min(1-left,w)),Math.max(.01,Math.min(1-top,h))];redraw();}
function cropHit(p,bounds){
 const [x,y,w,h]=bounds,r=x+w,b=y+h;const tol=.035;const near=(a,b)=>Math.abs(a-b)<tol;
 const inside=p.x>=x&&p.x<=r&&p.y>=y&&p.y<=b;
 const edges=[];if(near(p.x,x))edges.push('w');else if(near(p.x,r))edges.push('e');
 if(near(p.y,y))edges.push('n');else if(near(p.y,b))edges.push('s');
 if(edges.length&&p.x>=x-tol&&p.x<=r+tol&&p.y>=y-tol&&p.y<=b+tol)return {kind:'cropResize',edges};
 return inside?{kind:'cropMove'}:{kind:'cropNew'};
}
function bindCanvas(canvas,kind){
 canvas.addEventListener('pointerdown',e=>{if(!model||e.pointerType==='mouse'&&e.button!==0)return;const pt=rect(e,canvas);
  if(kind==='crop'){interaction={...cropHit(pt,model.crop),start:pt,old:[...model.crop]};}
  else {const x=model.x-model.w/2,y=model.y-model.h/2;
   const corners=[['nw',x,y],['ne',x+model.w,y],['sw',x,y+model.h],['se',x+model.w,y+model.h]];
   const found=model.modo==='fundo'?null:corners.find(k=>Math.hypot(pt.x-k[1],pt.y-k[2])<.055);
   const inside=pt.x>=x&&pt.x<=x+model.w&&pt.y>=y&&pt.y<=y+model.h;
   interaction={kind:found?'resize':inside?'move':'center',corner:found?.[0],start:pt,old:copy(model)};
   if(model.modo==='fundo'){$('icStatus').textContent='Para redimensionar, altere Exibição para Quadro móvel.';interaction=null;return;}
   if(interaction.kind==='center'){model.x=pt.x;model.y=pt.y;interaction.kind='move';interaction.start=pt;interaction.old=copy(model);redraw();}}
  canvas.setPointerCapture(e.pointerId);e.preventDefault();});
 canvas.addEventListener('pointermove',e=>{if(!interaction||!model||canvas.hasPointerCapture(e.pointerId)===false)return;const pt=rect(e,canvas),o=interaction.old;
  if(kind==='crop'){
   const [x,y,w,h]=o,dx=pt.x-interaction.start.x,dy=pt.y-interaction.start.y;
   if(interaction.kind==='cropMove')setCrop(clamp(x+dx,0,1-w),clamp(y+dy,0,1-h),w,h);
   else if(interaction.kind==='cropResize'){
     let left=x,right=x+w,top=y,bottom=y+h;
     if(interaction.edges.includes('w'))left=clamp(x+dx,0,right-.01);
     if(interaction.edges.includes('e'))right=clamp(x+w+dx,left+.01,1);
     if(interaction.edges.includes('n'))top=clamp(y+dy,0,bottom-.01);
     if(interaction.edges.includes('s'))bottom=clamp(y+h+dy,top+.01,1);
     setCrop(left,top,right-left,bottom-top);
   }else setCrop(Math.min(pt.x,interaction.start.x),Math.min(pt.y,interaction.start.y),Math.max(.01,Math.abs(pt.x-interaction.start.x)),Math.max(.01,Math.abs(pt.y-interaction.start.y)));
  }
  else if(interaction.kind==='move'){model.x=clamp(o.x+pt.x-interaction.start.x);model.y=clamp(o.y+pt.y-interaction.start.y);redraw();}
  else if(interaction.kind==='resize'){
   let left=o.x-o.w/2,right=o.x+o.w/2,top=o.y-o.h/2,bottom=o.y+o.h/2;
   const dx=pt.x-interaction.start.x,dy=pt.y-interaction.start.y;
   if(interaction.corner.includes('w'))left=Math.min(right-.08, left+dx);else right=Math.max(left+.08,right+dx);
   if(interaction.corner.includes('n'))top=Math.min(bottom-.08, top+dy);else bottom=Math.max(top+.08,bottom+dy);
   model.w=clamp(right-left,.08,1);model.h=clamp(bottom-top,.08,1);
   model.x=clamp((left+right)/2);model.y=clamp((top+bottom)/2);redraw();}
  e.preventDefault();});
 const end=()=>{interaction=null;};canvas.addEventListener('pointerup',end);canvas.addEventListener('pointercancel',end);
}
bindCanvas($('icSource'),'crop');bindCanvas($('icTarget'),'target');
for(const k of ['x','y','w','h'])$('ic'+k.toUpperCase()).addEventListener('change',e=>{if(!model)return;model[k]=clamp(Number(e.target.value)/100,k==='w'||k==='h'?.08:0,1);redraw();});
$('icMode').onchange=e=>{if(!model)return;model.modo=e.target.value==='fundo'?'fundo':'quadro';redraw();};
$('icFillCenter').onclick=()=>{if(!model)return;Object.assign(model,{modo:'quadro',x:.5,y:.5,w:.75,h:.60});redraw();};
$('icAll').onclick=()=>setCrop(0,0,1,1);
$('icCenter').onclick=()=>setCrop(.10,.10,.80,.80);
async function filePost(url,payload){
 const r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
 const data=await r.json();if(!r.ok)throw Error(data.error||'HTTP '+r.status);return data;
}
function loadBytes(file){return new Promise((resolve,reject)=>{const r=new FileReader();r.onload=()=>resolve(r.result);r.onerror=reject;r.readAsDataURL(file);});}
$('icImport').onclick=async()=>{
 const file=$('icImportFile').files[0];if(!file){$('icStatus').textContent='Selecione uma imagem primeiro.';return;}
 if(file.size>12_000_000){$('icStatus').textContent='Imagem acima de 12 MB.';return;}
 try{$('icStatus').textContent='Importando…';const data=await loadBytes(file);
  const preferred_name=$('icFileName').value.trim();const result=await filePost('/api/upload',{kind:'image',filename:file.name,preferred_name,data});
  imageFile=result.filename;model.crop=[0,0,1,1];await refreshImage('/api/media/image?file='+encodeURIComponent(imageFile));
  $('icStatus').textContent='Imagem importada: '+imageFile+'. Toque em Aplicar à cena.';
 }catch(e){$('icStatus').textContent='Falha na importação: '+e.message;}
};
$('icRename').onclick=async()=>{
 const label=$('icFileName').value.trim();if(!label){$('icStatus').textContent='Informe um novo nome.';return;}
 try{const result=await filePost('/api/media/image/alias',{file:imageFile,new_name:label});imageFile=result.filename;
  $('icStatus').textContent='Novo nome: '+imageFile+'. A imagem original foi preservada.';
 }catch(e){$('icStatus').textContent=e.message;}
};
const close=()=>dlg.close();$('icClose').onclick=close;$('icCancel').onclick=close;
$('icApply').onclick=()=>{if(onApply){const result=onApply({...copy(model),arquivo:imageFile});if(result!==false)close();}};
async function open({url,config,video,onChange}){
 if(!url)throw Error('Importe uma imagem antes de recortar');
 onApply=onChange;pic=null;model=copy(config);imageFile=model.arquivo||'';
 model.crop=Array.isArray(model.crop)&&model.crop.length===4?model.crop.map(v=>clamp(v)):[0,0,1,1];
 for(const [k,v] of Object.entries({x:.5,y:.56,w:.72,h:.40}))if(!Number.isFinite(Number(model[k])))model[k]=v;
 dlg.showModal();$('icStatus').textContent='Carregando imagem…';
 $('icFileName').value=imageFile.replace(/\.[^.]+$/,'');
 $('icImportFile').value='';
 try{await refreshImage(url,video);}
 catch(e){$('icStatus').textContent=e.message;throw e;}
}
async function refreshImage(url,video){
 const img=new Image();await new Promise((resolve,reject)=>{img.onload=resolve;img.onerror=()=>reject(Error('Não foi possível abrir esta imagem'));img.src=url;});
 if(!dlg.open)return;pic=img;const source=$('icSource'),target=$('icTarget');
 source.width=720;source.height=Math.max(1,Math.round(720*img.naturalHeight/img.naturalWidth));
 if(video){target.width=500;target.height=Math.round(500*video.height/video.width);}
 $('icStatus').textContent=`Imagem ${img.naturalWidth} × ${img.naturalHeight}`;redraw();
}
window.StudioImageComposer={open};
})();
