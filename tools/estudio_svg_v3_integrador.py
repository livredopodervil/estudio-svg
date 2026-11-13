#!/usr/bin/env python3
"""Estúdio SVG V3: runtime vetorial espacial + timeline Alpha 4 para stage Termux.

- Não gera PNGs, não mexe em main, não executa git add/commit/push.
- Usa o graphics.visualize EXISTENTE para os SVGs de base com wrappers de animação.
- Copia e amplia a versão V2 do player, conservando narração e pivô.
- Coloca a experiência em stage/vetorial-v3, sem sobrescrever /vetorial V2.
- Link opcional, auditável e reversível, para web/index.html da branch experimental.

Simulação (padrão): python SCRIPT.py --repo "$PWD" --stage "$HOME/estudio_player_stage"
Aplicação:         python SCRIPT.py --repo "$PWD" --stage "$HOME/estudio_player_stage" --apply --editor-link
Reversão:         python SCRIPT.py --repo "$PWD" --stage "$HOME/estudio_player_stage" --revert
"""
from __future__ import annotations
import argparse
import base64
import copy
import hashlib
import html
import importlib
import inspect
import json
import mimetypes
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET

PAGE_MARK='<!-- ESTUDIO_SVG_VETORIAL_V3_PORT -->'
V2_MARK='/* ESTUDIO_SVG_VETORIAL_AUDIO_PIVO_V2 */'
PORTAL_MARK='id="vetorial-v3-link"'
EDITOR_MARK='id="studio-v3-vetorial-link"'
RUNTIME_JS = r"""
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

"""

# Cada patch verifica correspondência exata; diante de outro código, interrompe antes de escrever.
JS_CHANGES = [
('''function ease(t,mode){return mode==='linear'?t:t*t*(3-2*t);}''',
 '''function ease(t,mode){return window.EstudioV3.ease(t,mode);}'''),
('''  for(const a of project.cenas[index].animacoes||[]){
    const dest=bases.get(String(a.alvo)); if(!dest)continue;
    const begin=val(a,'inicio'),end=val(a,'fim',1),k=ease(clamp((p-begin)/Math.max(0.000001,end-begin)),a.easing);''',
 '''  const animations=[];
  for(const a of project.cenas[index].animacoes||[]){
    const targets=Array.isArray(a.alvos)?a.alvos:[a.alvo],offset=val(a,'intervalo');
    for(let j=0;j<targets.length;j++){
      const begin=Math.min(1,val(a,'inicio')+j*offset),end=Math.min(1,val(a,'fim',1)+j*offset);
      if(end>begin)animations.push({...a,alvo:targets[j],inicio:begin,fim:end});
    }
  }
  for(const a of animations){
    const dest=bases.get(String(a.alvo)); if(!dest)continue;
    const k=window.EstudioV3.progress(a,p);'''),
('''  // Animação de entrada via CSS, mantendo o mesmo SVG na memória durante a cena.
  svg.style.opacity=String(clamp(p/.06));''',
 '''  window.EstudioV3.updateProcedural(svg,project.cenas[index],p);
  // Mesma cena permanece no DOM, sem solicitação de frames ao servidor.
  svg.style.opacity=String(clamp(p/.06));'''),
('''    out('Motor vetorial independente · '+project.cenas.length+' cenas · sem PNGs e sem /api/preview. '+
      'Animações procedurais do gerador Python ainda não foram totalmente migradas.');''',
 '''    out('Player Web vetorial V3 · '+project.cenas.length+' cenas · projeção espacial e timeline no navegador.');'''),
]
HTML_CHANGES = [
('''<script src="./player.js?v=2"></script>''',
 '''<script src="./runtime.js?v=3"></script><script src="./player.js?v=3"></script>'''),
('''Estúdio SVG · Player vetorial experimental''',
 '''Estúdio SVG · Player vetorial V3 experimental'''),
]


def exact_replace(text,changes,label):
    for old,new in changes:
        count=text.count(old)
        if count!=1:
            raise RuntimeError(f'{label}: patch exige exatamente 1 ocorrência ({count}): {old[:60]!r}. Preservado.')
        text=text.replace(old,new,1)
    return text


def atomic_text(path,text):
    tmp=path.with_name('.'+path.name+'.player-v3-tmp')
    if tmp.exists():raise RuntimeError('Arquivo temporário preexistente: '+str(tmp))
    try:
        tmp.write_text(text,'utf-8')
        os.replace(tmp,path)
    finally:
        if tmp.exists():tmp.unlink()


def parity_check(repo, project, runtime, height):
    """Compara a geometria espacial do JS com o renderizador Python do checkout real.

    Verifica posições SVG (grade, polígonos e esferas), sem exigir igualdade textual
    ou assumir que os parâmetros de cor e fontes sejam idênticos em navegadores.
    """
    scenes=[c['espacial'] for c in project['cenas'] if c.get('tipo')=='espacial'][:4]
    if not scenes:return 'Sem cenas espaciais no projeto.',False
    node=shutil.which('node')
    if not node:return 'Sem Node.js: paridade JS/Python não verificada.',False
    try:
        ref=importlib.import_module('spatial_scene')
    except ImportError:
        return 'Módulo spatial_scene não disponível; paridade não verificada.',False
    js_code=("const fs=require('fs'),v=require(process.argv[1]);"
        "const d=JSON.parse(fs.readFileSync(0,'utf8'));"
        "process.stdout.write(JSON.stringify(d.scenes.map(s=>d.times.map(t=>v.spatialMarkup(s,t,d.height))))); ")
    samples=[0,.25,.51,.83,1]
    payload={'scenes':scenes,'times':samples,'height':height}
    proc=subprocess.run([node,'-e',js_code,str(runtime)],text=True,
        input=json.dumps(payload,ensure_ascii=False),capture_output=True,timeout=60)
    if proc.returncode:raise RuntimeError('Paridade JS/Python não executou: '+proc.stderr[:1000])
    outputs=json.loads(proc.stdout)
    def shapes(markup):
        root=ET.fromstring(markup)
        result=[]
        for el in root.iter():
            tag=el.tag.split('}')[-1]
            if tag=='polygon':raw=el.get('points','')
            elif tag=='path':raw=el.get('d','')
            elif tag=='circle':raw=' '.join(el.get(k,'') for k in ('cx','cy','r'))
            else:continue
            values=[float(v) for v in re.findall(r'-?\d+(?:\.\d+)?(?:e[+-]?\d+)?',raw,re.I)]
            result.append((tag,values))
        return result
    count=0
    for i,spatial in enumerate(scenes):
        for j,t in enumerate(samples):
            expected=shapes(ref.render_spatial(spatial,t,height))
            actual=shapes('<g>'+outputs[i][j]+'</g>')
            if len(expected)!=len(actual):
                raise RuntimeError(f'Paridade espacial falhou: cena {i+1}, p={t}, elementos {len(expected)} != {len(actual)}')
            for k,((tag0,val0),(tag1,val1)) in enumerate(zip(expected,actual)):
                if tag0!=tag1 or len(val0)!=len(val1) or any(abs(a-b)>.07 for a,b in zip(val0,val1)):
                    raise RuntimeError(f'Paridade espacial falhou: cena {i+1}, p={t}, forma {k}: {tag0} != {tag1}')
            count+=1
    return f'Paridade espacial JS/Python: {count} amostras OK.',True


def git(repo,*args):
    p=subprocess.run(['git','-C',str(repo),*args],capture_output=True,text=True)
    if p.returncode: raise RuntimeError('Git: '+(p.stderr.strip() or p.stdout.strip()))
    return p.stdout.strip()


def within(file,root):
    return file.resolve().is_relative_to(root.resolve())


def source_asset(repo,stage,pub,name):
    if not isinstance(name,str):return None
    name=name.replace('\\','/')
    if name.startswith('midia/'):name=name[6:]
    f=Path(name)
    if f.is_absolute() or '..' in f.parts or not name.strip():return None
    for root in (repo/'midia',pub/'midia',stage/'midia',stage/'vetorial'/'midia'):
        a=root/f
        if a.is_file() and within(a,root):return a
    return None


def inline_svg_images(markup,repo,stage,pub,n,warnings):
    tags=re.compile(r'<image\b[^>]*>',re.I|re.S)
    href=re.compile(r'((?:xlink:)?href\s*=\s*)(["\'])(.*?)\2',re.I|re.S)
    def replacement(m):
        tag=m.group(0)
        def patch_attr(a):
            raw=html.unescape(a.group(3)).strip()
            if not raw or raw.startswith(('data:','blob:','#')):return a.group(0)
            url=urlsplit(raw)
            if url.scheme or raw.startswith(('//','/')):
                warnings.append(f'Cena {n}: imagem SVG externa/não portátil: {raw[:90]}')
                return a.group(0)
            name=unquote(url.path)
            if name.startswith('./'):name=name[2:]
            src=source_asset(repo,stage,pub,name)
            if not src or src.stat().st_size>20*1024*1024:
                warnings.append(f'Cena {n}: imagem ausente ou maior que 20 MB: {raw[:90]}')
                return a.group(0)
            typ=mimetypes.guess_type(src.name)[0] or ''
            if not typ.startswith('image/'):
                warnings.append(f'Cena {n}: mídia não é imagem: {name[:90]}')
                return a.group(0)
            data='data:'+typ+';base64,'+base64.b64encode(src.read_bytes()).decode('ascii')
            return a.group(1)+a.group(2)+data+a.group(2)
        return href.sub(patch_attr,tag)
    return tags.sub(replacement,markup)


def generate_svg(graphics,scene,i,count,media_dir,width,height):
    clean=copy.deepcopy(scene)
    clean['animacoes']=[]  # Browser usa o contrato original, nunca faixas já renderizadas.
    renderer=graphics.visualize
    names=inspect.signature(renderer).parameters
    required={'p','idx','total','media_dir','width','height'}
    if not required.issubset(names):
        raise RuntimeError(f'graphics.visualize incompatível: {inspect.signature(renderer)}')
    # Injeção local, apenas no processo do publicador experimental:
    # os wrappers preservam a aparência, mas expõem os IDs e os pivôs ao navegador.
    original_markup=graphics.animate_markup
    original_image=graphics.animate_image_markup
    def marked(markup,anim,p,target,center):
        if not markup:return ''
        return (f'<g id="{html.escape(target,quote=True)}" data-pivot-x="{float(center[0]):.4f}" '
                f'data-pivot-y="{float(center[1]):.4f}">{markup}</g>')
    def marked_image(markup,anim,p,center):
        return marked(markup,anim,p,'__imagem__',center)
    try:
        graphics.animate_markup=marked
        graphics.animate_image_markup=marked_image
        out=renderer(clean,p=1.0,idx=i,total=count,media_dir=media_dir,width=width,height=height)
    finally:
        graphics.animate_markup=original_markup
        graphics.animate_image_markup=original_image
    if not isinstance(out,str) or not out.lstrip().startswith('<svg'):
        raise RuntimeError(f'SVG da cena {i+1} não retornado pelo gerador')
    return out


def safety_preflight(repo,stage,slug):
    if not repo.is_dir() or not (repo/'.git').exists():raise RuntimeError('Repositório Git não identificado em '+str(repo))
    if git(repo,'rev-parse','--show-toplevel')!=str(repo):raise RuntimeError('--repo deve ser a raiz do Git')
    branch=git(repo,'branch','--show-current')
    head=git(repo,'rev-parse','--short','HEAD')
    print('Git:',branch,head)
    print('Alterações locais (preservadas):\n'+(git(repo,'status','--short') or '(nenhuma)'))
    if branch!='release/v3-alpha4-rc1':raise RuntimeError('Branch inesperada; abortando sem modificar arquivos')
    if stage.is_relative_to(repo) or repo.is_relative_to(stage):raise RuntimeError('Stage e repositório não podem ser diretórios aninhados')
    if not re.fullmatch(r'[a-z0-9-]{1,80}',slug):raise RuntimeError('Slug inválido')
    pub=stage/'apresentacoes'/slug
    project_json=pub/'projeto.json'
    old_js=stage/'vetorial'/'player.js'
    old_page=stage/'vetorial'/'index.html'
    for p in (project_json,old_js,old_page):
        if not p.is_file() or not within(p,stage):raise RuntimeError('Arquivo necessário indisponível: '+str(p))
    if V2_MARK not in old_js.read_text('utf-8'):
        raise RuntimeError('Player base não contém a correção V2 de voz/pivô. Preservado.')
    project=json.loads(project_json.read_text('utf-8'))
    if not isinstance(project.get('cenas'),list) or not project['cenas']:
        raise RuntimeError('projeto.json sem cenas')
    return pub,project,old_js,old_page


def banner(htmltext):
    return htmltext.replace('<!doctype html>','<!doctype html>\n'+PAGE_MARK,1)


def portal_link(stage,apply):
    path=stage/'portal'/'index.html'
    if not path.is_file():return 'Portal inexistente; player acessível diretamente.'
    old=path.read_text('utf-8')
    if PORTAL_MARK in old:return 'Portal já tem link V3.'
    if '<!-- ESTUDIO_PLAYER_PORTAL_V1 -->' not in old or '</header>' not in old:
        return 'Portal não reconhecido; link não aplicado.'
    link='<a id="vetorial-v3-link" href="../vetorial-v3/" style="color:#9feacb;font-weight:700">◈ Player vetorial V3</a>'
    updated=old.replace('</header>',link+'</header>',1)
    if apply:
        backup=path.with_name('index.html.antes_player_v3.bak')
        if not backup.exists():backup.write_text(old,'utf-8')
        atomic_text(path,updated)
    return 'Portal: link V3 '+('instalado' if apply else 'planejado')


def editor_link(repo,port,apply):
    path=repo/'web'/'index.html'
    if not path.is_file():return 'Editor web/index.html não encontrado; sem alteração.'
    old=path.read_text('utf-8')
    if EDITOR_MARK in old:return 'Editor já contém link V3.'
    if git(repo,'status','--porcelain','--','web/index.html'):
        return 'Editor possui alterações locais: link omitido para não sobrepor trabalho.'
    anchor='<button id="presentBtn">Apresentar / Gravar tela</button>'
    if old.count(anchor)!=1:return 'Editor desconhecido: âncora não encontrada, link omitido.'
    url=f'http://127.0.0.1:{port}/vetorial-v3/'
    link=(f'<a id="studio-v3-vetorial-link" href="{url}" target="_blank" rel="noopener noreferrer" '
          'style="display:inline-block;padding:9px;border:1px solid #758b9e;border-radius:6px;color:inherit" '
          'title="Player Web vetorial experimental; servidor local necessário">◈ Player Web V3</a>')
    updated=old.replace(anchor,anchor+link,1)
    if apply:
        backup=path.with_name('index.html.antes_player_web_v3.bak')
        if backup.exists() and backup.read_text('utf-8')!=old:
            return 'Backup do editor já existe e difere; alteração não executada.'
        if not backup.exists():backup.write_text(old,'utf-8')
        atomic_text(path,updated)
    return 'Página do editor: link V3 '+('instalado' if apply else 'planejado')


def revert(repo,stage):
    folder=stage/'vetorial-v3'
    if folder.is_dir():
        page=folder/'index.html'
        if not page.is_file() or PAGE_MARK not in page.read_text('utf-8'):
            raise RuntimeError('Diretório V3 não reconhecido; não será movido')
        disabled=stage/('vetorial-v3.desativado-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
        if disabled.exists():raise RuntimeError('Destino de desativação já existe')
        folder.rename(disabled)
        print('Dados preservados em',disabled)
    for path,marker in ((stage/'portal'/'index.html',PORTAL_MARK),(repo/'web'/'index.html',EDITOR_MARK)):
        if not path.is_file():continue
        current=path.read_text('utf-8')
        if marker not in current:continue
        if marker==PORTAL_MARK:
            updated=re.sub(r'<a id="vetorial-v3-link"[^>]*>.*?</a>','',current,count=1)
        else:
            updated=re.sub(r'<a id="studio-v3-vetorial-link"[^>]*>.*?</a>','',current,count=1)
        if updated!=current:atomic_text(path,updated);print('Link retirado:',path)


def main():
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument('--repo',default='~/estudio_svg_v3_git')
    a.add_argument('--stage',default='~/estudio_player_stage')
    a.add_argument('--slug',default='higiene-do-sono')
    a.add_argument('--port',type=int,default=8877)
    flags=a.add_mutually_exclusive_group()
    flags.add_argument('--apply',action='store_true')
    flags.add_argument('--revert',action='store_true')
    a.add_argument('--editor-link',action='store_true',help='Inclui link local na página principal do editor, com backup')
    args=a.parse_args()
    repo=Path(args.repo).expanduser().resolve()
    stage=Path(args.stage).expanduser().resolve()
    if not 1<=args.port<=65535:raise RuntimeError('Porta HTTP inválida')
    pub,project,old_js,old_page=safety_preflight(repo,stage,args.slug)
    if args.revert:
        revert(repo,stage);return
    dest=stage/'vetorial-v3'
    if dest.exists():
        raise RuntimeError(f'Player V3 já existe em {dest}. Não sobrescrevemos. Para testar novamente, preserve essa pasta e escolha outro stage.')
    old_js_text=old_js.read_text('utf-8')
    old_html_text=old_page.read_text('utf-8')
    if '<!-- ESTUDIO_SVG_PLAYER_VETORIAL_POC_V1 -->' not in old_html_text:
        raise RuntimeError('Página V2 não reconhecida. Preservada.')
    new_js=exact_replace(old_js_text,JS_CHANGES,'player.js V2')
    new_html=banner(exact_replace(old_html_text,HTML_CHANGES,'index.html V2'))
    new_html=new_html.replace('Player vetorial experimental</title>','Player vetorial V3</title>',1)
    # ESTUDIO_V3_MEDIA_PATCH_2026_11 — aplica recursos também aos novos exports
    from player_v3_compat import patch_player, patch_html
    new_js=patch_player(new_js)
    new_html=patch_html(new_html)
    sys.path.insert(0,str(repo));sys.dont_write_bytecode=True
    graphics=importlib.import_module('graphics')
    sig=inspect.signature(graphics.visualize)
    if 'p' not in sig.parameters:raise RuntimeError('graphics.visualize diferente')
    video=project.get('video') or {};width=int(video.get('width') or 1280);height=int(video.get('height') or 720)
    if width<1 or height<1:raise RuntimeError('Dimensões do vídeo inválidas')
    scenes=project['cenas']
    names=[(c.get('imagem') or {}).get('arquivo') for c in scenes if isinstance(c.get('imagem'),dict)]
    names=[n for n in names if isinstance(n,str) and n]
    roots=[repo/'midia',pub/'midia',stage/'midia']
    scores=[sum((root/n).is_file() for n in names if '/' not in n and '\\' not in n) for root in roots]
    media_dir=roots[scores.index(max(scores))]
    warnings=[];svgs=[]
    for i,c in enumerate(scenes):
        svg=generate_svg(graphics,c,i,len(scenes),media_dir,width,height)
        svg=inline_svg_images(svg,repo,stage,pub,i+1,warnings)
        try:ET.fromstring(svg)
        except ET.ParseError as e:raise RuntimeError(f'Cena {i+1} possui SVG inválido: {e}') from e
        if c.get('tipo')=='espacial' and 'id="spatial-world"' not in svg:
            raise RuntimeError(f'Cena {i+1} sem grupo espacial; interrupção para evitar frame congelado')
        svgs.append(svg)
        im=c.get('imagem') or {}
        filename=im.get('arquivo') if isinstance(im,dict) else None
        if filename and not source_asset(repo,stage,pub,filename):warnings.append(f'Cena {i+1}: imagem original não encontrada: {filename}')
    audios=[];clips=[]
    for c in scenes:
        data=c.get('audio') or {};name=data.get('voice_file','') if isinstance(data,dict) else ''
        if not name:continue
        src=source_asset(repo,stage,pub,name)
        if src:
            base=Path(name)
            if base.is_absolute() or '..' in base.parts:raise RuntimeError('Nome de áudio inválido')
            audios.append((src,base))
        else:warnings.append('Voz em arquivo ausente, síntese no browser será utilizada: '+str(name))
    for c in scenes:
        cfg=c.get('video_clipe') or {}
        name=cfg.get('arquivo','') if isinstance(cfg,dict) else ''
        if not name:continue
        if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_.-]{0,140}\.(?:mp4|webm|ogv)',name) or '..' in name:
            raise RuntimeError('Nome de clipe inseguro: '+str(name))
        src=source_asset(repo,stage,pub,name)
        if src:clips.append((src,Path(name)))
        else:warnings.append('Clipe sobreposto original ausente: '+name)
    print('Cenas:',len(svgs),'| Espaciais:',sum(c.get('tipo')=='espacial' for c in scenes))
    print('Mídia base:',media_dir)
    print('Narrações copiadas:',len(audios))
    for w in warnings:print('AVISO:',w)
    if not args.apply:
        print(portal_link(stage,False))
        if args.editor_link:print(editor_link(repo,args.port,False))
        print('SIMULAÇÃO: nenhum arquivo foi modificado. Acrescente --apply.')
        return
    stage.mkdir(parents=True,exist_ok=True)
    temp=Path(tempfile.mkdtemp(prefix='.vetorial-v3-build-',dir=stage))
    try:
        (temp/'cenas').mkdir()
        (temp/'index.html').write_text(new_html,'utf-8')
        (temp/'player.js').write_text(new_js,'utf-8')
        (temp/'runtime.js').write_text(RUNTIME_JS,'utf-8')
        shutil.copy2(repo/'web_player'/'v3'/'media_layer.js',temp/'media_layer.js')
        for i,svg in enumerate(svgs,1):(temp/'cenas'/f'cena-{i:03d}.svg').write_text(svg,'utf-8')
        for src,basename in audios:
            path=temp/'midia'/basename
            if not within(path,temp):raise RuntimeError('Mídia fora do stage')
            path.parent.mkdir(parents=True,exist_ok=True)
            if not path.exists():shutil.copy2(src,path)
        for src,basename in clips:
            dest_clip=temp/'midia'/basename
            dest_clip.parent.mkdir(parents=True,exist_ok=True)
            if not dest_clip.exists():shutil.copy2(src,dest_clip)
        report={
            'estado':'experimental; sem teste no Android real',
            'projeto':args.slug,'cenas':len(svgs),
            'branch':git(repo,'branch','--show-current'),'head':git(repo,'rev-parse','HEAD'),
            'contrato':'3.0.0-alpha.4','warnings':warnings,
            'implementado':['projeção e animação de cena espacial no navegador',
              'easings e repeticoes/yoyo','alvos SVG e alvos especiais',
              'animações procedurais: globo, linha, barras, numero, cartoes, arvore, svg',
              'voz e pivô do Player V2 preservados'],
            'limites':['trilhas musicais não integradas',
              'paridade pixel-a-pixel não comprovada','cenas SVG com SMIL/CSS podem ter timeline própria',
              'HTML público externo não alterado']
        }
        (temp/'RELATORIO.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf-8')
        node=shutil.which('node')
        if node:
            for file in ('player.js','runtime.js'):
                p=subprocess.run([node,'--check',str(temp/file)],capture_output=True,text=True)
                if p.returncode:raise RuntimeError('Erro sintático JS em '+file+': '+p.stderr)
            print('JS: sintaxe validada via node --check')
        parity_note,parity_ok=parity_check(repo,project,temp/'runtime.js',round(1280*height/width))
        print(parity_note)
        report['paridade_espacial_validada']=parity_ok
        (temp/'RELATORIO.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf-8')
        temp.rename(dest)
    except Exception:
        # Apenas a pasta temporária nossa é descartada; nenhum arquivo preexistente sofre alteração.
        if temp.exists():shutil.rmtree(temp)
        raise
    print('Player V3 criado:',dest)
    print(portal_link(stage,True))
    if args.editor_link:print(editor_link(repo,args.port,True))
    print('URL: http://127.0.0.1:'+str(args.port)+'/vetorial-v3/')
    print('Sem commit/push; /vetorial V2 preservado.')

if __name__=='__main__':
    try:main()
    except Exception as exc:
        print('ERRO:',exc,file=sys.stderr)
        raise SystemExit(2)
