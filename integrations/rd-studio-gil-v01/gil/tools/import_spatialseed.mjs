// Read-only, deliberately restricted adapter for native SpatialSeed v4 snapshots.
// Canonical projection and appearance resolution come from the installed SpatialSeed.
import {readFile,writeFile} from 'node:fs/promises';
import {resolve,join} from 'node:path';
import {pathToFileURL} from 'node:url';
import {compile} from '../src/model.mjs';
import {serialize} from '../src/language.mjs';
import {Timeline} from '../src/timeline.mjs';
const fail=m=>{throw Error(m)};
const vec=(v,n,label,positive=false)=>{if(!Array.isArray(v)||v.length!==n||v.some(x=>!Number.isFinite(x)||Math.abs(x)>1e5||(positive&&x<=0)))fail('Vetor inválido: '+label);return v;};
// XYZ Euler, inverse of the SpatialSeed eulerQuaternion convention.
function angles(q){const [x,y,z,w]=vec(q,4,'rotation');if(Math.abs(Math.hypot(...q)-1)>1e-4)fail('Quaternion não unitário');const m13=2*(x*z+y*w),m23=2*(y*z-x*w),m33=1-2*(x*x+y*y),m12=2*(x*y-z*w),m11=1-2*(y*y+z*z),m32=2*(y*z+x*w),m22=1-2*(x*x+z*z);const sy=Math.asin(Math.max(-1,Math.min(1,m13))),sx=Math.abs(m13)<.9999999?Math.atan2(-m23,m33):Math.atan2(m32,m22),sz=Math.abs(m13)<.9999999?Math.atan2(-m12,m11):0;return [sx,sy,sz].map(x=>x*180/Math.PI);}
export async function convert(snapshot,root){
 if(snapshot?.format!=='spatial-seed'||snapshot.schemaVersion!==4||!Array.isArray(snapshot.scene?.objects))fail('Esperado arquivo SpatialSeed JSON, schemaVersion 4');
 const imp=rel=>import(pathToFileURL(join(resolve(root),rel)).href);
 const {projectInstanceGraphScene}=await imp('packages/instance-graph/src/InstanceGraph.js');
 const {AppearanceRuntime}=await imp('packages/appearance-runtime/src/AppearanceRuntime.js');
 const ar=new AppearanceRuntime();if(snapshot.assets)ar.importAssets(snapshot.assets);
 const projected=projectInstanceGraphScene(snapshot.scene), objects=projected.objects;
 if(!objects.length||objects.length>240)fail('Limite inicial: 1–240 nós projetados');
 const ids=new Map(objects.map((o,i)=>[String(o.id),'ss_'+i]));if(ids.size!==objects.length)fail('Identidade duplicada');
 const spec={version:'gil-timeline-0.1',stage:{width:960,height:540,duration:8,background:'#101c2c',camera:'cam'},resources:[{id:'camR',kind:'camera',props:{z:16,fov:45}},{id:'sunR',kind:'light.directional',props:{x:-4,y:5,z:8,intensity:1.1}},{id:'groupR',kind:'group',props:{sourceId:''}},{id:'boxR',kind:'mesh.box',props:{size:1,color:'#88c9dd',sourceId:''}}],objects:[{id:'cam',resource:'camR',parent:null,props:{}},{id:'sun',resource:'sunR',parent:null,props:{}}],tracks:[],cues:[]};
 let extent=0, boxes=0;
 for(const o of objects){const id=ids.get(String(o.id)),parent=o.parentId==null?null:ids.get(String(o.parentId));if(o.parentId!=null&&!parent)fail('Pai não projetado: '+o.id);
  const pos=vec(o.position??[0,0,0],3,'position'), rot=angles(o.rotation??[0,0,0,1]), scale=vec(o.scale??[1,1,1],3,'scale',true);
  if(o.pivot&&vec(o.pivot,3,'pivot').some(x=>Math.abs(x)>1e-8))fail('Pivot distinto da origem ainda não suportado: '+o.id);
  const sourceId=String(o.id);if(sourceId.length>2048)fail('ID excessivo');
  // A logical node retains TRS; a geometry child retains dimension independently of logical descendants.
  const props={x:pos[0],y:pos[1],z:pos[2],rx:rot[0],ry:rot[1],rz:rot[2],sx:scale[0],sy:scale[1],sz:scale[2],sourceId};
  spec.objects.push({id,resource:'groupR',parent,props});
  if(o.kind==='group')continue;
  if(o.geometry?.type!=='box'||o.mesh||o.geometry?.mesh||o.geometry?.vertices)fail('Não suportado nesta ponte: '+o.id+' ('+o.kind+'/'+o.geometry?.type+'). Exporte vídeo ou SVG pelo motor original.');
  const dim=vec(o.geometry.size??[1,1,1],3,'size',true);const material=o.appearanceId?ar.legacyMaterial(o.appearanceId):o.material??{};
  const color=o.color??material.color??'#88c9dd';if(typeof color!=='string'||!/^#[0-9a-fA-F]{6}$/.test(color))fail('Cor incompatível: '+o.id);
  const opacity=material.opacity??1;if(!Number.isFinite(opacity)||opacity<0||opacity>1)fail('Opacidade inválida');
  spec.objects.push({id:id+'_geo',resource:'boxR',parent:id,props:{sx:dim[0],sy:dim[1],sz:dim[2],color,opacity,sourceId}});boxes++;
 }
 if(!boxes)fail('Nenhuma caixa suportada encontrada');
 // Auto-frame from the same world matrices used by GIL, not from local positions.
 const frame=new Timeline(compile(spec)).sample(0), centers=frame.objects.filter(x=>x.kind==='mesh.box').map(o=>{const m=o.matrix;return {center:m.slice(12,15),r:(Math.hypot(m[0],m[1],m[2])+Math.hypot(m[4],m[5],m[6])+Math.hypot(m[8],m[9],m[10]))/2};});
 const min=[0,1,2].map(i=>Math.min(...centers.map(b=>b.center[i]-b.r))),max=[0,1,2].map(i=>Math.max(...centers.map(b=>b.center[i]+b.r))),mid=min.map((a,i)=>(a+max[i])/2);extent=Math.max(...max.map((a,i)=>a-min[i]));
 spec.objects[0].props={x:mid[0],y:mid[1],z:mid[2]+Math.max(5,extent*2.2)};
 const result=serialize(spec);compile(result);return result;
}
if(process.argv[1]&&pathToFileURL(resolve(process.argv[1])).href===import.meta.url){const [input,output,root]=process.argv.slice(2);if(!input||!output||!root)fail('Uso: node import_spatialseed.mjs arquivo.spatialseed saida.gil raiz-spatialseed');const source=await convert(JSON.parse(await readFile(input,'utf8')),root);await writeFile(output,source,{flag:'wx'});}
