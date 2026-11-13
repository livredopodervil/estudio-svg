/* ESTUDIO_V3_MEDIA_PATCH_2026_11: clipes no navegador. */
(() => {
  'use strict';
  let el=null, active=-1, source='', clip=null, sceneStart=0, playing=false, timer=0;
  const clamp=(x,a=0,b=1)=>Math.max(a,Math.min(b,Number(x)||0));
  const stage=document.getElementById('stageShell');
  if(!stage)return;
  stage.style.position='relative';
  const video=document.createElement('video');
  video.setAttribute('aria-label','Clipe sobreposto à apresentação');
  video.setAttribute('playsinline',''); video.setAttribute('webkit-playsinline','');
  video.playsInline=true;video.muted=true;video.defaultMuted=true;video.preload='metadata';
  video.style.cssText='position:absolute;z-index:3;display:none;pointer-events:none;background:transparent;border-radius:6px;';
  stage.append(video);el=video;
  const status=msg=>{const n=document.getElementById('status');if(n)n.textContent=msg;};
  const fileName=clip=>{
    const n=String(clip?.arquivo||'');
    return /^[A-Za-z0-9][A-Za-z0-9_.-]{0,140}\.(mp4|webm|ogv)$/i.test(n)&&!n.includes('..')?n:'';
  };
  function place(){
    if(!clip)return;
    const rect=stage.getBoundingClientRect(),W=rect.width,H=rect.height;
    const dimensions=window.StudioMedia.dimensions||{};
    const ar=Math.max(.05,(Number(dimensions.width)||720)/(Number(dimensions.height)||1280));
    const fitW=Math.min(W,H*ar),fitH=fitW/ar;
    const left=(W-fitW)/2,top=(H-fitH)/2;
    const cx=clamp(clip.x??.5),cy=clamp(clip.y??.5);
    const w=clamp(clip.w??.7,0,1)*fitW,h=clamp(clip.h??.4,0,1)*fitH;
    Object.assign(video.style,{
      left:(left+cx*fitW-w/2)+'px', top:(top+cy*fitH-h/2)+'px',
      width:w+'px',height:h+'px',objectFit:clip.fit==='contain'?'contain':'cover',
      opacity:String(clamp(clip.opacidade??1))
    });
  }
  function sync(local){
    if(!clip||!Number.isFinite(video.duration)||video.duration<=0)return;
    const start=Math.max(0,Number(clip.inicio)||0);
    const t=start+Math.max(0,Number(local)||0);
    const dest=clip.repetir===false?Math.min(video.duration-.02,t):t%video.duration;
    if(Number.isFinite(dest)&&Math.abs((video.currentTime||0)-dest)>.5){
      try{video.currentTime=Math.max(0,dest)}catch(_){}
    }
  }
  video.addEventListener('loadedmetadata',()=>sync(sceneStart));
  video.addEventListener('error',()=>{if(clip)status('Clipe ausente ou formato incompatível: '+fileName(clip));});
  video.addEventListener('ended',()=>{if(clip&&!clip.repetir)video.pause()});
  function pause(){playing=false;video.pause();}
  function play(){
    playing=true;
    if(clip){video.play().catch(e=>status('Clipe bloqueado: '+e.message));}
  }
  function scene(i,c,dimensions,localCurrent,isPlaying){
    const next=c?.video_clipe,filename=fileName(next);
    window.StudioMedia.dimensions=dimensions||{};
    sceneStart=Math.max(0,Number(localCurrent)||0);
    if(i===active&&source===filename){place();return;}
    pause();active=i;source=filename;clip=filename?next:null;
    if(!filename){video.style.display='none';video.removeAttribute('src');video.load();return;}
    video.loop=next.repetir!==false;
    video.src='./midia/'+encodeURIComponent(filename);
    video.style.display='block';place();video.load();
    if(isPlaying){play();}
  }
  function seek(i,local){
    if(i===active){sceneStart=Math.max(0,local||0);sync(sceneStart)}
  }
  if(typeof ResizeObserver!=='undefined')new ResizeObserver(place).observe(stage);
  else window.addEventListener('resize',place);
  window.addEventListener('pagehide',pause);
  window.StudioMedia={scene,seek,play,pause,dimensions:{}};
})();
