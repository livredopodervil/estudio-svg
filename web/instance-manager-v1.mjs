// M1T — ações controladas sobre o grafo canônico; sem duplicar assets.
import {affineFrom,affineMultiply,assertGraph} from './instance-graph-v1.mjs';
const NAME=/^[A-Za-z0-9_-]{1,64}$/;
const unique=(taken,prefix)=>{for(let n=1;n<=9999;n++){const id=`${prefix}${n}`;if(!taken.has(id))return id;}throw Error('Limite de identificadores atingido');};
const rootById=(scene,id)=>{const root=scene.instances?.find(r=>r.id===id);if(!root)throw Error('Instância não encontrada: '+id);return root;};
// Link a selected, existing media object to a reusable definition.
export function instantiateSelected(project,scene,media){
  if(!media||!['image','video','gil'].includes(media.kind))throw Error('Selecione imagem, vídeo ou GIL independente');
  if(media.kind==='video'&&media.audio_enabled!==false)throw Error('Desative o áudio do clipe antes de criar uma instância visual');
  if(!NAME.test(media.id||''))throw Error('ID do objeto inválido');
  const lib=structuredClone(project.instance_library||{format:'rd-instance-library-1',definitions:[]});
  const roots=structuredClone(scene.instances||[]);
  if(lib.format!=='rd-instance-library-1')throw Error('Versão da biblioteca incompatível');
  const defs=lib.definitions;
  let id='d_'+media.id.slice(0,60);
  let def=defs.find(d=>d.id===id&&d.kind==='media');
  if(def && JSON.stringify({...def.media,id:media.id})!==JSON.stringify(media)){
    // Preserve earlier definitions; a changed asset deserves a fresh definition.
    def=null;id=unique(new Set(defs.map(d=>d.id)),'d');
  }
  if(!def){
    if(defs.length>=64)throw Error('Biblioteca cheia (64 definições)');
    def={id,kind:'media',media:{...structuredClone(media),id}};
    defs.push(def);
  }
  const rootId=unique(new Set(roots.map(r=>r.id)),'inst');
  if(roots.length>=32)throw Error('Cena comporta no máximo 32 instâncias');
  const root={id:rootId,ref:id,transform:{matrix:[1,0,0,1,.04,.04]},
    opacity:1,start:0,end:Number(scene.duracao)||8,enabled:true};
  roots.push(root);
  assertGraph(lib,roots);
  project.instance_library=lib;scene.instances=roots;
  return root;
}
export function duplicateInstance(project,scene,id){
  const original=rootById(scene,id);
  if(scene.instances.length>=32)throw Error('Limite de instâncias');
  const copy=structuredClone(original);copy.id=unique(new Set(scene.instances.map(r=>r.id)),'inst');
  copy.transform={matrix:affineMultiply([1,0,0,1,.04,.04],original.transform?.matrix||[1,0,0,1,0,0])};
  const candidate=[...scene.instances,copy];assertGraph(project.instance_library,candidate);
  scene.instances=candidate;return copy;
}
export function groupSceneInstances(project,scene){
  const roots=scene.instances||[];
  if(roots.length<2)throw Error('Selecione ao menos duas instâncias para agrupar');
  const [first]=roots;
  if(roots.some(r=>r.start!==first.start||r.end!==first.end||r.enabled!==first.enabled))
    throw Error('Agrupamento exige o mesmo intervalo e visibilidade; ajuste antes de agrupar');
  const lib=structuredClone(project.instance_library);
  const defs=lib.definitions;
  if(defs.length>=64)throw Error('Limite de definições');
  const id=unique(new Set(defs.map(d=>d.id)),'grupo');
  const edges=roots.map((r,i)=>({id:'item'+(i+1),ref:r.ref,transform:structuredClone(r.transform),opacity:r.opacity??1}));
  if(edges.length>32)throw Error('Grupo comporta no máximo 32 membros');
  const def={id,kind:'group',children:edges};
  const root={id:unique(new Set(roots.map(r=>r.id)),'grupo'),ref:id,
    transform:{matrix:[1,0,0,1,0,0]},opacity:1,start:first.start,end:first.end,enabled:first.enabled};
  defs.push(def);assertGraph(lib,[root]);
  project.instance_library=lib;scene.instances=[root];return root;
}
export function transformInstance(project,scene,id,action){
  const node=rootById(scene,id);
  const moves={left:[1,0,0,1,-.04,0],right:[1,0,0,1,.04,0],up:[1,0,0,1,0,-.04],down:[1,0,0,1,0,.04]};
  const op=moves[action]||({rotate:affineFrom({rotation:15}),
    'rotate-back':affineFrom({rotation:-15}),grow:affineFrom({sx:1.12,sy:1.12}),
    shrink:affineFrom({sx:.9,sy:.9}),skew:affineFrom({shear:.10})})[action];
  if(!op)throw Error('Transformação desconhecida: '+action);
  const before=node.transform?.matrix||[1,0,0,1,0,0];
  node.transform={matrix:affineMultiply(op,before)};
  try{assertGraph(project.instance_library,scene.instances);}catch(e){node.transform={matrix:before};throw e;}
  return node;
}
export function removeInstance(scene,id){
  const index=scene.instances?.findIndex(r=>r.id===id)??-1;
  if(index<0)throw Error('Instância não encontrada');
  return scene.instances.splice(index,1)[0];
}

// M1U — typed, non-destructive commands for a shared definition library.
const FILE_NAME=/^[A-Za-z0-9_.-]{1,100}$/;
const validateAllScenes=(project,library)=>{
  for(const scene of project.cenas||[])assertGraph(library,scene.instances||[]);
};
const getDefinition=(project,id)=>{
  const d=project?.instance_library?.definitions?.find(x=>x.id===id);
  if(!d)throw Error('Definição ausente: '+id);
  return d;
};
export function replaceDefinitionMedia(project,id,updates){
  const prior=getDefinition(project,id);
  if(prior.kind!=='media')throw Error('Selecione uma definição de mídia');
  if(!updates||typeof updates!=='object'||Array.isArray(updates))throw Error('Parâmetros inválidos');
  const accepted=new Set(['label','file','x','y','w','h','opacity','rotation','fit']);
  for(const key of Object.keys(updates))if(!accepted.has(key))throw Error('Parâmetro não permitido: '+key);
  const result=structuredClone(project.instance_library);
  const d=result.definitions.find(x=>x.id===id),m=d.media;
  for(const [key,value] of Object.entries(updates)){
    if(key==='label'){
      if(typeof value!=='string'||value.length>120)throw Error('Rótulo inválido');m.label=value;
    }else if(key==='file'){
      if(m.kind==='gil')throw Error('Fonte GIL deve ser importada como definição JSON');
      if(typeof value!=='string'||!FILE_NAME.test(value))throw Error('Nome de mídia inválido');
      const ext=value.toLowerCase().split('.').pop();
      if(!((m.kind==='image'&&['jpg','jpeg','png','webp'].includes(ext))||(m.kind==='video'&&['mp4','webm','mov','mkv','m4v'].includes(ext))))throw Error('Extensão incompatível');
      m.file=value;if(m.kind==='image'){m.source_file=value;m.source_crop=[];}
    }else if(key==='fit'){
      if(!['cover','contain'].includes(value))throw Error('Ajuste inválido');m.fit=value;
    }else{
      const ranges={x:[-2,3],y:[-2,3],w:[.02,2],h:[.02,2],opacity:[0,1],rotation:[-360,360]};
      const [lo,hi]=ranges[key];if(typeof value!=='number'||!Number.isFinite(value)||value<lo||value>hi)throw Error('Valor fora de limite: '+key);
      m[key]=value;
    }
  }
  validateAllScenes(project,result);
  project.instance_library=result;
  return result.definitions.find(x=>x.id===id);
}
export function exportDefinitionBundle(project,id){
  const defs=new Map((project.instance_library?.definitions||[]).map(d=>[d.id,d]));
  const ordered=[],seen=new Set();
  function walk(key){
    if(seen.has(key))return;
    const d=defs.get(key);if(!d)throw Error('Definição não encontrada');
    seen.add(key);
    if(d.kind==='group')for(const ch of d.children)walk(ch.ref);
    ordered.push(structuredClone(d));
  }
  walk(id);
  return {format:'rd-studio-element-1',root:id,definitions:ordered};
}
export function importDefinitionBundle(project,scene,doc){
  if(doc?.format!=='rd-studio-element-1'||!Array.isArray(doc.definitions)||!doc.definitions.length||doc.definitions.length>64||typeof doc.root!=='string')throw Error('Pacote de definição inválido');
  const base=structuredClone(project.instance_library||{format:'rd-instance-library-1',definitions:[]});
  if(base.format!=='rd-instance-library-1')throw Error('Biblioteca incompatível');
  const input=new Map(),taken=new Set(base.definitions.map(d=>d.id));
  for(const d of doc.definitions){
    if(!d||typeof d.id!=='string'||!NAME.test(d.id)||input.has(d.id)||!['media','group'].includes(d.kind))throw Error('ID de definição inválido ou repetido');
    input.set(d.id,d);
  }
  if(!input.has(doc.root))throw Error('Raiz do elemento ausente');
  if(base.definitions.length+input.size>64)throw Error('Limite de 64 definições');
  const ids=new Map();
  for(const old of input.keys()){
    let next=old;
    if(taken.has(next))next=unique(taken,'asset');
    taken.add(next);ids.set(old,next);
  }
  for(const original of input.values()){
    const d=structuredClone(original);d.id=ids.get(original.id);
    if(d.kind==='media'){
      if(!d.media||d.media.id!==original.id)throw Error('ID de mídia incoerente');
      d.media.id=d.id;
    }else{
      if(!Array.isArray(d.children))throw Error('Grupo inválido');
      for(const child of d.children){
        if(ids.has(child.ref))child.ref=ids.get(child.ref);
        else if(!taken.has(child.ref))throw Error('Referência ausente: '+child.ref);
      }
    }
    base.definitions.push(d);
  }
  const roots=structuredClone(scene.instances||[]);
  if(roots.length>=32)throw Error('Limite de instâncias da cena');
  const root={id:unique(new Set(roots.map(r=>r.id)),'inst'),ref:ids.get(doc.root),transform:{matrix:[1,0,0,1,0,0]},opacity:1,start:0,end:Number(scene.duracao)||8,enabled:true};
  roots.push(root);validateAllScenes(project,base);assertGraph(base,roots);
  project.instance_library=base;scene.instances=roots;
  return root;
}
function resourceHierarchy(library,ref,parent,depth=0,rows=[]){
  if(depth>12)return rows;
  const d=library.definitions.find(x=>x.id===ref);if(!d)return rows;
  rows.push({ref,id:parent,depth,kind:d.kind,label:d.kind==='media'?(d.media.label||d.id):d.id});
  if(d.kind==='group')for(const edge of d.children)resourceHierarchy(library,edge.ref,edge.id,depth+1,rows);
  return rows;
}

// One inspector for resources, groups and scene instances. Never duplicates media.
export function installInstanceManager(ins,ctx){
  const doc=ins.ownerDocument;
  const panel=doc.createElement('details');panel.className='rd-instance-manager';
  panel.style.cssText='margin:12px 0;padding:12px;border:1px solid var(--line,#58606d);border-radius:12px;';
  const summary=doc.createElement('summary');summary.textContent='◈ Recursos, grupos e instâncias vinculadas';
  summary.style.cssText='font-weight:650;cursor:pointer';panel.append(summary);
  const note=doc.createElement('p');note.textContent='Selecione uma definição para alterar a mídia base em TODAS as instâncias. Árvores compartilhadas preservam memória.';
  note.style.cssText='font-size:.86em;line-height:1.4';panel.append(note);
  const tools=doc.createElement('div');tools.style.cssText='display:flex;flex-wrap:wrap;gap:6px;margin:9px 0';panel.append(tools);
  const rootsView=doc.createElement('div');rootsView.style.cssText='display:grid;gap:6px';panel.append(rootsView);
  const defsView=doc.createElement('div');defsView.style.cssText='display:grid;gap:6px;margin-top:12px';panel.append(defsView);
  const editor=doc.createElement('div');editor.style.cssText='display:grid;gap:8px;margin:10px 0';panel.append(editor);
  const status=doc.createElement('small');status.setAttribute('role','status');panel.append(status);
  ins.after(panel);
  let activeRoot='',activeDef='';
  function btn(parent,text,fn){const b=doc.createElement('button');b.type='button';b.textContent=text;b.style.cssText='min-height:36px;touch-action:manipulation';b.onclick=fn;parent.append(b);return b;}
  function mutate(fn){try{const out=fn();ctx.changed();ctx.preview();refresh();return out;}catch(e){ctx.notify(e.message,true);return null;}}
  btn(tools,'＋ Criar instância do selecionado',()=>mutate(()=>{const r=instantiateSelected(ctx.project(),ctx.scene(),ctx.selectedObject());activeRoot=r.id;activeDef=r.ref;}));
  btn(tools,'▧ Agrupar instâncias',()=>mutate(()=>{const r=groupSceneInstances(ctx.project(),ctx.scene());activeRoot=r.id;activeDef=r.ref;}));
  function downloadJSON(docValue,title){const b=new Blob([JSON.stringify(docValue,null,2)],{type:'application/json'});const url=URL.createObjectURL(b);const a=doc.createElement('a');a.href=url;a.download=title+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),5000);}
  btn(tools,'↓ Exportar elemento',()=>{try{if(!activeDef)throw Error('Selecione uma definição');downloadJSON(exportDefinitionBundle(ctx.project(),activeDef),activeDef);}catch(e){ctx.notify(e.message,true);}});
  const importPick=doc.createElement('input');importPick.type='file';importPick.accept='.json,application/json';importPick.hidden=true;panel.append(importPick);
  btn(tools,'↑ Importar elemento JSON',()=>importPick.click());
  importPick.onchange=async()=>{const file=importPick.files?.[0];importPick.value='';if(!file)return;
    try{if(file.size>500000)throw Error('Elemento JSON muito grande');const json=JSON.parse(await file.text());
      const r=mutate(()=>importDefinitionBundle(ctx.project(),ctx.scene(),json));if(r){activeRoot=r.id;activeDef=r.ref;refresh();}}
    catch(e){ctx.notify(e.message,true);}
  };
  function refresh(){
    rootsView.replaceChildren();defsView.replaceChildren();editor.replaceChildren();
    const project=ctx.project(),scene=ctx.scene(),library=project?.instance_library||{format:'rd-instance-library-1',definitions:[]},roots=scene?.instances||[];
    if(!scene||!project)return;
    const heading=doc.createElement('strong');heading.textContent='Hierarquia da cena ('+roots.length+' instâncias)';rootsView.append(heading);
    if(!roots.length){const p=doc.createElement('small');p.textContent='Nenhuma instância nesta cena';rootsView.append(p);}
    for(const root of roots){
      const card=doc.createElement('div');card.style.cssText='border:1px solid #506679;border-radius:9px;padding:7px';
      const select=btn(card,(activeRoot===root.id?'● ':'○ ')+root.id+' → '+root.ref,()=>{activeRoot=root.id;activeDef=root.ref;refresh();});select.style.cssText+=';display:block;width:100%;text-align:left';
      if(activeRoot===root.id){
        for(const child of resourceHierarchy(library,root.ref,root.id).slice(1)){
          const line=btn(card,'  '.repeat(child.depth)+'↳ '+child.id+' → '+child.ref+' · '+child.label,()=>{activeDef=child.ref;refresh();});
          line.style.cssText+=';display:block;width:100%;text-align:left;padding-left:'+Math.min(26*child.depth,130)+'px';
        }
        const actions=doc.createElement('div');actions.style.cssText='display:flex;flex-wrap:wrap;gap:4px';card.append(actions);
        for(const [label,op] of [['←','left'],['→','right'],['↑','up'],['↓','down'],['↻','rotate'],['＋','grow'],['−','shrink'],['⌁','skew']])btn(actions,label,()=>mutate(()=>transformInstance(project,scene,root.id,op)));
        btn(actions,'Duplicar vinculado',()=>mutate(()=>{const r=duplicateInstance(project,scene,root.id);activeRoot=r.id;}));
        btn(actions,'Remover instância',()=>mutate(()=>{removeInstance(scene,root.id);activeRoot='';}));
      }
      rootsView.append(card);
    }
    const dh=doc.createElement('strong');dh.textContent='Biblioteca de definições ('+library.definitions.length+')';defsView.append(dh);
    for(const d of library.definitions){
      const b=btn(defsView,(activeDef===d.id?'● ':'○ ')+(d.kind==='media'?'▧ ':'▤ ')+d.id+(d.kind==='media'?' · '+(d.media.label||d.media.kind):' · grupo'),()=>{activeDef=d.id;refresh();});
      b.style.cssText+=';width:100%;text-align:left';
    }
    const def=library.definitions.find(d=>d.id===activeDef);
    if(!def)return;
    const h=doc.createElement('strong');h.textContent='Definição: '+def.id;editor.append(h);
    if(def.kind==='group'){
      const txt=doc.createElement('p');txt.textContent='Grupo compartilhado. Selecione os membros na hierarquia acima ou exporte/import e a definição.';editor.append(txt);
      return;
    }
    const media=def.media;
    if(media.kind==='image'){
      const img=doc.createElement('img');img.style.cssText='width:100%;max-height:190px;object-fit:contain;border-radius:8px;background:#142332';img.alt='Prévia de '+def.id;
      img.src='/api/media/image?file='+encodeURIComponent(media.file||'');
      img.onerror=()=>{status.textContent='Imagem ausente: '+(media.file||'')+' — use Substituir mídia base.';};editor.append(img);
    }
    if(media.kind==='video'){
      const v=doc.createElement('video');v.muted=true;v.controls=true;v.preload='metadata';v.style.cssText='width:100%;max-height:190px';v.src='/api/media/clip?file='+encodeURIComponent(media.file||'');editor.append(v);
    }
    const fields=doc.createElement('div');fields.style.cssText='display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:8px';editor.append(fields);
    function field(key,label){
      const w=doc.createElement('label');w.textContent=label;w.style.cssText='display:grid;gap:3px;font-size:.85em';
      const inp=doc.createElement('input');inp.value=String(media[key]??'');inp.dataset.key=key;
      if(['x','y','w','h','opacity','rotation'].includes(key)){inp.type='number';inp.step='any';}else inp.type='text';
      w.append(inp);fields.append(w);return inp;
    }
    const label=field('label','Nome da definição');
    const other=media.kind==='gil'?[]:['x','y','w','h','opacity','rotation'].map(k=>field(k,k));
    btn(editor,'Aplicar parâmetros à definição',()=>mutate(()=>{
      const updates={label:label.value};for(const i of other)updates[i.dataset.key]=Number(i.value);
      return replaceDefinitionMedia(project,def.id,updates);
    }));
    if(media.kind==='image'||media.kind==='video'){
      const fileInput=doc.createElement('input');fileInput.type='file';fileInput.accept=media.kind==='image'?'image/*':'video/*';fileInput.hidden=true;editor.append(fileInput);
      btn(editor,'▧ Substituir mídia base (todas as instâncias)',()=>fileInput.click());
      fileInput.onchange=async()=>{const f=fileInput.files?.[0];fileInput.value='';if(!f)return;
        const owner=ctx.project(),defId=def.id,kind=media.kind;
        try{const filename=await ctx.upload(f,kind);
          if(ctx.project()!==owner)throw Error('O projeto mudou durante o upload');
          mutate(()=>replaceDefinitionMedia(owner,defId,{file:filename}));
          status.textContent='Mídia atualizada em todas as instâncias de '+defId;
        }catch(e){ctx.notify(e.message,true);}
      };
    }else{const p=doc.createElement('p');p.textContent='Fonte GIL: exporte/import e um elemento JSON para substituí-la sem perder a integridade dos hashes.';editor.append(p);}
  }
  return {refresh,panel};
}
