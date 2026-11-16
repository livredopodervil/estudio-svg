import {invertAffineMatrix, identityMatrix} from './spatialseed.mjs';
const esc=v=>String(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&apos;'}[c]));
const f=v=>Number.isFinite(v)?Number(v.toFixed(4)):0;
const color=(v,d='#88c9dd')=>typeof v==='string'&&/^#[0-9a-f]{6}$/i.test(v)?v:d;
const bounded=(v,d,min,max)=>typeof v==='number'?Math.max(min,Math.min(max,v)):d;
const point=(m,[x,y,z])=>[m[0]*x+m[4]*y+m[8]*z+m[12],m[1]*x+m[5]*y+m[9]*z+m[13],m[2]*x+m[6]*y+m[10]*z+m[14]];
const subtract=(a,b)=>a.map((x,i)=>x-b[i]);const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];const dot=(a,b)=>a.reduce((s,x,i)=>s+x*b[i],0);const unit=a=>{const len=Math.hypot(...a)||1;return a.map(x=>x/len);};
const shade=(c,k)=>'#'+[1,3,5].map(i=>Math.round(Math.min(255,parseInt(c.slice(i,i+2),16)*k)).toString(16).padStart(2,'0')).join('');
export const SUPPORTED=Object.freeze(['group','camera','light.directional','mesh.box','shape.circle','shape.rect','image.svg','text','overlay.fade','audio.tone']);
export const ASSETS=Object.freeze({'helix.svg':'assets/helix.svg','snowflake.svg':'assets/snowflake.svg'});
export function renderSVG(frame,{assetResolver=name=>ASSETS[name]??null,selected=null}={}){
 const {width:w,height:h,background,camera}=frame.stage, pp=h/8, cameraNode=frame.objects.find(o=>o.id===camera); const view=invertAffineMatrix(cameraNode?.matrix??identityMatrix()), focal=h/(2*Math.tan(bounded(cameraNode?.props.fov,45,15,120)*Math.PI/360));
 const light=frame.objects.find(o=>o.kind==='light.directional'); const lightDir=unit(light?[light.matrix[12],light.matrix[13],light.matrix[14]]:[-3,4,6]);const strength=bounded(light?.props.intensity,.9,0,3);
 const draw=[],missing=[];const wrap=(o,s)=>`<g data-object="${esc(o.id)}" opacity="${f(o.opacity)}"${o.id===selected?' stroke="#f9f0be" stroke-width="1.8"':''}>${s}</g>`;
 function add(o,markup,depth=0){draw.push({level:o.props.layer,depth,index:draw.length,markup:wrap(o,markup)});}
 const project=p=>{const [x,y,z]=point(view,p);return z<-.08?{x:w/2+focal*x/-z,y:h/2-focal*y/-z,z}:null;};
 for(const o of frame.objects){const p=o.props,m=o.matrix,kind=o.kind,c=color(p.color),size=bounded(p.size,1,.001,100);if(!SUPPORTED.includes(kind)){missing.push(`${o.id}: ${kind}`);continue;}if(o.opacity<=0)continue;
  if(kind==='mesh.box'){
   const a=size/2,vertices=[[-a,-a,-a],[a,-a,-a],[a,a,-a],[-a,a,-a],[-a,-a,a],[a,-a,a],[a,a,a],[-a,a,a]].map(v=>point(m,v));const faces=[[0,3,2,1],[4,5,6,7],[0,4,7,3],[1,2,6,5],[0,1,5,4],[3,7,6,2]];
   for(const face of faces){const vs=face.map(i=>vertices[i]),normal=unit(cross(subtract(vs[1],vs[0]),subtract(vs[2],vs[0]))),center=vs.reduce((s,v)=>s.map((x,i)=>x+v[i]/4),[0,0,0]);if(dot(normal,subtract([cameraNode.matrix[12],cameraNode.matrix[13],cameraNode.matrix[14]],center))<=0)continue;const ps=vs.map(project);if(ps.some(v=>!v))continue;const fill=shade(c,.32+strength*.68*Math.max(0,dot(normal,lightDir)));add(o,`<polygon points="${ps.map(q=>`${f(q.x)},${f(q.y)}`).join(' ')}" fill="${fill}" stroke="${o.id===selected?'#fff1ac':'#d3efff'}" stroke-opacity=".6" stroke-width="1"/>`,ps.reduce((n,q)=>n+q.z/4,0));}
  }else if(['shape.circle','shape.rect','image.svg','text'].includes(kind)){
   const transform=`matrix(${[m[0],-m[1],-m[4],m[5],w/2+m[12]*pp,h/2-m[13]*pp].map(f).join(' ')})`;let s='';
   if(kind==='shape.circle')s=`<circle r="${f(size*pp/2)}" fill="${c}"/>`;
   if(kind==='shape.rect'){const a=bounded(p.width,size,.01,100)*pp,b=bounded(p.height,size,.01,100)*pp;s=`<rect x="${f(-a/2)}" y="${f(-b/2)}" width="${f(a)}" height="${f(b)}" rx="4" fill="${c}"/>`;}
   if(kind==='text')s=`<text text-anchor="middle" dominant-baseline="middle" font-family="sans-serif" font-size="${f(bounded(p.fontSize,28,8,150))}" font-weight="600" fill="${c}">${esc(p.text??'')}</text>`;
   if(kind==='image.svg'){const href=Object.hasOwn(ASSETS,p.asset)?assetResolver(p.asset):null;if(!href){missing.push(`${o.id}: asset indisponível`);continue;}const dim=size*pp;s=`<image href="${esc(href)}" x="${f(-dim/2)}" y="${f(-dim/2)}" width="${f(dim)}" height="${f(dim)}"/>`;}
   add(o,`<g transform="${transform}">${s}</g>`);
  }else if(kind==='overlay.fade'){add(o,`<rect width="${w}" height="${h}" fill="${c}" pointer-events="none"/>`);}
 }
 draw.sort((a,b)=>a.level-b.level||a.depth-b.depth||a.index-b.index);
 return {svg:`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${w} ${h}" width="${w}" height="${h}" role="img" aria-label="Prévia GIL"><rect width="${w}" height="${h}" fill="${background}"/>${draw.map(x=>x.markup).join('')}</svg>`,missing};
}
