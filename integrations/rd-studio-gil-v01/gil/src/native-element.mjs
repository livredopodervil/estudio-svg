// Presentation adapter only. No editor, admin API, audio or file operations.
import {compile} from './model.mjs';
import {Timeline} from './timeline.mjs';
import {renderSVG} from './render-svg.mjs';
export function defineNative(tag,source){
 const doc=compile(source),duration=doc.spec.stage.duration;
 if(customElements.get(tag))return;
 class GILNative extends HTMLElement{
  #timeline=new Timeline(doc);#host;#raf=0;#epoch=0;#last=-Infinity;#observer;#motion;#visible=false;
  constructor(){super();const shadow=this.attachShadow({mode:'open'}),style=document.createElement('style');style.textContent=':host{display:block;contain:layout paint}div,svg{display:block;width:100%;height:100%}';this.#host=document.createElement('div');shadow.append(style,this.#host);}
  #draw(t){const xml=new DOMParser().parseFromString(renderSVG(this.#timeline.sample(t)).svg,'image/svg+xml'),svg=xml.documentElement;if(svg.localName!=='svg')throw Error('SVG inválido');if(!this.hasAttribute('opaque')){const bg=svg.firstElementChild;if(bg?.localName==='rect')bg.remove();}svg.setAttribute('aria-hidden','true');this.#host.replaceChildren(document.importNode(svg,true));this.dataset.frame=t.toFixed(3);}
  #stop=()=>{if(this.#raf)cancelAnimationFrame(this.#raf);this.#raf=0;};
  #tick=now=>{this.#raf=0;if(!this.isConnected||!this.#visible||document.hidden||this.#motion.matches)return;if(now-this.#last>=1000/15){this.#last=now;let t=(now-this.#epoch)/1000;this.#draw(this.hasAttribute('once')?Math.min(t,duration):t%duration);if(this.hasAttribute('once')&&t>=duration)return;}this.#raf=requestAnimationFrame(this.#tick);};
  #sync=()=>{this.#stop();if(this.#motion.matches){this.#draw(0);return;}if(this.isConnected&&this.#visible&&!document.hidden)this.#raf=requestAnimationFrame(this.#tick);};
  connectedCallback(){if(!this.hasAttribute('aria-label'))this.setAttribute('aria-hidden','true');this.#epoch=performance.now();this.#last=-Infinity;this.#motion=matchMedia('(prefers-reduced-motion: reduce)');this.#motion.addEventListener('change',this.#sync);document.addEventListener('visibilitychange',this.#sync);this.#draw(0);this.#observer=new IntersectionObserver(entries=>{this.#visible=entries[0].isIntersecting;this.#sync();});this.#observer.observe(this);}
  disconnectedCallback(){this.#stop();this.#observer?.disconnect();this.#motion?.removeEventListener('change',this.#sync);document.removeEventListener('visibilitychange',this.#sync);this.#visible=false;}
 }
 customElements.define(tag,GILNative);
}
