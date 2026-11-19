// Estúdio SVG M1T — grafo de instâncias 2D (motor matemático puro).
// Autor do projeto: Rogério Duarte. Sem DOM, eval ou dependências externas.
export const IDENTITY = Object.freeze([1, 0, 0, 1, 0, 0]);
const NAME = /^[A-Za-z0-9_-]{1,64}$/;
const finite = x => typeof x === 'number' && Number.isFinite(x);
const validId = (s, context) => {
  if (typeof s !== 'string' || !NAME.test(s)) throw Error(`${context}: identificador inválido`);
  return s;
};
export function affineMultiply(a, b) {
  return [
    a[0]*b[0]+a[2]*b[1], a[1]*b[0]+a[3]*b[1],
    a[0]*b[2]+a[2]*b[3], a[1]*b[2]+a[3]*b[3],
    a[0]*b[4]+a[2]*b[5]+a[4], a[1]*b[4]+a[3]*b[5]+a[5]
  ];
}
export function affinePoint(a,x,y) {return [a[0]*x+a[2]*y+a[4],a[1]*x+a[3]*y+a[5]];}
export function affineInverse(a) {
  const det=a[0]*a[3]-a[1]*a[2];
  if (Math.abs(det)<1e-10) throw Error('Transformação singular não admite picking');
  return [a[3]/det,-a[1]/det,-a[2]/det,a[0]/det,
    (a[2]*a[5]-a[3]*a[4])/det,(a[1]*a[4]-a[0]*a[5])/det];
}
export function validateAffine(m, context='matriz') {
  if (!Array.isArray(m) || m.length!==6 || !m.every(finite)) throw Error(`${context}: matriz afim 2D inválida`);
  if (m.some((v,i)=>Math.abs(v)>(i<4?100:5))) throw Error(`${context}: fora de limite`);
  if (Math.abs(m[0]*m[3]-m[1]*m[2])<1e-8) throw Error(`${context}: transformação singular`);
  return [...m];
}
export function affineFrom({x=0,y=0,sx=1,sy=1,rotation=0,shear=0,pivotX=.5,pivotY=.5}={}) {
  const vals=[x,y,sx,sy,rotation,shear,pivotX,pivotY];
  if (!vals.every(finite)) throw Error('Parâmetros de transformação não finitos');
  const r=rotation*Math.PI/180,c=Math.cos(r),s=Math.sin(r);
  const linear=affineMultiply([c,s,-s,c,0,0], [sx,0,shear*sy,sy,0,0]);
  return affineMultiply([1,0,0,1,x+pivotX,y+pivotY],affineMultiply(linear,[1,0,0,1,-pivotX,-pivotY]));
}
export function pixelMatrix(m,width,height) {
  if(!(width>0&&height>0))throw Error('Viewport sem dimensões');
  return [m[0],m[1]*height/width,m[2]*width/height,m[3],m[4]*width,m[5]*height];
}
const keyOf = path => 'gi_'+path.map(s=>s.replace(/[^A-Za-z0-9_-]/g,'_')).join('_').slice(0,180);
const asMatrix = item => validateAffine(item?.matrix??IDENTITY);

export function assertGraph(library, roots=[]) {
  if (!library && (!roots || !roots.length)) return new Map();
  if(!library || library.format!=='rd-instance-library-1' || !Array.isArray(library.definitions) || library.definitions.length>64) throw Error('Biblioteca de instâncias inválida');
  const defs=new Map();
  for(const d of library.definitions){
    if(!d||typeof d!=='object')throw Error('Definição inválida');
    validId(d.id,'definição');
    if(defs.has(d.id))throw Error(`Definição repetida: ${d.id}`);
    if(d.kind==='media'){
      if(!d.media||!['image','video','gil'].includes(d.media.kind)||d.media.id!==d.id)throw Error(`Mídia de definição inválida: ${d.id}`);
      if(d.media.kind==='video'&&d.media.audio_enabled!==false)throw Error('Vídeo instanciado precisa estar sem áudio até integrar mixagem por instância');
    }else if(d.kind==='group'){
      if(!Array.isArray(d.children)||d.children.length>32)throw Error(`Grupo inválido: ${d.id}`);
      const ids=new Set();
      for(const ch of d.children){
        validId(ch.id,'aresta');validId(ch.ref,'referência');
        if(ids.has(ch.id))throw Error('Aresta repetida: '+ch.id);
        ids.add(ch.id);asMatrix(ch.transform);if(ch.opacity!==undefined && (!finite(ch.opacity)||ch.opacity<0||ch.opacity>1))throw Error('Opacidade de grupo inválida');
      }
    }else throw Error(`Tipo de definição inválido: ${d.kind}`);
    defs.set(d.id,d);
  }
  // Strongly bounded graph: prevent cycles and combinatorial expansion.
  const visits=new Map(),leafCounts=new Map();
  const dfs=(ref,depth)=>{
    if(depth>12)throw Error('Grafo de instâncias profundo demais');
    if(visits.get(ref)==='visiting')throw Error('Ciclo no grafo de instâncias: '+ref);
    const d=defs.get(ref);if(!d)throw Error('Definição ausente: '+ref);
    if(visits.get(ref)==='done')return leafCounts.get(ref);
    visits.set(ref,'visiting');
    let count=d.kind==='media'?1:0;
    if(d.kind==='group') for(const ch of d.children) count+=dfs(ch.ref,depth+1);
    if(count>256)throw Error('Grafo excede 256 folhas');
    leafCounts.set(ref,count);visits.set(ref,'done');return count;
  };
  for(const ref of defs.keys())dfs(ref,0);
  if(!Array.isArray(roots)||roots.length>32)throw Error('Instâncias da cena inválidas');
  const ids=new Set();let total=0;
  for(const r of roots){
    validId(r?.id,'instância');validId(r.ref,'referência da instância');
    if(ids.has(r.id))throw Error('Instância repetida: '+r.id);ids.add(r.id);
    asMatrix(r.transform);
    if(r.opacity!==undefined && (!finite(r.opacity)||r.opacity<0||r.opacity>1))throw Error('Opacidade da instância inválida');
    if(r.start!==undefined && (!finite(r.start)||r.start<0||r.start>600))throw Error('Início inválido');
    if(r.end!==undefined && (!finite(r.end)||r.end<=0||r.end>600))throw Error('Fim inválido');
    if(r.start!==undefined&&r.end!==undefined&&r.end<=r.start)throw Error('Intervalo da instância inválido');
    if(!defs.has(r.ref))throw Error('Instância aponta para definição ausente');
    total+=leafCounts.get(r.ref);
    if(total>128)throw Error('Cena excede 128 instâncias visuais');
  }
  return defs;
}

// Return flat, renderer-compatible media objects. Shared definitions remain in project JSON.
export function expandSceneInstances(library,roots=[],{duration=600}={}){
  const defs=assertGraph(library,roots), out=[], keys=new Set();
  function descend(ref,path,matrix,opacity,start,end){
    const d=defs.get(ref);
    if(d.kind==='group'){
      for(const edge of d.children){
        descend(edge.ref,[...path,edge.id],affineMultiply(matrix,asMatrix(edge.transform)),opacity*(edge.opacity??1),start,end);
      }
      return;
    }
    const key=keyOf(path);
    if(keys.has(key))throw Error('Colisão de identificador de instância: '+key);
    keys.add(key);
    const base=d.media;
    const lo=Math.max(start,Number(base.start??0)),hi=Math.min(end,Number(base.end??duration));
    if(hi<=lo)return;
    const o={...base,id:key,instance_path:path.join('/'),instance_definition:d.id,
      instance_matrix:[...matrix],opacity:(base.opacity??1)*opacity,start:lo,end:hi};
    if(base.motion_programs)o.motion_programs=[...base.motion_programs];
    out.push(o);
  }
  for(const root of roots){
    if(root.enabled===false)continue;
    descend(root.ref,[root.id],asMatrix(root.transform),root.opacity??1,
      Math.max(0,root.start??0),Math.min(duration,root.end??duration));
  }
  return out;
}

export function renderableLayers(project,scene){
  const direct=scene?.objetos_midia||[];
  if(!scene?.instances?.length)return direct;
  const generated=expandSceneInstances(project?.instance_library,scene.instances,{duration:Number(scene.duracao)||600});
  const names=new Set(direct.map(o=>o.id));
  for(const o of generated)if(names.has(o.id))throw Error('ID de instância colide com objeto existente: '+o.id);
  return [...direct,...generated];
}

export function pickGraphLeaf(leaves, x,y, alphaTest=()=>true){
  for(let i=leaves.length-1;i>=0;i--){
    const o=leaves[i],m=affineInverse(o.instance_matrix||IDENTITY);
    const [u,v]=affinePoint(m,x,y);
    const x0=o.x-o.w/2,y0=o.y-o.h/2;
    if(u>=x0&&u<=x0+o.w&&v>=y0&&v<=y0+o.h&&alphaTest(o,(u-x0)/o.w,(v-y0)/o.h))return o;
  }
  return null;
}
