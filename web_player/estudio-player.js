/* Estúdio Player Web v1.0 — autor do projeto Estúdio SVG: Rogério Duarte.
 * Dependências: nenhuma. Manifesto: studio.web-player/v1.
 * SVGs são exibidos como IMG (não são inseridos via innerHTML).
 */
const CONTRACT = 'studio.web-player/v1';
const STYLE = `
:host{display:block;box-sizing:border-box;--ep-bg:#101820;--ep-fg:#f4f6fa;--ep-accent:#51c7df;font-family:system-ui,-apple-system,sans-serif;color:var(--ep-fg);contain:content}
*,*::before,*::after{box-sizing:border-box}
.ep{background:var(--ep-bg);position:relative;min-height:270px;height:100%;border-radius:12px;overflow:hidden;display:grid;grid-template-rows:minmax(210px,1fr) auto;isolation:isolate}
.viewport{position:relative;background:#0c1218;min-height:210px;display:grid;place-items:center;overflow:hidden;touch-action:manipulation}
.artboard{position:relative;max-width:100%;max-height:100%;overflow:hidden;background:#111;flex:none}
.artboard img{width:100%;height:100%;display:block;object-fit:contain;user-select:none;-webkit-user-drag:none}
.artboard video{position:absolute;pointer-events:none;background:#080b0e}
.artboard video[hidden]{display:none}
.toolbar{display:flex;gap:7px;flex-wrap:wrap;align-items:center;justify-content:center;background:#151d29e8;padding:9px;min-height:54px;transition:opacity .2s,transform .2s}
button,select{color:var(--ep-fg);border:1px solid #526170;border-radius:7px;background:#243244;padding:7px 10px;font:inherit;font-size:13px;min-height:36px}
button{cursor:pointer}button:focus-visible,select:focus-visible{outline:2px solid var(--ep-accent)}
button:hover{background:#33465d}button:disabled{opacity:.4;cursor:not-allowed}
.status{font-size:12px;color:#c4d3e2;min-width:85px;text-align:center}
.titles{position:absolute;inset:6px 6px auto 6px;pointer-events:none;display:flex;justify-content:space-between;align-items:center;font-size:12px;color:#d5e1f5}
.subtitle{position:absolute;left:8px;right:8px;bottom:8px;background:#07111ccc;color:white;padding:9px 12px;border-radius:7px;font-size:14px;text-align:center;pointer-events:none;line-height:1.45;max-height:27%;overflow:auto}
.subtitle[hidden]{display:none}
.error{padding:24px;text-align:center;line-height:1.5;color:#ffd3c9}
.loading{padding:16px;color:#c5d9eb}
.ep.is-playing:not(.show-ui) .toolbar{opacity:0;pointer-events:none;transform:translateY(6px)}
.ep.is-playing:not(.show-ui) .subtitle{bottom:8px}
@media(prefers-reduced-motion:reduce){.toolbar{transition:none}}
`;

function safeSameOrigin(url, base) {
  const u = new URL(url, base);
  if (u.origin !== new URL(base).origin || !['http:', 'https:', 'file:'].includes(u.protocol)) {
    throw Error('Recurso fora da origem permitida');
  }
  if (u.username || u.password) throw Error('URL com credenciais não permitida');
  return u.href;
}
function positiveNumber(x, fallback) { const n=Number(x); return Number.isFinite(n)&&n>0?n:fallback; }
function clamp(x,lo,hi) { return Math.min(hi,Math.max(lo,x)); }
function validateManifest(m) {
  if (!m || m.schema!==CONTRACT) throw Error('Manifesto incompatível (esperado '+CONTRACT+')');
  if (!m.video || !positiveNumber(m.video.width,0) || !positiveNumber(m.video.height,0)) throw Error('Dimensões inválidas');
  if (!Array.isArray(m.scenes) || !m.scenes.length || m.scenes.length>500) throw Error('Cenas inválidas');
  for (const s of m.scenes) {
    if (!positiveNumber(s.duration,0)||!Array.isArray(s.frames)||!s.frames.length||s.frames.length>4000) throw Error('Quadros ou duração inválidos');
    if (!positiveNumber(s.fps,0)|| s.frames.some(f=>typeof f!=='string'||!f.startsWith('frames/'))) throw Error('Referência de quadro inválida');
  }
  return m;
}

export class EstudioPlayer extends HTMLElement {
  static get observedAttributes(){ return ['src']; }
  constructor(){
    super();
    this.attachShadow({mode:'open'});
    this._manifest=null;this._base='';this._sceneIndex=0;this._sceneTime=0;
    this._playing=false;this._paused=false;this._raf=0;this._epoch=0;
    this._speech=null;this._speechPending=false;this._speechEnded=true;this._speechToken=0;
    this._clip='';this._clipIndex=-1;this._loadedToken=0;this._showTimeout=0;
    this._speed=1;this._voiceEnabled=true;this._captions=true;
  }
  connectedCallback(){this._render();this._observeSize();if(this.getAttribute('src'))this.load(this.getAttribute('src'));}
  disconnectedCallback(){this.stop();this._resizeObserver?.disconnect();clearTimeout(this._showTimeout);}
  attributeChangedCallback(name,oldV,newV){if(name==='src'&&oldV!==newV&&this.isConnected&&this._q&&newV)this.load(newV);}
  async load(src){
    this.stop();const token=++this._loadedToken;
    this._message('Carregando apresentação…');
    try{
      const abs=safeSameOrigin(src,document.baseURI);
      const response=await fetch(abs,{cache:'no-cache'});
      if(!response.ok)throw Error('Falha HTTP '+response.status);
      const m=validateManifest(await response.json());
      if(token!==this._loadedToken)return;
      this._manifest=m;this._base=abs;
      this._sceneIndex=0;this._sceneTime=0;
      this._message('');this._fit();this._draw(0);this._status();
      this.dispatchEvent(new CustomEvent('loaded',{detail:{manifest:m}}));
    }catch(e){if(token!==this._loadedToken)return;this._manifest=null;this._message('Não foi possível abrir o projeto: '+e.message,true);this.dispatchEvent(new CustomEvent('playererror',{detail:{message:e.message}}));}
  }
  _render(){
    this.shadowRoot.innerHTML=`<style>${STYLE}</style><section class="ep" part="container" aria-label="Apresentação audiovisual"><div class="viewport" part="viewport" tabindex="0"><div class="artboard"><img alt="Quadro da apresentação"><video muted playsinline preload="metadata" hidden></video><div class="titles"><span class="scene-title"></span></div><div class="subtitle" aria-live="off" hidden></div></div><div class="loading">Abra uma apresentação.</div></div><div class="toolbar" role="toolbar" aria-label="Controles do player"><button class="back" title="Cena anterior" aria-label="Cena anterior">◀◀</button><button class="play" title="Reproduzir ou pausar">▶ Iniciar</button><button class="next" title="Próxima cena" aria-label="Próxima cena">▶▶</button><button class="voice" title="Alternar narração">🔊 Voz</button><button class="captions" title="Alternar legendas">CC</button><select class="speed" title="Velocidade de narração" aria-label="Velocidade da voz"><option value="1">1×</option><option value="1.25">1,25×</option><option value="1.5">1,5×</option><option value="2">2×</option></select><button class="full" title="Tela cheia">⛶</button><span class="status" aria-live="polite"></span></div></section>`;
    const q=(s)=>this.shadowRoot.querySelector(s);this._q=q;
    q('.play').onclick=()=>this._playing?this.pause():this.play();
    q('.next').onclick=()=>this.goTo(this._sceneIndex+1);
    q('.back').onclick=()=>this.goTo(this._sceneIndex-1);
    q('.voice').onclick=()=>{this._voiceEnabled=!this._voiceEnabled;q('.voice').textContent=this._voiceEnabled?'🔊 Voz':'🔇 Voz';this._cancelSpeech();if(this._playing)this._speakCurrent();};
    q('.captions').onclick=()=>{this._captions=!this._captions;this._draw(this._sceneTime);};
    q('.speed').onchange=()=>{this._speed=Number(q('.speed').value)||1;};
    q('.full').onclick=()=>{const target=q('.ep');if(document.fullscreenElement)document.exitFullscreen?.();else target.requestFullscreen?.().catch(()=>{});};
    q('.viewport').onclick=()=>this._revealControls();
    q('.viewport').onkeydown=(e)=>{if(e.key===' '||e.key==='Enter'){e.preventDefault();this._playing?this.pause():this.play();}};
  }
  _observeSize(){if(typeof ResizeObserver==='function'){this._resizeObserver=new ResizeObserver(()=>this._fit());this._resizeObserver.observe(this._q('.viewport'));}else window.addEventListener('resize',()=>this._fit(),{passive:true});}
  _fit(){const m=this._manifest;if(!m)return;const p=this._q('.viewport'),box=this._q('.artboard');const r=p.getBoundingClientRect();const scale=Math.min(r.width/m.video.width,r.height/m.video.height);if(!Number.isFinite(scale)||scale<=0)return;box.style.width=Math.max(1,Math.floor(m.video.width*scale))+'px';box.style.height=Math.max(1,Math.floor(m.video.height*scale))+'px';}
  _message(t,err=false){const l=this._q('.loading');l.textContent=t;l.style.display=t?'block':'none';l.classList.toggle('error',err);}
  _status(){const m=this._manifest;this._q('.status').textContent=m?`${this._sceneIndex+1}/${m.scenes.length}`:'—';this._q('.play').textContent=this._playing?'Ⅱ Pausar':'▶ Iniciar';}
  _draw(t){const m=this._manifest;if(!m)return;const s=m.scenes[this._sceneIndex];const idx=clamp(Math.floor(t*s.fps),0,s.frames.length-1);const frameUrl=safeSameOrigin(s.frames[idx],this._base);const img=this._q('img');if(img.src!==frameUrl)img.src=frameUrl;
    this._q('.scene-title').textContent=s.title||'';
    const sub=this._q('.subtitle');sub.textContent=s.voiceText||'';sub.hidden=!this._captions||!sub.textContent;
    this._clipAt(s,t);
  }
  _clipAt(s,t){const el=this._q('video'),c=s.clip||{};
    if(!c.file){el.pause();el.hidden=true;this._clip='';return;}
    const u=safeSameOrigin(c.file,this._base);
    if(this._clip!==u||this._clipIndex!==this._sceneIndex){el.pause();el.src=u;el.load();this._clip=u;this._clipIndex=this._sceneIndex;}
    const w=clamp(Number(c.w??.7),0.01,1.9),h=clamp(Number(c.h??.4),0.01,1.9),x=Number(c.x??.5),y=Number(c.y??.56);
    Object.assign(el.style,{left:(x-w/2)*100+'%',top:(y-h/2)*100+'%',width:w*100+'%',height:h*100+'%',objectFit:c.fit==='contain'?'contain':'cover',opacity:String(clamp(Number(c.opacity??1),0,1))});
    const raw=Math.max(0,Number(c.start||0)+t),duration=el.duration;const over=!c.loop&&Number.isFinite(duration)&&raw>=duration;
    el.hidden=over;if(over){el.pause();return;}
    el.loop=!!c.loop;
    const wanted=c.loop&&Number.isFinite(duration)&&duration>0?raw%duration:raw;
    if(el.readyState>=1&&Math.abs(el.currentTime-wanted)>.55){try{el.currentTime=wanted;}catch{}}
    if(this._playing&&!this._paused&&el.paused)el.play().catch(()=>{});
    if(!this._playing&&!el.paused)el.pause();
  }
  _cancelSpeech(){this._speechToken++;this._speechPending=false;this._speechEnded=true;this._speech=null;try{window.speechSynthesis?.cancel();}catch{}}
  _speakCurrent(){
    this._cancelSpeech();const s=this._manifest.scenes[this._sceneIndex];
    const text=(s.voiceText||'').trim();
    if(!this._voiceEnabled||!s.voiceEnabled||!text||typeof window.SpeechSynthesisUtterance==='undefined'||!('speechSynthesis' in window))return;
    const token=this._speechToken;const u=new SpeechSynthesisUtterance(text);
    const api=window.speechSynthesis;
    const locale=s.lang||'pt-BR';u.lang=locale;u.rate=this._speed;
    const voices=api.getVoices?.()||[];
    u.voice=voices.find(v=>v.lang.toLowerCase()===locale.toLowerCase()&&v.localService)||voices.find(v=>v.lang.toLowerCase()===locale.toLowerCase())||voices.find(v=>v.lang.toLowerCase().startsWith('pt'))||null;
    this._speechPending=true;this._speechEnded=false;this._speech=u;
    u.onend=()=>{if(this._speechToken!==token)return;this._speechEnded=true;this._speechPending=false;};
    u.onerror=()=>{if(this._speechToken!==token)return;this._speechEnded=true;this._speechPending=false;};
    try{api.speak(u);}catch{this._speechEnded=true;this._speechPending=false;}
  }
  play(){
    if(!this._manifest||this._playing)return;
    const continuing=this._paused;
    this._playing=true;this._paused=false;this._epoch=performance.now()-this._sceneTime*1000;
    if(continuing){try{window.speechSynthesis?.resume();}catch{}}else this._speakCurrent();
    this._q('.ep').classList.add('is-playing');this._q('.ep').classList.remove('show-ui');this._status();
    this._raf=requestAnimationFrame(this._tick);
  }
  _tick=(now)=>{
    if(!this._playing)return;
    const s=this._manifest.scenes[this._sceneIndex];this._sceneTime=Math.max(0,(now-this._epoch)/1000);
    const isEnded=this._sceneTime>=s.duration;
    if(isEnded&&this._speechPending){this._sceneTime=s.duration;this._draw(this._sceneTime);}else if(isEnded){if(this._sceneIndex>=this._manifest.scenes.length-1){this.stop();return;}this._enterScene(this._sceneIndex+1);return;}
    else this._draw(this._sceneTime);
    this._raf=requestAnimationFrame(this._tick);
  }
  _enterScene(index){this._cancelSpeech();this._sceneIndex=index;this._sceneTime=0;this._epoch=performance.now();this._clipIndex=-1;this._draw(0);this._status();if(this._playing)this._speakCurrent();this._raf=requestAnimationFrame(this._tick);}
  pause(){if(!this._playing)return;this._playing=false;this._paused=true;cancelAnimationFrame(this._raf);this._q('video').pause();try{window.speechSynthesis?.pause();}catch{}this._q('.ep').classList.remove('is-playing');this._status();}
  stop(){this._playing=false;this._paused=false;cancelAnimationFrame(this._raf);this._cancelSpeech();if(this._q){this._q('video').pause();this._q('.ep').classList.remove('is-playing');this._status();}}
  goTo(index){if(!this._manifest)return;const previousPlaying=this._playing;this._playing=false;cancelAnimationFrame(this._raf);this._cancelSpeech();this._sceneIndex=clamp(index,0,this._manifest.scenes.length-1);this._sceneTime=0;this._paused=false;this._draw(0);this._status();if(previousPlaying)this.play();}
  _revealControls(){this._q('.ep').classList.add('show-ui');clearTimeout(this._showTimeout);this._showTimeout=setTimeout(()=>this._q('.ep')?.classList.remove('show-ui'),3500);}
}
if(!customElements.get('estudio-player'))customElements.define('estudio-player',EstudioPlayer);

export function openEstudioModal(manifestUrl,{title='Apresentação audiovisual'}={}){
  const overlay=document.createElement('div');overlay.style.cssText='position:fixed;inset:0;background:#000d;z-index:2147483000;display:grid;place-items:center;padding:12px';
  const dialog=document.createElement('section');dialog.setAttribute('role','dialog');dialog.setAttribute('aria-modal','true');dialog.setAttribute('aria-label',title);dialog.style.cssText='width:min(97vw,720px);max-height:96vh;background:#141b23;color:white;padding:8px;border-radius:12px;display:grid;gap:6px';
  const close=document.createElement('button');close.textContent='✕ Fechar apresentação';close.style.cssText='justify-self:end;background:#283444;color:white;border:1px solid #70869a;border-radius:7px;padding:8px;cursor:pointer';
  const player=document.createElement('estudio-player');player.style.cssText='display:block;height:min(82vh,850px)';player.setAttribute('src',manifestUrl);
  const previous=document.activeElement;
  const finish=()=>{player.stop();overlay.remove();document.removeEventListener('keydown',escape);previous?.focus?.();};
  const escape=(e)=>{if(e.key==='Escape')finish();};
  close.onclick=finish;overlay.onclick=(e)=>{if(e.target===overlay)finish();};
  dialog.append(close,player);overlay.append(dialog);document.body.append(overlay);document.addEventListener('keydown',escape);close.focus();
  return {close:finish,player};
}
