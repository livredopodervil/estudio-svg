/* Estúdio SVG V3.4 — narração e locales. Código original; sem dependências. */
(function (global) {
  'use strict';
  const okLocale = v => /^[a-z]{2,3}(?:-[A-Za-z0-9]{2,8}){0,2}$/.test(String(v||''));
  const clamp = (v,min,max) => Math.max(min,Math.min(max,Number(v)||min));
  function localeText(scene, i, locale, packs, baseLocale) {
    const pack = packs?.[locale];
    const item = pack?.scenes?.[scene.id] || pack?.scenes?.[String(i)] || null;
    if(item && typeof item.voice_text === 'string' && item.voice_text.trim())
      return {text:item.voice_text.trim(), lang:locale, translated:true};
    const original = String(scene.audio?.voice_text || scene.fala || '').trim();
    return {text:original,lang:baseLocale,translated:false};
  }
  function chooseVoice(voices, lang, preferred) {
    const vv = Array.from(voices||[]);
    if(preferred) {const x=vv.find(v=>v.voiceURI===preferred || v.name===preferred);if(x && x.lang.toLowerCase().startsWith(lang.split('-')[0].toLowerCase()))return x;}
    return vv.find(v=>v.lang.toLowerCase()===lang.toLowerCase()) ||
      vv.find(v=>v.lang.toLowerCase().split('-')[0]===lang.toLowerCase().split('-')[0]) || null;
  }
  class Narrator {
    constructor({synth=null, createAudio=null, status=()=>{}}={}) {
      this.synth=synth;this.createAudio=createAudio;
      this.status=status;this.audio=null;this.utterance=null;this.busy=false;
      this.epoch=0;this.mode='browser';this.rate=1.2;this.volume=1;this.onDone=()=>{};
    }
    setMode(mode) {if(!['browser','recorded','auto','none'].includes(mode))throw new Error('Modo de narração inválido');this.mode=mode;this.stop();}
    setRate(rate){this.rate=clamp(rate,.6,2.2);if(this.audio)this.audio.playbackRate=this.rate;}
    setVolume(volume){this.volume=clamp(volume,0,1);if(this.audio)this.audio.volume=this.volume;}
    stop(){this.epoch++;this.busy=false;this.onDone=()=>{};
      if(this.audio){this.audio.pause();this.audio.onended=null;this.audio.onerror=null;this.audio.removeAttribute('src');this.audio=null;}
      this.utterance=null;if(this.synth)this.synth.cancel();}
    pause(){if(this.audio)this.audio.pause();else if(this.utterance)this.synth?.pause();}
    async resume(){if(this.audio){try{await this.audio.play();}catch(e){this.status('Áudio bloqueado: toque para reproduzir.');}} else if(this.utterance)this.synth?.resume();}
    speak({text='',lang='pt-BR',file='',voices=[],voiceName='',onDone=()=>{}}={}) {
      this.stop();this.onDone=onDone;
      if(this.mode==='none')return;
      const token=this.epoch;
      const done=()=>{if(token!==this.epoch)return;this.busy=false;this.onDone();};
      const useRecorded=this.mode==='recorded'||(this.mode==='auto'&&!!file);
      if(useRecorded){
        if(!file || !this.createAudio){this.status('Não existe gravação para a cena/idioma selecionados.');return;}
        const a=this.createAudio();this.audio=a;a.src=file;a.playbackRate=this.rate;a.volume=this.volume;
        a.onended=done;a.onerror=()=>{this.status('Erro no arquivo de áudio.');done();};this.busy=true;
        try{const p=a.play();if(p?.catch)p.catch(e=>{if(token===this.epoch){this.status('Reprodução bloqueada: '+e.message);done();}});}catch(e){this.status('Não foi possível reproduzir: '+e.message);done();}
        return;
      }
      if(!text.trim()){this.status('Sem texto de narração.');return;}
      if(!this.synth || typeof global.SpeechSynthesisUtterance!=='function'){this.status('Voz do navegador indisponível.');return;}
      const u=new global.SpeechSynthesisUtterance(text);u.lang=lang;u.rate=this.rate;u.volume=this.volume;
      u.voice=chooseVoice(voices,lang,voiceName);u.onend=done;
      u.onerror=e=>{if(e.error!=='canceled'&&e.error!=='interrupted')this.status('Erro de voz: '+e.error);done();};
      this.utterance=u;this.busy=true;
      try{this.synth.speak(u);}catch(e){this.status('Falha na síntese: '+e.message);done();}
    }
  }
  async function fetchPack(lang, fetcher=global.fetch) {
    if(!okLocale(lang))throw new Error('Locale inválido');
    const response=await fetcher('./locales/'+encodeURIComponent(lang)+'.json');
    if(!response.ok) return null;
    const data=await response.json();
    if(data.locale!==lang || !data.scenes || typeof data.scenes!=='object')throw new Error('Pacote de idioma inválido');
    return data;
  }
  global.StudioV34={Narrator,chooseVoice,localeText,fetchPack,okLocale};
})(typeof window!=='undefined'?window:globalThis);
