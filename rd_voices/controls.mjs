/** Catálogo comum de vozes: roteiro, personagem e cena usam o MESMO componente.
 * Os locais de montagem e persistência são decididos pelo Estúdio existente.
 * Uso: mountVoicePicker(node,{scope:'character', value: actor.voice, onChange:v=>{actor.voice=v;save();}})
 */
export const EDGE_PRESETS = Object.freeze({
  neutro: [0,0,0], calmo: [-12,-4,-5], alegre: [12,8,0],
  solene: [-15,-6,3], tenso: [8,5,0], triste: [-18,-8,-6]
});

export function normalizeVoice(v) {
  if (typeof v === 'string') {
    for (const p of ['edge','browser','piper','kokoro']) {
      if (v.startsWith(p+':')) return {provider:p,voice_id:v.slice(p.length+1)};
    }
    return {provider:'legacy',voice_id:v};
  }
  if (!v || typeof v!=='object') throw Error('Voz inválida');
  const voice_id=String(v.voice_id||v.id||'');
  const provider=String(v.provider||'legacy');
  if (!voice_id) throw Error('Identificador de voz ausente');
  return {provider,voice_id:voice_id.startsWith(provider+':')?voice_id.slice(provider.length+1):voice_id};
}

export function resolveVoice({project={},scene=null,character=null,line=null}={}) {
  for (const item of [line,scene,character,project]) {
    if (item && (item.voice||item.voz)) return normalizeVoice(item.voice||item.voz);
  }
  throw Error('Voz não definida; fallback automático proibido');
}

export async function loadEdgeCatalog(endpoint='/api/rd-voices/catalog') {
  const r=await fetch(endpoint,{credentials:'same-origin'});
  if (!r.ok) throw Error(`Catálogo Edge HTTP ${r.status}`);
  const p=await r.json();
  if(!Array.isArray(p.voices)||p.count!==p.voices.length) throw Error('Catálogo Edge inconsistente');
  return p.voices;
}

export function getBrowserVoices(){
  if(!('speechSynthesis' in window)) return [];
  return window.speechSynthesis.getVoices().map(v=>({
    provider:'browser',voice_id:v.voiceURI,id:'browser:'+v.voiceURI,
    name:v.name,locale:v.lang,gender:null,personalities:[],
    browserLocal:v.localService
  }));
}

function el(tag, attrs={}, text='') {
  const node=document.createElement(tag);
  for (const [k,v] of Object.entries(attrs)) {
    if(k==='class') node.className=v;
    else if(k==='type'||k==='min'||k==='max'||k==='step'||k==='placeholder'||k==='title'||k==='value'||k==='aria-label') node.setAttribute(k,String(v));
  }
  if(text) node.textContent=text;
  return node;
}
const cap=(n,min,max)=>Math.min(max,Math.max(min,Number.isFinite(+n)?+n:0));
const opt=(value,text)=>new Option(text,value);

export async function mountVoicePicker(container, {
    scope='scene', value={}, extraVoices=[], onChange=()=>{},
    onPreviewOther=null, endpoint='/api/rd-voices/catalog'
  }={}) {
  if(!(container instanceof Element)) throw Error('Container não é Element');
  const initialVoice = value.provider && value.voice_id ? `${value.provider}:${value.voice_id}`
    : typeof value.voice === 'string' ? value.voice : typeof value === 'string' ? value : '';
  let selected=initialVoice;
  let voices=[], objectUrl=null, audio=null, currentUtterance=null;
  let prosody={rate_pct:0,pitch_hz:0,volume_pct:0,...(value.prosody||{})};
  let browser={rate:1,pitch:1,volume:1,...(value.browser||{})};
  let intention=value.intention||value.emotion||'neutro';
  const root=el('section',{class:'rd-voice-picker'});
  const filter=el('input',{type:'search',placeholder:'Buscar voz, idioma ou personalidade','aria-label':'Buscar voz'});
  const selector=el('select',{'aria-label':'Todas as vozes'});
  const refresh=el('button',{type:'button'},'Atualizar vozes Edge');
  const details=el('p',{class:'rd-voice-meta'});
  const params=el('div',{class:'rd-voice-params'});
  const fields={};
  const field=(label, name, {min,max,step=1,value:initial})=>{
    const wrapper=el('label');wrapper.append(el('span',{},label));
    const input=el('input',{type:'number',min,max,step,value:initial,'aria-label':label});
    fields[name]=input;wrapper.append(input);params.append(wrapper);return input;
  };
  field('Velocidade Edge (%)','rate_pct',{min:-90,max:100,value:prosody.rate_pct});
  field('Altura tonal Edge (Hz)','pitch_hz',{min:-100,max:100,value:prosody.pitch_hz});
  field('Volume Edge (%)','volume_pct',{min:-100,max:100,value:prosody.volume_pct});
  field('Velocidade browser (razão)','browser_rate',{min:0.1,max:3,step:0.1,value:browser.rate});
  field('Altura browser (razão)','browser_pitch',{min:0,max:2,step:0.1,value:browser.pitch});
  field('Volume browser (0–1)','browser_volume',{min:0,max:1,step:0.1,value:browser.volume});
  const intentionLabel=el('label');intentionLabel.append(el('span',{},'Intenção expressiva (aproximação, não estilo Edge)'));
  const intentionSelect=el('select',{'aria-label':'Intenção expressiva'});
  for(const p of Object.keys(EDGE_PRESETS))intentionSelect.append(opt(p,p));
  intentionSelect.value=intention;
  intentionLabel.append(intentionSelect);
  const preset=el('button',{type:'button'},'Aplicar aproximação à prosódia');
  const previewText=el('textarea',{placeholder:'Texto para ouvir a voz','aria-label':'Texto de teste'});
  previewText.value='Esta voz está sendo testada no Estúdio SVG.';
  const play=el('button',{type:'button'},'Ouvir');
  const stop=el('button',{type:'button'},'Parar');
  const status=el('p',{class:'rd-voice-status'});
  audio=el('audio');audio.controls=true;
  root.append(filter,selector,refresh,details,params,intentionLabel,preset,previewText,play,stop,audio,status);
  container.replaceChildren(root);

  const currentVoice=()=>voices.find(v=>`${v.provider}:${v.voice_id}`===selected);
  function publish(){
    prosody={rate_pct:cap(fields.rate_pct.value,-90,100),pitch_hz:cap(fields.pitch_hz.value,-100,100),volume_pct:cap(fields.volume_pct.value,-100,100)};
    browser={rate:cap(fields.browser_rate.value,0.1,3),pitch:cap(fields.browser_pitch.value,0,2),volume:cap(fields.browser_volume.value,0,1)};
    intention=intentionSelect.value;
    const v=currentVoice();
    if(!v)return;
    const config={provider:v.provider,voice_id:v.voice_id,prosody:{...prosody},browser:{...browser},intention,
                  nativeEmotionSupported:false};
    onChange(config,{scope,voice:v});
    root.dispatchEvent(new CustomEvent('rd-voice-change',{detail:{scope,config},bubbles:true}));
  }
  function redraw(){
    const q=filter.value.toLowerCase().trim();
    const shown=voices.filter(v=>!q||[v.name,v.locale,v.voice_id,...(v.personalities||[])].some(s=>String(s||'').toLowerCase().includes(q)));
    selector.replaceChildren(...shown.map(v=>opt(`${v.provider}:${v.voice_id}`,`${v.locale||'—'} · ${v.name||v.voice_id} · ${v.provider}`)));
    if(shown.some(v=>`${v.provider}:${v.voice_id}`===selected))selector.value=selected;
    else if(shown.length)selector.value=`${shown[0].provider}:${shown[0].voice_id}`;
    selector.disabled=!shown.length;
    details.textContent=`${voices.length} vozes totais · ${shown.length} encontradas`;
    showCapabilities();
  }
  function showCapabilities(){
    const v=voices.find(v=>`${v.provider}:${v.voice_id}`===selector.value);
    const provider=v?.provider;
    for (const k of ['rate_pct','pitch_hz','volume_pct'])fields[k].parentElement.hidden=provider!=='edge';
    for (const k of ['browser_rate','browser_pitch','browser_volume'])fields[k].parentElement.hidden=provider!=='browser';
    intentionLabel.hidden=preset.hidden=provider!=='edge';
    if(v){details.textContent=`${v.locale||''} · ${v.voice_id} · ${(v.personalities||[]).join(', ')||'Sem características declaradas'} · ${provider}`;}
  }
  function addBrowser(){
    const previous=selected;
    voices=[...voices.filter(v=>v.provider!=='browser'),...getBrowserVoices()];
    selected=previous;redraw();
  }
  selector.addEventListener('change',()=>{selected=selector.value;showCapabilities();publish();});
  filter.addEventListener('input',redraw);
  refresh.addEventListener('click',async()=>{
    refresh.disabled=true;status.textContent='Atualizando Edge na rede...';
    try{const r=await fetch('/api/rd-voices/refresh',{method:'POST',credentials:'same-origin'});
      const result=await r.json();if(!r.ok)throw Error(result.error||'Falha na atualização');
      voices=[...result.voices,...voices.filter(v=>v.provider!=='edge')];
      redraw();status.textContent=`Edge atualizado: ${result.count} vozes.`;
    }catch(e){status.textContent=String(e)+'; catálogo anterior preservado';}
    finally{refresh.disabled=false;}
  });
  intentionSelect.addEventListener('change',publish);
  for (const input of Object.values(fields))input.addEventListener('change',publish);
  preset.addEventListener('click',()=>{
    const [r,p,v]=EDGE_PRESETS[intentionSelect.value]||EDGE_PRESETS.neutro;
    fields.rate_pct.value=r;fields.pitch_hz.value=p;fields.volume_pct.value=v;publish();
  });
  play.addEventListener('click',async()=>{
    const v=voices.find(x=>`${x.provider}:${x.voice_id}`===selector.value);
    if (!v)return;
    const text=previewText.value.trim();if(!text){status.textContent='Digite um texto de teste';return;}
    play.disabled=true;stop.click();
    try{
      if(v.provider==='edge'){
        status.textContent='Gerando áudio Edge...';
        const res=await fetch('/api/rd-voices/synthesize',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({text,voice:selector.value,prosody:{rate_pct:+fields.rate_pct.value,pitch_hz:+fields.pitch_hz.value,volume_pct:+fields.volume_pct.value},intention:intentionSelect.value})});
        const out=await res.json();if(!res.ok)throw Error(out.error||'Falha Edge');
        // URL relativa à origem atual, não a URL externa arbitrária.
        audio.src=new URL(out.audio_url, location.origin).href;
        await audio.play();status.textContent=`Gerado ${v.voice_id}. Arquivo disponível no cache do Estúdio.`;
      } else if(v.provider==='browser'){
        const original=window.speechSynthesis.getVoices().find(x=>x.voiceURI===v.voice_id);
        if(!original)throw Error('Voz do navegador não disponível');
        currentUtterance=new SpeechSynthesisUtterance(text);currentUtterance.voice=original;
        currentUtterance.rate=+fields.browser_rate.value;currentUtterance.pitch=+fields.browser_pitch.value;
        currentUtterance.volume=+fields.browser_volume.value;
        speechSynthesis.speak(currentUtterance);status.textContent='Prévia do navegador (não exporta áudio)';
      } else if(onPreviewOther){
        await onPreviewOther({provider:v.provider,voice_id:v.voice_id},text);status.textContent='Prévia solicitada ao motor existente';
      } else throw Error('Prévia deste provedor deve usar o motor já existente do Estúdio');
    }catch(e){status.textContent=String(e)}finally{play.disabled=false;}
  });
  stop.addEventListener('click',()=>{audio.pause();audio.currentTime=0;if('speechSynthesis' in window)speechSynthesis.cancel();});
  try{voices=await loadEdgeCatalog(endpoint);}catch(e){status.textContent='Edge indisponível: '+e.message;}
  voices.push(...extraVoices.map(v=>({provider:v.provider,voice_id:v.voice_id,
    name:v.name||v.voice_id,locale:v.locale||'',personalities:v.personalities||[]})));
  addBrowser();
  if('speechSynthesis' in window)window.speechSynthesis.addEventListener?.('voiceschanged',addBrowser);
  return {root, getValue:()=>({provider:selector.value.split(':')[0],voice_id:selector.value.slice(selector.value.indexOf(':')+1),
    prosody:{...prosody},browser:{...browser},intention}),refreshBrowser:addBrowser,
    destroy:()=>{stop.click();if('speechSynthesis' in window)window.speechSynthesis.removeEventListener?.('voiceschanged',addBrowser);if(objectUrl)URL.revokeObjectURL(objectUrl);root.remove();}};
}
