// Public presentation adapter: shares the same domain, timeline, renderer and audio.
import {DocumentService} from './model.mjs';
import {Timeline} from './timeline.mjs';
import {renderSVG} from './render-svg.mjs';
import {AudioAdapter} from './audio.mjs';
const $=id=>document.getElementById(id);
const audio=new AudioAdapter();let generation=0,raf=0,playing=false,time=0;
try {
 const bytes=Uint8Array.from(atob($('gil-source').textContent.trim()),c=>c.charCodeAt(0));
 const doc=new DocumentService(new TextDecoder().decode(bytes)).document;
 const timeline=new Timeline(doc),duration=doc.spec.stage.duration;
 $('seek').max=duration; $('stage').style.aspectRatio=`${doc.spec.stage.width}/${doc.spec.stage.height}`;
 function draw(){const result=renderSVG(timeline.sample(time));$('stage').innerHTML=result.svg;$('seek').value=time;$('clock').textContent=`${time.toFixed(2)} / ${duration.toFixed(2)} s`;}
 function pause(){generation++;playing=false;cancelAnimationFrame(raf);audio.stop();$('play').disabled=false;}
 function seek(v){pause();time=Math.max(0,Math.min(duration,Number(v)));draw();}
 function fail(e){pause();$('status').textContent='Erro: '+e.message;}
 $('play').onclick=async()=>{pause();if(time>=duration)time=0;const current=++generation;playing=true;$('play').disabled=true;let delay=0;try{if($('sound').checked){await audio.play(doc,timeline,time);delay=60;}}catch(e){$('status').textContent='Som indisponível: '+e.message;}if(current!==generation)return;const start=performance.now()+delay,base=time;function tick(now){if(!playing||generation!==current)return;try{time=Math.min(duration,base+Math.max(0,now-start)/1000);draw();if(time>=duration)pause();else raf=requestAnimationFrame(tick);}catch(e){fail(e);}}raf=requestAnimationFrame(tick);};
 $('pause').onclick=pause;$('reset').onclick=()=>seek(0);$('seek').oninput=()=>{try{seek($('seek').value);}catch(e){fail(e);}};$('sound').onchange=pause;
 addEventListener('pagehide',pause);draw();$('status').textContent='Pronto · reprodução local no navegador';
} catch(e){$('status').textContent='Não foi possível abrir a composição: '+e.message;$('play').disabled=true;}
