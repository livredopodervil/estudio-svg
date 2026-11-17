/* ESTUDIO_V3_MEDIA_PATCH_2026_11: clipes no navegador. */
(() => {
  'use strict';
  let active=-1, source='', clip=null, sceneTime=0, playing=false, rate=1, playPending=false, failed=false, generation=0;
  const clamp=(x,a=0,b=1)=>Math.max(a,Math.min(b,Number(x)||0));
  const stage=document.getElementById('stageShell');
  if(!stage)return;
  stage.style.position='relative';
  const video=document.createElement('video');
  video.setAttribute('aria-label','Clipe sobreposto à apresentação');
  video.setAttribute('playsinline','');video.setAttribute('webkit-playsinline','');
  video.playsInline=true;video.muted=true;video.defaultMuted=true;video.preload='auto';
  video.style.cssText='position:absolute;z-index:3;display:none;pointer-events:none;background:transparent;border-radius:6px;';
  stage.append(video);
  const status=msg=>{const n=document.getElementById('clipStatus')||document.getElementById('status');if(n)n.textContent=msg;};
  const fileName=c=>{
    const n=String(c?.arquivo||'');
    return /^[A-Za-z0-9_][A-Za-z0-9_.-]{0,154}\.(mp4|webm|ogv|mov|m4v|mkv)$/i.test(n)&&!n.includes('..')?n:'';
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
      left:(left+cx*fitW-w/2)+'px',top:(top+cy*fitH-h/2)+'px',
      width:w+'px',height:h+'px',objectFit:clip.fit==='contain'?'contain':'cover',
      opacity:String(clamp(clip.opacidade??1))
    });
  }
  function startVideo(){
    if(!playing||!clip||failed||playPending||!video.paused||video.seeking||video.readyState<1)return;
    const token=generation;playPending=true;
    try{
      Promise.resolve(video.play()).catch(e=>{
        if(token!==generation||!playing||e.name==='AbortError')return;
        failed=true;status('Clipe '+source+': '+e.message+' — pause e reproduza novamente.');
      }).finally(()=>{if(token===generation)playPending=false;});
    }catch(e){playPending=false;failed=true;status('Clipe '+source+': '+e.message);}
  }
  function sync(force=false){
    if(!clip)return;
    const d=video.duration,t=Math.max(0,Number(clip.inicio)||0)+sceneTime;
    video.playbackRate=rate;
    if(!Number.isFinite(d)||d<=0||video.readyState<1){if(!playing)video.pause();return;}
    if(clip.repetir===false&&t>=d){video.style.display='none';video.pause();return;}
    video.style.display='block';
    const dest=clip.repetir===false?t:t%d;
    const delta=Math.abs(video.currentTime-dest);
    // Native video follows the canonical scene clock; do not issue a seek every RAF.
    if(!video.seeking&&delta>((force||!playing) ? .025 : .35)){
      try{video.currentTime=dest;}catch(_){}
    }
    if(playing)startVideo();else video.pause();
  }
  video.addEventListener('loadedmetadata',()=>{if(clip){status('Clipe: '+source+' · '+video.duration.toFixed(2)+' s');sync(true);}});
  video.addEventListener('canplay',()=>sync());
  video.addEventListener('seeked',()=>sync());
  video.addEventListener('error',()=>{if(clip){failed=true;status('Clipe ausente ou formato incompatível: '+source+' (erro '+(video.error?.code||'?')+').');}});
  function pause(){playing=false;video.pause();}
  function play(){playing=true;failed=false;sync(true);}
  function scene(i,c,dimensions,localCurrent,isPlaying,newRate=1){
    const next=c?.video_clipe,filename=fileName(next);
    window.StudioMedia.dimensions=dimensions||{};
    sceneTime=Math.max(0,Number(localCurrent)||0);rate=clamp(newRate,.5,2);
    if(i===active&&source===filename){clip=filename?next:null;playing=!!isPlaying;place();sync(true);return;}
    ++generation;pause();playPending=false;failed=false;active=i;source=filename;clip=filename?next:null;
    if(!filename){video.style.display='none';video.removeAttribute('src');video.load();status(next?.arquivo?'Nome de clipe incompatível: '+String(next.arquivo):'');return;}
    video.loop=next.repetir!==false;video.muted=true;
    video.src=(location.pathname.startsWith('/player-v3/')?'/api/media/clip?file=':'./midia/')+encodeURIComponent(filename);
    video.style.display='block';place();status('Carregando clipe: '+filename);playing=!!isPlaying;video.load();sync(true);
  }
  function tick(i,local,isPlaying,newRate=1){
    if(i!==active)return;
    sceneTime=Math.max(0,Number(local)||0);playing=!!isPlaying;rate=clamp(newRate,.5,2);sync();
  }
  function seek(i,local){if(i===active){sceneTime=Math.max(0,Number(local)||0);sync(true);}}
  if(typeof ResizeObserver!=='undefined')new ResizeObserver(place).observe(stage);
  else window.addEventListener('resize',place);
  window.addEventListener('pagehide',pause);
  window.StudioMedia={scene,tick,seek,play,pause,dimensions:{}};
})();
