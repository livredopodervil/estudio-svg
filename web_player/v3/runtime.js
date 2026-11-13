
/* ESTUDIO_SVG_RUNTIME_V3_ALPHA4_PORT_V1
 * Runtime vetorial local: projeção SVG da cena espacial e timeline determinística.
 * Sem GSAP/WebGL. Não consulta /api/preview e não usa sequências de PNG.
 * Referência funcional: spatial_scene.py, timeline_easing.py, graphics.py na V3 Alpha 4.
 */
(() => {
  'use strict';
  const NS = 'http://www.w3.org/2000/svg';
  const PI = Math.PI, clamp=(n,a=0,b=1)=>Math.max(a,Math.min(b,n));
  const num=(n,d=0)=>Number.isFinite(Number(n))?Number(n):d;
  const fmt=n=>Number(n).toFixed(2);
  const safeColor=c=>/^#[0-9a-fA-F]{6}$/.test(String(c))?String(c):'#64bcdb';
  const safeId=s=>/^[A-Za-z_][A-Za-z0-9_-]{0,39}$/.test(String(s))?String(s):'objeto';
  function ease(t,name='suave'){
    t=clamp(t); if(name==='linear')return t;
    if(name==='suave')return t*t*(3-2*t);
    if(/^power[123]\.(in|out|inOut)$/.test(name)){
      const power=Number(name[5])+1;
      if(name.endsWith('.inOut'))return t<.5?2**(power-1)*t**power:1-((-2*t+2)**power)/2;
      if(name.endsWith('.out'))return 1-(1-t)**power;
      return t**power;
    }
    if(name==='sine.in')return 1-Math.cos(t*PI/2);
    if(name==='sine.out')return Math.sin(t*PI/2);
    if(name==='sine.inOut')return -(Math.cos(PI*t)-1)/2;
    if(name==='expo.out')return t>=1?1:1-2**(-10*t);
    if(name==='back.out'){const v=t-1;return 1+2.70158*v**3+1.70158*v**2;}
    if(name==='bounce.out'){
      if(t<1/2.75)return 7.5625*t*t;
      if(t<2/2.75){t-=1.5/2.75;return 7.5625*t*t+.75;}
      if(t<2.5/2.75){t-=2.25/2.75;return 7.5625*t*t+.9375;}
      t-=2.625/2.75;return 7.5625*t*t+.984375;
    }
    return t*t*(3-2*t);
  }
  function progress(a,p){
    const start=num(a?.inicio),end=num(a?.fim,1),mode=a?.easing||'suave';
    if(p<=start)return ease(0,mode);
    const cycles=clamp(Math.floor(num(a?.repeticoes))+1,1,21),yoyo=Boolean(a?.yoyo);
    if(p>=end)return ease(yoyo&&cycles%2===0?0:1,mode);
    const total=clamp((p-start)/Math.max(1e-9,end-start))*cycles;
    const i=Math.min(cycles-1,Math.floor(total));
    let x=total-i; if(yoyo&&i%2)x=1-x;
    return ease(x,mode);
  }
  const add=(a,b)=>a.map((v,i)=>v+b[i]);
  const sub=(a,b)=>a.map((v,i)=>v-b[i]);
  const mul=(a,s)=>a.map(v=>v*s);
  const dot=(a,b)=>a.reduce((v,x,i)=>v+x*b[i],0);
  const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
  const unit=a=>mul(a,1/Math.max(1e-10,Math.sqrt(dot(a,a))));
  function rotated(v,angles){
    let [x,y,z]=v;
    for(let axis=0;axis<3;axis++){
      const a=num(angles[axis])*PI/180,c=Math.cos(a),s=Math.sin(a);
      if(axis===0){const yy=y*c-z*s;z=y*s+z*c;y=yy;}
      else if(axis===1){const xx=x*c+z*s;z=-x*s+z*c;x=xx;}
      else{const xx=x*c-y*s;y=x*s+y*c;x=xx;}
    }
    return [x,y,z];
  }
  const rgb=(color,factor)=>{
    const c=safeColor(color),v=[1,3,5].map(i=>Math.floor(clamp(parseInt(c.slice(i,i+2),16)*factor,0,255)));
    return '#'+v.map(x=>x.toString(16).padStart(2,'0')).join('');
  };
  const cubeV=[[-1,-1,-1],[1,-1,-1],[1,1,-1],[-1,1,-1],[-1,-1,1],[1,-1,1],[1,1,1],[-1,1,1]];
  const cubeF=[[0,3,2,1],[4,5,6,7],[0,4,7,3],[1,2,6,5],[3,7,6,2],[0,1,5,4]];
  const pyrV=[[-1,-1,-1],[1,-1,-1],[1,-1,1],[-1,-1,1],[0,1.4,0]];
  const pyrF=[[0,3,2,1],[0,1,4],[1,2,4],[2,3,4],[3,0,4]];
  const nseg=16;
  const cylinderV=[-1,1].flatMap(y=>Array.from({length:nseg},(_,i)=>[Math.cos(2*PI*i/nseg),y,Math.sin(2*PI*i/nseg)]));
  const cylinderF=[Array.from({length:nseg},(_,i)=>nseg-1-i),Array.from({length:nseg},(_,i)=>nseg+i),
    ...Array.from({length:nseg},(_,i)=>[i,(i+1)%nseg,(i+1)%nseg+nseg,i+nseg])];
  const coneV=[...Array.from({length:nseg},(_,i)=>[Math.cos(2*PI*i/nseg),-1,Math.sin(2*PI*i/nseg)]),[0,1,0]];
  const coneF=[Array.from({length:nseg},(_,i)=>nseg-1-i),...Array.from({length:nseg},(_,i)=>[i,(i+1)%nseg,nseg])];
  const shapes={cubo:[cubeV,cubeF],piramide:[pyrV,pyrF],cilindro:[cylinderV,cylinderF],cone:[coneV,coneF]};
  function spatialMarkup(spatial,p,height=720){
    if(!spatial || !Array.isArray(spatial.objetos))return '';
    const tracks=Array.isArray(spatial.animacoes)?spatial.animacoes:[];
    const cam={...(spatial.camera||{})};
    for(const a of tracks)if(a.alvo==='__camera__' && ['azimute','elevacao','distancia'].includes(a.propriedade))
      cam[a.propriedade]=num(a.de)+(num(a.ate)-num(a.de))*progress(a,p);
    const yaw=num(cam.azimute,28)*PI/180,pitch=num(cam.elevacao,18)*PI/180;
    const target=Array.isArray(cam.alvo)&&cam.alvo.length===3?cam.alvo.map(v=>num(v)): [0,0,0];
    const d=num(cam.distancia,9);
    const cpos=add(target,[d*Math.cos(pitch)*Math.sin(yaw),d*Math.sin(pitch),d*Math.cos(pitch)*Math.cos(yaw)]);
    const forward=unit(sub(target,cpos)),right=unit(cross(forward,[0,1,0])),up=cross(right,forward);
    const project=point=>{
      const v=sub(point,cpos),x=dot(v,right),y=dot(v,up),z=dot(v,forward);
      return z<.1?null:[640+1100*x/z,height*.55-1100*y/z,z];
    };
    const out=[];
    for(let n=-4;n<=4;n++){
      for(const [a,b] of [[ [n,-1.7,-4],[n,-1.7,4] ],[ [-4,-1.7,n],[4,-1.7,n] ]]){
        const pa=project(a),pb=project(b);
        if(pa&&pb)out.push(`<path d="M${fmt(pa[0])} ${fmt(pa[1])} L${fmt(pb[0])} ${fmt(pb[1])}" stroke="#8696b4" stroke-opacity=".18" stroke-width="2"/>`);
      }
    }
    const objects=Object.fromEntries(spatial.objetos.slice(0,32).map(o=>[String(o.id),o]));
    const poses={};
    for(const o of spatial.objetos.slice(0,32)){
      const position=Array.isArray(o.posicao)?o.posicao.map(x=>num(x)): [0,0,0];
      const rotation=Array.isArray(o.rotacao)?o.rotacao.map(x=>num(x)): [0,0,0];
      let scale=num(o.escala,1);
      for(const a of tracks)if(a.alvo===o.id){
        const value=num(a.de)+(num(a.ate)-num(a.de))*progress(a,p),prop=a.propriedade;
        if(prop==='escala')scale=value;
        else if(/^posicao_[xyz]$/.test(prop))position['xyz'.indexOf(prop.at(-1))]=value;
        else if(/^rotacao_[xyz]$/.test(prop))rotation['xyz'.indexOf(prop.at(-1))]=value;
      }
      poses[o.id]=[position,rotation,scale];
    }
    const chain=o=>{
      const acc=[],seen=new Set();let item=o;
      while(item && !seen.has(item.id) && acc.length<=32){acc.push(item);seen.add(item.id);item=item.pai?objects[item.pai]:null;}
      return acc;
    };
    const worldPoint=(o,v)=>chain(o).reduce((point,item)=>{
      const [pos,rot,scale]=poses[item.id];return add(rotated(mul(point,scale),rot),pos);
    },v);
    const globalScale=o=>chain(o).reduce((s,item)=>s*poses[item.id][2],1);
    const polys=[],lightDir=unit([-.35,.8,.55]);
    for(const o of spatial.objetos.slice(0,32)){
      if(o.visivel===false || o.tipo==='grupo')continue;
      const color=safeColor(o.cor);
      if(o.tipo==='esfera'){
        const point=project(worldPoint(o,[0,0,0]));
        if(point){const [x,y,z]=point,r=1100*globalScale(o)/z;
          if(r>0){const id=safeId(o.id);
            out.push(`<defs><radialGradient id="spg-${id}" cx="30%" cy="25%"><stop stop-color="${rgb(color,1.65)}"/><stop offset=".7" stop-color="${color}"/><stop offset="1" stop-color="${rgb(color,.35)}"/></radialGradient></defs>`);
            polys.push([z,`<circle cx="${fmt(x)}" cy="${fmt(y)}" r="${fmt(r)}" fill="url(#spg-${id})" stroke="${rgb(color,1.2)}" stroke-width="2"/>`]);
          }
        }
        continue;
      }
      const shape=shapes[o.tipo];if(!shape)continue;
      const [vertices,faces]=shape,world=vertices.map(v=>worldPoint(o,v));
      for(const face of faces){
        const coords=face.map(j=>project(world[j]));if(coords.some(p=>!p))continue;
        const [a,b,c]=face.slice(0,3).map(j=>world[j]);
        const normal=unit(cross(sub(b,a),sub(c,a))),light=Math.max(.24,.52+.43*dot(normal,lightDir));
        const points=coords.map(v=>`${fmt(v[0])},${fmt(v[1])}`).join(' ');
        const fill=rgb(color,light);
        polys.push([coords.reduce((s,v)=>s+v[2],0)/coords.length,`<polygon points="${points}" fill="${fill}" stroke="${rgb(color,.72)}" stroke-width="2" stroke-linejoin="round"/>`]);
      }
    }
    polys.sort((a,b)=>b[0]-a[0]);
    out.push(...polys.map(v=>v[1]));
    return out.join('');
  }
  function updateSpatial(world,scene,p,h){
    if(!world)return;
    world.innerHTML=spatialMarkup(scene,p,h);
  }
  function updateProcedural(svg,scene,p){
    if(!svg || !scene)return;
    const view=svg.viewBox?.baseVal,h=view?.height||720;
    const ty=scene.tipo||'',content=svg.querySelector('#__conteudo__');
    const e=scene.movimento==='linear'?p:p*p*(3-2*p);
    // Decorações: o mesmo relógio normalizado serve para replay, seek e pausa.
    const rootEllipses=svg.querySelectorAll(':scope > ellipse');
    if(rootEllipses.length){rootEllipses[0].setAttribute('cx',String(1070+52*Math.sin(p*PI*2)));
      rootEllipses[0].setAttribute('cy',String(350+30*Math.sin(p*PI)));}
    const footer=svg.querySelectorAll('rect[height="6"]');
    if(footer.length>=2)footer[footer.length-1].setAttribute('width',String(1120*p));
    if(!content)return;
    if(ty==='espacial'){
      updateSpatial(content.querySelector('#spatial-world'),scene.espacial,p,h);
    }else if(ty==='globo'){
      const orbits=content.querySelectorAll('ellipse');
      orbits.forEach((el,i)=>{if(i<4){const circle=content.querySelector('circle');
        if(circle){const cx=circle.getAttribute('cx'),cy=circle.getAttribute('cy');
          el.setAttribute('transform',`rotate(${fmt(p*24)} ${cx} ${cy})`);}}});
      content.querySelectorAll('text').forEach((el,i)=>el.setAttribute('opacity',String(clamp(p*7-i*.25))));
    }else if(ty==='barras'){
      content.querySelectorAll('rect[rx="9"]').forEach(el=>{
        if(!el.dataset.heightFull){el.dataset.heightFull=el.getAttribute('height');el.dataset.bottom=String(num(el.getAttribute('y'))+num(el.getAttribute('height')));}
        const height=num(el.dataset.heightFull)*e;
        el.setAttribute('height',String(height));el.setAttribute('y',String(num(el.dataset.bottom)-height));
      });
    }else if(ty==='numero'){
      const rects=content.querySelectorAll('rect[rx="10"]');
      if(rects.length>=2)rects[rects.length-1].setAttribute('width',String(920*e));
      const txt=content.querySelector('text');if(txt)txt.setAttribute('opacity',String(.15+.85*e));
    }else if(ty==='cartoes'){
      const rects=content.querySelectorAll('rect[rx="20"]');
      rects.forEach((el,i)=>el.setAttribute('opacity',String(.22+Math.min(.22,Math.max(0,(p*rects.length-i)*.3)))));
    }else if(ty==='linha'){
      const line=content.querySelector('polyline');
      if(line){
        const points=line.points,len=points?.numberOfItems||0;
        if(len>=2){
          const lengths=[];let total=0;
          for(let i=1;i<len;i++){const a=points.getItem(i-1),b=points.getItem(i);
            lengths.push(Math.hypot(b.x-a.x,b.y-a.y));total+=lengths.at(-1);}
          const pos=clamp(p)*(len-1),whole=Math.min(len-1,Math.floor(pos));
          let partial=lengths.slice(0,whole).reduce((s,x)=>s+x,0);
          if(whole<len-1)partial+=lengths[whole]*(pos-whole);
          line.setAttribute('stroke-dasharray',String(total));
          line.setAttribute('stroke-dashoffset',String(total-partial));
        }
      }
      const dots=content.querySelectorAll('circle[r="7"]');
      dots.forEach((dot,i)=>dot.setAttribute('opacity',i<=p*Math.max(0,dots.length-1)+.01?'1':'0'));
    }else if(ty==='arvore'){
      content.querySelectorAll('path[stroke-linecap="round"]').forEach(path=>{
        const level=Math.round(num(path.getAttribute('stroke-width'))/3);
        if(level<1||level>6)return;
        const q=clamp(p*7-(6-level));
        let length=num(path.dataset.length,-1);
        if(length<0){try{length=path.getTotalLength();}catch(_){length=0;}path.dataset.length=String(length);}
        path.setAttribute('stroke-dasharray',String(length));
        path.setAttribute('stroke-dashoffset',String(length*(1-q)));
        path.setAttribute('opacity',q>0?'1':'0');
      });
    }else if(ty==='svg'){
      const group=[...content.children].find(el=>el.localName==='g' && (el.getAttribute('transform')||'').includes('translate(640,360) scale('));
      if(group){const t=group.getAttribute('transform');
        group.setAttribute('transform',t.replace(/scale\([^)]*\)/,`scale(${(.86+.14*e).toFixed(3)})`));}
    }
  }
  const exported={ease,progress,spatialMarkup,updateSpatial,updateProcedural};
  if(typeof window!=='undefined')window.EstudioV3=exported;
  if(typeof module!=='undefined' && module.exports)module.exports=exported;
})();
