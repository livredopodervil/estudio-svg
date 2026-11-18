// RD Studio 0.4 — parametric catalog, not an external asset collection.
// GIL uses only shape.circle, shape.rect, text and transformations already supported.
import {createTitleGIL} from './title-gil.mjs';
export const PALETTES=[
 ['oceano','#142938','#70d8db','#f6e0ad'],['tinta','#232329','#f2eee8','#ed9c69'],['sinal','#0e2119','#c9fa89','#7cc8af'],
 ['neon','#121329','#ff8cc6','#83dfe9'],['marfim','#eae2d4','#2d3037','#b56844'],['cosmos','#0a183a','#dce3ff','#b6a1fa'],
 ['terracota','#322020','#ffe0b4','#df8666'],['aquarela','#e1e7e4','#304e5d','#ee9e81'],['industrial','#273038','#f5d86a','#a3c4ce'],
 ['brutal','#ffea51','#191919','#dc3439'],['laboratorio','#082b2c','#a0eee2','#e3b27d'],['rosa','#32233a','#ffd7eb','#a3c0ff']
].map(([id,bg,fg,accent])=>({id,bg,fg,accent}));
export const MOTIFS=[
 ['linha','Linha'],['seta','Seta'],['seta-dupla','Seta dupla'],['tracejado','Linha tracejada'],['pontilhado','Linha pontilhada'],
 ['eixos','Eixos cartesianos'],['grade','Grade'],['barras','Gráfico de barras'],['seno','Senoide'],['coseno','Cosseno'],
 ['parabola','Parábola'],['espiral','Espiral'],['orbita','Órbita'],['atomo','Átomo'],['molecula','Molécula'],
 ['boneco','Boneco articulado'],['fluxo','Fluxograma'],['escada','Linha do tempo'],['raios','Raios'],['onda','Ondas'],
 ['rede','Rede de nós'],['marcadores','Marcadores'],['venn','Venn'],['moldura','Moldura']
];
export const SFX_FAMILIES=['clique','seleção','confirmar','erro','notificação','entrada','saída','whoosh','sopro','sino','sinal','impacto','pulso','subida','descida','passo','transição','digital'];
export const TITLE_STYLES=['editorial','lower','cinema','neon','minimal','signal','poster','caption'];
export const TITLE_ENTRIES=['cascade','typewriter','rise','fall','scatter','zoom','wave','fade','none'];
export const CATALOG=Object.freeze([
 ...MOTIFS.flatMap(([id,name])=>PALETTES.map(p=>({id:`geo:${id}:${p.id}`,type:'geometry',name:`${name} · ${p.id}`,motif:id,palette:p.id,license:'original'}))),
 ...TITLE_STYLES.flatMap(style=>TITLE_ENTRIES.map(entry=>({id:`title:${style}:${entry}`,type:'title',name:`Título ${style} · ${entry}`,style,entry,license:'original'}))),
 ...SFX_FAMILIES.flatMap(family=>Array.from({length:12},(_,variant)=>({id:`sfx:${family}:${variant+1}`,type:'sound',name:`${family} · variação ${variant+1}`,family,variant,license:'original-procedural'})))
]);
// Só as famílias aparecem no catálogo. Estilo, paleta, movimento e timbre são parâmetros.
// CATALOG permanece como índice legado para compatibilidade e regressões existentes.
export const CATALOG_FAMILIES=Object.freeze([
 ...MOTIFS.map(([id,name])=>({id:`geo:${id}`,type:'geometry',name,motif:id,license:'original'})),
 {id:'title:text',type:'title',name:'Texto / título animado',license:'original'},
 ...SFX_FAMILIES.map(family=>({id:`sfx:${family}`,type:'sound',name:`Som · ${family}`,family,license:'original-procedural'}))
]);
const f=n=>Math.round(n*10000)/10000;
export function createMotifGIL({motif='seta',palette='oceano',duration=6,label='UM CONCEITO'}={}){
 const p=PALETTES.find(a=>a.id===palette);if(!p||!MOTIFS.some(x=>x[0]===motif))throw Error('Geometria/paleta desconhecida');
 if(typeof label!=='string'||[...label].length>70)throw Error('Texto do motivo excessivo');
 const d=Number(duration);if(!Number.isFinite(d)||d<.5||d>60)throw Error('Duração inválida');
 const res=['resource camera camera {"z":15,"fov":45}','resource g group {}'];
 const obj=['object cam camera - {}','object conjunto g - {}'];let counter=0;
 function make(kind,geometry,x,y,rz=0){const n=counter++;const name='p'+n;res.push(`resource r${n} ${kind} ${JSON.stringify(geometry)}`);obj.push(`object ${name} r${n} conjunto ${JSON.stringify({x:f(x),y:f(y),rz:f(rz)})}`);}
 function circle(x,y,r=0.12,color=p.fg){make('shape.circle',{size:f(r*2),color,layer:3},x,y);}
 function line(x1,y1,x2,y2,w=.065,color=p.fg){const len=Math.hypot(x2-x1,y2-y1);if(len<1e-5)return;make('shape.rect',{width:f(len),height:f(w),color,layer:3},(x1+x2)/2,(y1+y2)/2,Math.atan2(y2-y1,x2-x1)*180/Math.PI);}
 function poly(points,close=false,color=p.fg){for(let i=1;i<points.length;i++)line(...points[i-1],...points[i],.06,color);if(close)line(...points.at(-1),...points[0],.06,color);}
 const pts=(n,fn)=>Array.from({length:n},(_,i)=>fn(i/(n-1),i));
 const arrow=(x1,y1,x2,y2,double=false)=>{line(x1,y1,x2,y2,.10,p.accent);const a=Math.atan2(y2-y1,x2-x1);const head=(x,y,dir)=>{line(x,y,x-.42*Math.cos(dir-.58),y-.42*Math.sin(dir-.58),.10,p.accent);line(x,y,x-.42*Math.cos(dir+.58),y-.42*Math.sin(dir+.58),.10,p.accent);};head(x2,y2,a);if(double)head(x1,y1,a+Math.PI);};
 switch(motif){
 case 'linha':line(-3,0,3,0,.11,p.accent);break;case 'seta':arrow(-3,0,3,0);break;case 'seta-dupla':arrow(-3,0,3,0,true);break;
 case 'tracejado':for(let x=-3;x<3;x+=.6)line(x,0,x+.32,0,.09,p.accent);break;
 case 'pontilhado':for(let x=-3;x<=3;x+=.27)circle(x,0,.075,p.accent);break;
 case 'eixos':arrow(-3,-2.1,3,-2.1);arrow(-2.5,-2.5,-2.5,2);break;
 case 'grade':for(let i=-4;i<=4;i++){line(i*.6,-2,i*.6,2,.028,p.accent);line(-2.4,i*.43,2.4,i*.43,.028,p.accent);}break;
 case 'barras':for(let i=0;i<6;i++)make('shape.rect',{width:.48,height:f(.65+(i*7%5)*.48),color:i%2?p.fg:p.accent,layer:3},-2.3+i*.92,-1.4+(i*7%5)*.24);break;
 case 'seno':poly(pts(35,t=>[-3+6*t,1.1*Math.sin(2*Math.PI*2*t)]),false,p.accent);break;
 case 'coseno':poly(pts(35,t=>[-3+6*t,1.1*Math.cos(2*Math.PI*2*t)]),false,p.accent);break;
 case 'parabola':poly(pts(30,t=>[-3+6*t,2.4*(2*t-1)**2-1.5]),false,p.accent);break;
 case 'espiral':poly(pts(45,t=>{const a=6*Math.PI*t,r=.15+2.15*t;return [r*Math.cos(a),r*Math.sin(a)];}),false,p.accent);break;
 case 'orbita':poly(pts(35,t=>[2.5*Math.cos(t*2*Math.PI),1.25*Math.sin(t*2*Math.PI)]),true,p.accent);circle(0,0,.32);break;
 case 'atomo':for(let j=0;j<3;j++)poly(pts(26,t=>{let a=2*Math.PI*t,b=j*Math.PI/3;return [2*Math.cos(a)*Math.cos(b)-1.1*Math.sin(a)*Math.sin(b),2*Math.cos(a)*Math.sin(b)+1.1*Math.sin(a)*Math.cos(b)];}),true,p.accent);circle(0,0,.22);break;
 case 'molecula':for(const [x,y] of [[-2,0],[-.9,1.2],[.8,.4],[2,-.8]])circle(x,y,.36,p.accent);poly([[-2,0],[-.9,1.2],[.8,.4],[2,-.8]]);break;
 case 'boneco':circle(0,1.7,.47);poly([[0,1.1],[0,-.4]]);poly([[-1.35,.55],[0,.45],[1.35,.55]]);poly([[-1,-2],[0,-.4],[1,-2]]);break;
 case 'fluxo':for(let i=0;i<3;i++)make('shape.rect',{width:1.25,height:.8,color:i%2?p.accent:p.fg,layer:3},-2.3+i*2.3,0);arrow(-1.55,0,-.65,0);arrow(.75,0,1.65,0);break;
 case 'escada':line(-3,0,3,0,.1,p.accent);for(let i=0;i<5;i++){circle(-2.5+i*1.25,0,.2);line(-2.5+i*1.25,0,-2.5+i*1.25,(i%2?-.8:.8),.045);}break;
 case 'raios':for(let i=0;i<20;i++){const a=i*2*Math.PI/20;line(.55*Math.cos(a),.55*Math.sin(a),2.9*Math.cos(a),2.1*Math.sin(a),.06,i%2?p.accent:p.fg);}break;
 case 'onda':for(let k=0;k<3;k++)poly(pts(35,t=>[-3+6*t,(k-1)*.75+.23*Math.sin(t*8*Math.PI+k)]),false,k===1?p.accent:p.fg);break;
 case 'rede':{const points=Array.from({length:9},(_,i)=>[2.6*Math.cos(i*2.4),1.8*Math.sin(i*1.7)]);for(let i=0;i<8;i++)for(let j=i+1;j<9;j++)if((i+j)%4===0)line(...points[i],...points[j],.035,p.accent);for(const xy of points)circle(...xy,.13);break;}
 case 'marcadores':for(let i=0;i<10;i++){const x=-2.5+(i%5)*1.25,y=1-(i/5|0)*2;circle(x,y,.14,i%3?p.fg:p.accent);}break;
 case 'venn':for(let j=-1;j<=1;j++)poly(pts(40,t=>[j*.75+1.35*Math.cos(2*Math.PI*t),1.35*Math.sin(2*Math.PI*t)]),true,j===0?p.accent:p.fg);break;
 case 'moldura':poly([[-3,-2.2],[3,-2.2],[3,2.2],[-3,2.2]],true,p.accent);for(let i=-1;i<=1;i++)line(-2.5,-1.5+i*.55,2.5,-1.5+i*.55,.04);break;
 }
 res.push(`resource title text ${JSON.stringify({text:label,fontSize:35,color:p.fg,layer:8})}`);obj.push('object rotulo title - {"y":-3.1}');
 // movement is deterministic in the shared GIL Timeline; do not animate audio here.
 const animation=`animate conjunto y ${JSON.stringify({keys:[[0,0],[d/2,.12],[d,0]],ease:'smooth'})}`;
 return `gil timeline 0.1 {\nstage ${JSON.stringify({width:1280,height:720,duration:d,background:p.bg,camera:'cam'})}\n${res.join('\n')}\n${obj.join('\n')}\n${animation}\n}\n`;
}
export function sourceFor(item,{duration=6,label='UM CONCEITO',palette,style,entry}={}){
 if(item.type==='geometry')return createMotifGIL({motif:item.motif,palette:palette||item.palette||'oceano',duration,label});
 if(item.type==='title')return createTitleGIL({text:label,style:style||item.style||'editorial',entry:entry||item.entry||'cascade',duration});
 throw Error('Este item não é um objeto GIL');
}
// PCM synthesis: original short samples, exportable as WAV for the EXISTING audio track importer.
// This intentionally does not create a second audio transport or synthesize speech.
export function soundSamples(item,{rate=22050}={}){
 if(item.type!=='sound'||!SFX_FAMILIES.includes(item.family))throw Error('Efeito inexistente');
 const v=Number(item.variant??0),family=item.family;if(!Number.isInteger(v)||v<0||v>11)throw Error('Variante sonora inválida');const seconds=.22+v*.035,length=Math.round(seconds*rate),pcm=new Float32Array(length);
 let seed=222+(v+1)*571+SFX_FAMILIES.indexOf(family)*173;const rnd=()=>{seed^=seed<<13;seed^=seed>>>17;seed^=seed<<5;return (seed>>>0)/4294967296*2-1;};
 const tone=(family==='sino'?730:family==='impacto'?130:family==='sopro'?280:family==='erro'?180:family==='whoosh'?225:350)+v*19;
 for(let i=0;i<length;i++){
  const t=i/rate,u=i/length,attack=Math.min(1,t/.008),envelope=(1-u)**(family==='sino'?1.5:family==='whoosh'?.8:2.5),hz=tone*(family==='subida'?.6+u:family==='descida'?1.5-u:family==='entrada'?.8+.3*u:1);
  const sine=Math.sin(2*Math.PI*(hz*t)),click=(family==='clique'||family==='passo'||family==='impacto'),noise=rnd();
  const sample=family==='sopro'||family==='whoosh'||family==='transição'?noise*.65+sine*.18:click?noise*.48+sine*.42:family==='digital'||family==='erro'?Math.sign(sine)*.55:family==='sino'?sine*.52+Math.sin(2*Math.PI*hz*1.5*t)*.20:sine*.6+noise*.11;
  pcm[i]=Math.max(-1,Math.min(1,attack*envelope*sample*.8));
 }
 return {pcm,rate};
}
export function wavBlob(item){const {pcm,rate}=soundSamples(item),buf=new ArrayBuffer(44+pcm.length*2),v=new DataView(buf);const str=(o,s)=>{for(let i=0;i<s.length;i++)v.setUint8(o+i,s.charCodeAt(i));};
 str(0,'RIFF');v.setUint32(4,36+pcm.length*2,true);str(8,'WAVE');str(12,'fmt ');v.setUint32(16,16,true);v.setUint16(20,1,true);v.setUint16(22,1,true);v.setUint32(24,rate,true);v.setUint32(28,rate*2,true);v.setUint16(32,2,true);v.setUint16(34,16,true);str(36,'data');v.setUint32(40,pcm.length*2,true);
 pcm.forEach((n,i)=>v.setInt16(44+i*2,Math.max(-32767,Math.min(32767,Math.round(n*32767))),true));return new Blob([buf],{type:'audio/wav'});
}
