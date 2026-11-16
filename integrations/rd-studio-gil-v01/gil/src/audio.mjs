// Adaptador de áudio. O documento fornece cues; o navegador fornece relógio e saída.
export function soundPlan(doc,timeline,from=0){return doc.cues.filter(c=>c.start+c.duration>from).map(c=>{const n=timeline.sample(c.start).objects.find(o=>o.id===c.target),p=n.props;return {id:c.target,start:Math.max(0,c.start-from),offset:Math.max(0,from-c.start),duration:c.start+c.duration-Math.max(c.start,from),frequency:Math.min(1800,Math.max(40,p.frequency??440)),gain:Math.min(.17,Math.max(0,p.gain??.06))*n.opacity,wave:['sine','triangle','square','sawtooth'].includes(p.wave)?p.wave:'sine'};});}
export class AudioAdapter{
 #context=null;#active=[];#generation=0;
 async play(doc,timeline,from){this.stop();const generation=this.#generation;const C=globalThis.AudioContext??globalThis.webkitAudioContext;if(!C)throw Error('Web Audio indisponível');this.#context??=new C();await this.#context.resume();if(generation!==this.#generation)return false;const now=this.#context.currentTime+.06;
 for(const cue of soundPlan(doc,timeline,from)){const ctx=this.#context,osc=ctx.createOscillator(),gain=ctx.createGain();osc.type=cue.wave;osc.frequency.value=cue.frequency;osc.connect(gain);gain.connect(ctx.destination);const a=now+cue.start,b=a+cue.duration,ramp=Math.min(.035,cue.duration/3);gain.gain.setValueAtTime(0,a);gain.gain.linearRampToValueAtTime(cue.gain,a+ramp);gain.gain.setValueAtTime(cue.gain,b-ramp);gain.gain.linearRampToValueAtTime(0,b);osc.start(a);osc.stop(b);this.#active.push({osc,gain});osc.onended=()=>{osc.disconnect();gain.disconnect();this.#active=this.#active.filter(x=>x.osc!==osc);};}
 return true;}
 stop(){this.#generation++;for(const {osc,gain} of this.#active){try{osc.stop();}catch{}osc.disconnect();gain.disconnect();}this.#active=[];}
}
