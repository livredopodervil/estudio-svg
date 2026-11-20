/** Catalog-driven choices in the existing RD Audio editor (no extra panel).
 * Status must be honest: unavailable voices are shown, but cannot be selected.
 */
let promise=null;
export function normalizeCatalog(data){
  if(!data||!Array.isArray(data.voices)||data.count!==data.voices.length)throw Error('Catálogo de vozes inválido');
  const seen=new Set();return data.voices.filter(v=>{
    if(!v||typeof v.id!=='string'||!v.id.includes(':')||seen.has(v.id))return false;
    seen.add(v.id);return true;
  });
}
export function filterVoices(items,query){
 const q=String(query||'').trim().toLocaleLowerCase();
 return items.filter(v=>!q||[v.id,v.name,v.locale,v.provider].some(x=>String(x||'').toLocaleLowerCase().includes(q)))
 .sort((a,b)=>Number(b.locale==='pt-BR')-Number(a.locale==='pt-BR')||a.provider.localeCompare(b.provider)||String(a.locale).localeCompare(String(b.locale))||String(a.name).localeCompare(String(b.name)));
}
export function browserVoices(synth){
 try{return (synth?.getVoices?.()||[]).filter(v=>v.voiceURI).map(v=>({
 id:'browser:'+v.voiceURI,provider:'browser',name:v.name,locale:v.lang||'und',
 available:false,exportable:false,online:null,status:'Somente prévia; não exportável neste roteiro'
 }));}catch{return []}
}
export async function mountAllVoices(select,search,status,request,synth){
 if(!select)return;
 const attached=()=>select.isConnected;
 const render=items=>{
   if(!attached())return;
   const old=select.value;
   const filtered=filterVoices(items,search?.value);
   if(old&&!filtered.some(v=>v.id===old)){
      const existing=items.find(v=>v.id===old);
      if(existing)filtered.unshift(existing);
   }
   select.replaceChildren(...filtered.map(v=>{
     const label=`${v.provider} · ${v.locale||'und'} · ${v.name||v.voice_id||v.id}${v.exportable===false?' [prévia apenas]':v.available?'':' [indisponível]'}`;
     const o=new Option(label,v.id);o.disabled=!v.available;o.title=v.status||(!v.exportable?'Prévia apenas':'');return o;
   }));
   if(old&&filtered.some(v=>v.id===old))select.value=old;
   else if(filtered.length&&filtered[0].available)select.value=filtered[0].id;
 };
 const items=browserVoices(synth);
 let active=items;
 const onChange=()=>render(active);
 search?.addEventListener('input',onChange,{signal:undefined});
 render(active);
 if(status)status.textContent='Carregando catálogo do Termux…';
 try{
   if(!promise)promise=Promise.resolve().then(()=>request('/api/rd-voices/installed')).then(data=>({data,voices:normalizeCatalog(data)})).catch(e=>{promise=null;throw e;});
   const {data,voices}=await promise;
   if(!attached())return;
   active=[...voices,...items];render(active);
   const piperSelect=document.getElementById('rdPiperVoice');
   if(piperSelect?.isConnected){
      const prior=piperSelect.value;
      const piper=voices.filter(v=>v.provider==='piper'&&v.available);
      piperSelect.replaceChildren(...piper.map(v=>new Option(v.name,v.voice_id)));
      if(piper.some(v=>v.voice_id===prior))piperSelect.value=prior;
   }
   if(status)status.textContent=`${voices.length} vozes no catálogo; ${voices.filter(x=>x.available).length} disponíveis para geração. ${data.warnings?.join('; ')||''}`;
   if(!document.getElementById('rdEdgeRefresh')){
      const update=document.createElement('button');update.type='button';update.id='rdEdgeRefresh';update.textContent='Atualizar catálogo Edge';
      status?.after(update);
      update.addEventListener('click',async()=>{
        update.disabled=true;status.textContent='Consultando catálogo Edge na rede…';
        try{
          const r=await fetch('/api/rd-voices/refresh',{method:'POST',credentials:'same-origin'});
          const obj=await r.json();if(!r.ok)throw Error(obj.error||'Falha ao atualizar vozes');
          promise=null;await mountAllVoices(select,search,status,request,synth);
        }catch(e){status.textContent='Erro Edge: '+e.message;}
        finally{if(update.isConnected)update.disabled=false;}
      });
   }
 }catch(e){if(attached()&&status)status.textContent='Catálogo indisponível: '+e.message;}
}
export function clearVoiceCache(){promise=null}
