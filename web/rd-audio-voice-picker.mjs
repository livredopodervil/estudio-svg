/** RD-Audio voice picker for the existing Audio tab, not another editor. */
const PIPER = [
  {id:'faber', label:'Piper · Faber (offline PT-BR)'},
  {id:'edresson', label:'Piper · Edresson (offline PT-BR)'}
];
let catalogPromise=null;

export function parseEdgeCatalogue(data){
  if(!data || !Array.isArray(data.voices) || !Number.isInteger(data.count) || data.voices.length !== data.count)
    throw Error('Catálogo Edge ausente ou incompleto');
  const seen=new Set();
  return data.voices.map(v=>{
    const name=v?.voice_id;
    if(v?.provider!=='edge' || typeof name!=='string' || !/^[a-zA-Z0-9-]{5,100}$/.test(name) || seen.has(name))
      throw Error('Identificador de voz Edge inválido ou repetido');
    seen.add(name);
    return {id:'edge:'+name, label:`Edge · ${v.locale||'?'} · ${v.name||name}`,locale:v.locale||'',name};
  }).sort((a,b)=>(a.locale==='pt-BR'?0:1)-(b.locale==='pt-BR'?0:1)||a.locale.localeCompare(b.locale)||a.name.localeCompare(b.name));
}
export function filterVoiceOptions(edgeVoices,search=''){
  const term=String(search||'').trim().toLocaleLowerCase();
  const edge=term ? edgeVoices.filter(v=>[v.id,v.name,v.locale,v.label].some(x=>String(x||'').toLocaleLowerCase().includes(term))) : edgeVoices;
  return [...PIPER, ...edge];
}
export async function readEdgeCatalogue(load){
  if(!catalogPromise)catalogPromise=Promise.resolve().then(()=>load('/api/rd-voices/catalog')).then(parseEdgeCatalogue).catch(e=>{catalogPromise=null;throw e;});
  return catalogPromise;
}
export function resetEdgeCatalogue(){catalogPromise=null;}

export async function mountVoicePicker(select,search,status,load){
  if(!select || !search)return;
  const live=()=>select.isConnected && search.isConnected;
  let voices=[];
  const update=()=>{
    if(!live())return;
    const old=select.value;
    const options=filterVoiceOptions(voices,search.value);
    // Never drop an already selected voice when filtering.
    if(old&&!options.some(x=>x.id===old)){
      const current=voices.find(x=>x.id===old)||PIPER.find(x=>x.id===old);
      if(current)options.unshift(current);
    }
    select.replaceChildren(...options.map(v=>new Option(v.label,v.id)));
    if(old&&options.some(v=>v.id===old))select.value=old;
  };
  search.addEventListener('input',update);
  update();
  if(status)status.textContent='Carregando catálogo Edge…';
  try {
    voices=await readEdgeCatalogue(load);
    if(!live())return;
    update();
    if(status)status.textContent=`Edge: ${voices.length} vozes disponíveis; Piper permanece offline. Digite para filtrar.`;
  }catch(e){
    if(live()&&status)status.textContent='Edge indisponível: '+e.message+'. Piper continua disponível; verifique /api/rd-voices/catalog.';
  }
}
