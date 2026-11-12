(()=>{'use strict';
const $=id=>document.getElementById(id), cp=o=>JSON.parse(JSON.stringify(o));
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const types=['globo','linha','barras','numero','cartoes','arvore','svg','foto'];
const names={globo:'Globo',linha:'Linhas',barras:'Barras',numero:'Número',cartoes:'Cartões',arvore:'Árvore fractal',svg:'SVG personalizado',foto:'Fotografia'};
const presets={'16:9':[1280,720],'9:16':[720,1280],'1:1':[800,800],'4:5':[800,1000],'21:9':[1260,540]};
const sceneBase=()=>({id:'cena_'+Date.now(),tipo:'cartoes',duracao:7,titulo:'NOVA CENA',subtitulo:'Descreva o assunto',fala:'',categoria:'ESTÚDIO SVG',fonte:'',movimento:'suave',itens:['Novo item','Mais uma informação'],dados:[[1,1],[2,2],[3,3]],valor:'',unidade:'',sufixo:'',destaque:'',svg:'<circle cx="650" cy="350" r="160" fill="#e8a770"/>',imagem:{arquivo:'',fit:'cover',align_x:.5,align_y:.5,bg:'#241b1a',crop:[]},cores:{fundo:'#241b1a',destaque:'#d99a62',texto:'#fff1da'},audio:{voice_text:'',voice_enabled:false,voice_file:'',voice_volume:1,voice_delay:.12,music_file:'',music_volume:.16,duck_music:false,tracks:[]}});
let project=null,projectName='',selected=0,tab='scene',dirty=false,saving=false,playing=false,playTime=0,lastFrame=0,previewBusy=false,previewPending=false,jobTimer=null,busy=false,assetPath=null,cacheInfo=null,selectedPane='previewPanel';
const api=async(path,options={})=>{const response=await fetch(path,options);const kind=response.headers.get('Content-Type')||'';let v=kind.includes('json')?await response.json():await response.text();if(!response.ok)throw Error(v.error||'HTTP '+response.status);return v;};
const post=(path,body)=>api(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
function toast(t,bad=false){const el=$('toast');el.textContent=t;el.style.borderColor=bad?'#e58b7d':'#c7996c';el.classList.add('show');setTimeout(()=>el.classList.remove('show'),3600);}
function sec(t){return Math.floor(t/60).toString().padStart(2,'0')+':'+Math.floor(t%60).toString().padStart(2,'0');}
function totalDuration(){return project.cenas.reduce((n,c)=>n+Number(c.duracao),0);}
function startOf(i){return project.cenas.slice(0,i).reduce((n,c)=>n+Number(c.duracao),0);}
function sceneAt(t){let sum=0;for(let i=0;i<project.cenas.length;i++){let d=Number(project.cenas[i].duracao);if(t<sum+d||i===project.cenas.length-1)return {i,progress:Math.max(0,Math.min(1,(t-sum)/Math.max(.5,d)))};sum+=d;}return {i:0,progress:0};}
function getPath(path){let keys=path.split('.'),obj=project;for(let k of keys)obj=obj[k];return obj;}
function setPath(path,value){let ks=path.split('.'),obj=project;for(let j=0;j<ks.length-1;j++)obj=obj[ks[j]];obj[ks[ks.length-1]]=value;}
const variant=(options,current)=>options.map(([v,t])=>`<option value="${esc(v)}" ${String(v)===String(current)?'selected':''}>${esc(t)}</option>`).join('');
function field(label,path,type='text',choices=null,hint=''){
 const val=getPath(path);let inner='';const tag=`data-path="${esc(path)}"`;
 if(type==='textarea')inner=`<textarea ${tag} ${path.endsWith('.svg')?'class="code"':''} rows="${path.endsWith('.svg')?9:4}">${esc(val)}</textarea>`;
 else if(type==='select')inner=`<select ${tag}>${variant(choices,val)}</select>`;
 else if(type==='checkbox')inner=`<input ${tag} type="checkbox" ${val?'checked':''}>`;
 else if(type==='color')inner=`<input ${tag} type="color" value="${esc(val)}">`;
 else inner=`<input ${tag} type="${type}" ${type==='number'?'step="any"':''} value="${esc(val)}">`;
 return `<div class="formField"><label>${esc(label)}</label>${inner}${hint?`<div class="fieldHint">${esc(hint)}</div>`:''}</div>`;
}
function action(name,title='Enviar arquivo'){return `<button type="button" data-upload="${esc(name)}">${esc(title)}</button>`;}
function drawEditor(){if(!project)return;const s=project.cenas[selected],a=s.audio;$('editor').innerHTML=tab==='project'?renderProject():tab==='audio'?renderAudio():renderScene();}
function renderProject(){let h='<div class="sectionTitle">Configuração global</div>';
 h+=field('Título','titulo');
 const [w,hh]=[project.video.width,project.video.height];const current=Object.keys(presets).find(x=>presets[x][0]===w&&presets[x][1]===hh)||'custom';
 h+=`<div class="formField"><label>Formato de vídeo</label><select id="preset"><option value="custom" ${current==='custom'?'selected':''}>Personalizado</option>${Object.keys(presets).map(x=>`<option ${x===current?'selected':''}>${x}</option>`).join('')}</select></div>`;
 h+=field('Largura (pixels pares)','video.width','number');h+=field('Altura (pixels pares)','video.height','number');
 h+=field('Quadros finais por segundo','video.fps','select',[[24,'24'],[25,'25'],[30,'30']]);
 h+=field('Quadros SVG gerados por segundo','video.draw_fps','select',[[1,'1 (rápido)'],[2,'2'],[3,'3'],[4,'4'],[6,'6'],[8,'8'],[10,'10'],[12,'12'],[15,'15'],[24,'24 (lento)']]);
 h+=field('Cor de fundo','video.background','color');
 h+='<div class="sectionTitle">Narração global</div>';
 h+=field('Motor de síntese para o MP4','motor_voz','select',[
   ['edge-tts','Edge neural (internet)'],['espeak-ng','eSpeak NG (offline, voz simples)'],
   ['piper','Piper (neural offline, modelo ONNX necessário)']]);
 h+=field('Voz eSpeak NG (ex.: pt-br)','voz_espeak');
 h+=field('Velocidade eSpeak NG (palavras/minuto)','velocidade_espeak','number');
 h+=field('Modelo Piper em modelos/ (ex.: voz.onnx)','modelo_piper');
 h+='<p class="smallNote">A voz Android usa o botão de audição, sem gerar arquivos. Para MP4 sem internet: eSpeak NG ou Piper com modelo instalado. Escolher outro motor só invalida cache de voz, não os quadros.</p>';

 h+=field('Voz','voz','select',[['pt-BR-AntonioNeural','Antônio (brasileiro)'],['pt-BR-FranciscaNeural','Francisca (brasileira)']]);
 h+=field('Velocidade (ex.: +0%, -10%)','velocidade_voz');
 h+=field('Se voz exceder a cena','encaixe_voz','select',[['estender','Estender a cena'],['avisar','Interromper e avisar']]);
 h+=field('Volume geral da voz','volume_voz','number');h+=field('Volume de trilha global','volume_musica','number');
 h+=field('Arquivo de música global','trilha');h+=action('trilha','Importar música global');
 h+='<p class="smallNote">Mudar resolução ou FPS invalida o cache visual de todas as cenas. Mudar a voz não invalida os quadros.</p>';
 return h;
}
function renderScene(){let h='<div class="sectionTitle">Cena '+(selected+1)+' · Visual</div>';
 h+=field('Identificador','cenas.'+selected+'.id');
 h+=field('Tipo','cenas.'+selected+'.tipo','select',types.map(t=>[t,names[t]]));
 h+=field('Duração mínima (s)','cenas.'+selected+'.duracao','number');
 for(let x of [['titulo','Título'],['subtitulo','Subtítulo'],['categoria','Selo editorial'],['fonte','Fonte bibliográfica']])h+=field(x[1],'cenas.'+selected+'.'+x[0]);
 h+=field('Movimento','cenas.'+selected+'.movimento','select',[['suave','Suave'],['linear','Linear'],['entrada','Aceleração'],['saida','Desaceleração']]);
 for(let k of [['fundo','Cor de fundo'],['destaque','Cor de destaque'],['texto','Cor do texto']])h+=field(k[1],`cenas.${selected}.cores.${k[0]}`,'color');
 if(sType('linha','barras')){
  const list=getPath(`cenas.${selected}.dados`).map(x=>Array.isArray(x)?x.join(', '):x.x+', '+x.y).join('\n');
  h+=`<div class="formField"><label>Dados (categoria, valor por linha)</label><textarea id="dataPairs" rows="7">${esc(list)}</textarea><small class="fieldHint">Exemplo: 2022, 8\n2085, 10.3</small></div>`;
 }
 if(sType('globo','cartoes')){
  h+=`<div class="formField"><label>Itens, um por linha</label><textarea id="itemsText">${esc(getPath(`cenas.${selected}.itens`).join('\n'))}</textarea></div>`;
 }
 if(sType('numero'))for(let [k,l] of [['valor','Valor'],['unidade','Unidade'],['sufixo','Texto adicional']])h+=field(l,`cenas.${selected}.${k}`);
 if(sType('arvore'))h+=field('Texto de destaque',`cenas.${selected}.destaque`);
 if(sType('svg')){
  h+=field('Fragmento SVG (sem <svg> externo)',`cenas.${selected}.svg`,'textarea');
  h+='<div class="inline"><button data-shape="circle">+ Círculo</button><button data-shape="rect">+ Retângulo</button><button data-shape="path">+ Curva</button><button data-shape="text">+ Texto</button></div>';
 }
 if(sType('foto')){
  h+='<div class="sectionTitle">Imagem e enquadramento</div>';
  h+=field('Imagem importada',`cenas.${selected}.imagem.arquivo`);
  h+=action(`cenas.${selected}.imagem.arquivo`,'Importar imagem');
  h+=field('Modo de ajuste',`cenas.${selected}.imagem.fit`,'select',[['cover','Preencher e recortar'],['contain','Mostrar inteira'],['pad','Inteira com fundo'],['stretch','Esticar'],['crop','Recorte definido']]);
  h+=field('Posição horizontal (0 a 1)',`cenas.${selected}.imagem.align_x`,'number');
  h+=field('Posição vertical (0 a 1)',`cenas.${selected}.imagem.align_y`,'number');
  h+=field('Cor de preenchimento',`cenas.${selected}.imagem.bg`,'color');
  h+=`<div class="formField"><label>Recorte relativo (x, y, largura, altura) — números de 0 a 1</label><input id="cropInput" value="${esc(sImgCrop())}"></div>`;
 }
 h+='<div class="separator"></div><div class="inline"><button id="duplicateScene">Duplicar cena</button><button id="removeScene">Excluir cena</button><button id="moveUp">↑ Subir</button><button id="moveDown">↓ Descer</button></div>';
 return h;
}
function sType(...choices){return choices.includes(project.cenas[selected].tipo);}
function sImgCrop(){return (project.cenas[selected].imagem.crop||[]).join(', ');}
function renderAudio(){let h='<div class="sectionTitle">Narração e áudio da cena '+(selected+1)+'</div>';
 h+=field('Ativar narração',`cenas.${selected}.audio.voice_enabled`,'checkbox');
 h+=field('Texto para voz neural',`cenas.${selected}.audio.voice_text`,'textarea','', 'Síntese gerada apenas quando você tocar em Áudio em lote.');
 h+=field('Voz gravada (substitui o texto neural)',`cenas.${selected}.audio.voice_file`);
 h+=action(`cenas.${selected}.audio.voice_file`,'Importar locução pronta');
 h+=field('Volume da voz nesta cena',`cenas.${selected}.audio.voice_volume`,'number');
 h+=field('Atraso da voz (segundos)',`cenas.${selected}.audio.voice_delay`,'number');
 h+='<div class="sectionTitle">Música da cena</div>';
 h+=field('Trilha específica (vazio: usa a global)',`cenas.${selected}.audio.music_file`);
 h+=action(`cenas.${selected}.audio.music_file`,'Importar trilha da cena');
 h+=field('Volume da trilha específica',`cenas.${selected}.audio.music_volume`,'number');
 h+=field('Abaixar música com voz',`cenas.${selected}.audio.duck_music`,'checkbox');
 h+='<div class="sectionTitle">Faixas extras: efeitos, ambientes e outras vozes</div>';
 for(let [i,tr] of project.cenas[selected].audio.tracks.entries()){
   let p=`cenas.${selected}.audio.tracks.${i}`;
   h+=`<div class="track"><div class="trackHead"><h4>Faixa ${i+1}</h4><button data-remove-track="${i}">Remover</button></div>`;
   h+=field('Arquivo de áudio',p+'.file');h+=action(p+'.file','Importar faixa');
   h+=field('Começa em (segundos)',p+'.start','number');h+=field('Volume',p+'.volume','number');
   h+=field('Fade in (s)',p+'.fade_in','number');h+=field('Fade out (s)',p+'.fade_out','number');
   h+=field('Repetir até terminar a cena',p+'.loop','checkbox');h+='</div>';
 }
 h+='<button id="addTrack">+ Nova faixa independente</button><p class="smallNote">As vozes são reutilizadas por texto. Modificar somente o volume ou os efeitos refaz a mixagem, não a animação.</p>';
 return h;
}
function dirtyNow(redraw=false){dirty=true;$('saveInfo').textContent='● Há alterações não salvas';if(redraw)drawEverything();else showPreview();}
async function save(force=false){if(!project||(!dirty&&!force))return;
 if(saving)return; saving=true;
 try{const d=await post('/api/project',{name:projectName,project});dirty=false;$('saveInfo').textContent='✓ Salvo no aparelho';}finally{saving=false;}}
function drawSceneList(){const l=$('sceneList');l.innerHTML=project.cenas.map((s,i)=>`<div class="sceneItem ${i===selected?'active':''}"><button class="scenePick" data-scene="${i}"><small>${String(i+1).padStart(2,'0')} · ${esc(names[s.tipo]||s.tipo)} · ${s.duracao}s</small><b>${esc(s.titulo||'Sem título')}</b><small>${s.audio.voice_enabled?'♫ voz':'sem voz'}</small></button><div class="sceneOrder"><button data-shift="-1" data-index="${i}">↑</button><button data-shift="1" data-index="${i}">↓</button></div></div>`).join('');$('sceneCount').textContent=project.cenas.length;}
function drawTimeline(){const total=totalDuration();$('timeline').innerHTML=project.cenas.map((s,i)=>`<button class="${selected===i?'active':''}" data-scene="${i}" style="width:${Math.max(94,Math.min(230,Math.floor(s.duracao/total*680)))}px">${i+1}. ${esc(s.titulo)}</button>`).join('');}
function drawEverything(){if(!project)return;drawSceneList();drawTimeline();drawEditor();$('stage').style.aspectRatio=project.video.width+'/'+project.video.height;$('formatInfo').textContent=`${project.video.width} × ${project.video.height} · ${project.video.fps} FPS`;showPreview();}
function jump(i){clearMediaPlayers();selected=Math.max(0,Math.min(project.cenas.length-1,i));playTime=startOf(selected);drawEverything();}
function tick(ts){if(!playing)return;if(lastFrame){playTime=Math.min(totalDuration(),playTime+(ts-lastFrame)/1000);}lastFrame=ts;
 if(playTime>=totalDuration()){playing=false;$('playButton').textContent='▶';}
 const ix=sceneAt(playTime).i;if(ix!==selected){clearMediaPlayers();selected=ix;drawSceneList();drawTimeline();drawEditor();}
 showPreview();if(playing)requestAnimationFrame(tick);
}
async function showPreview(){if(!project)return;
 $('timeInfo').textContent=sec(playTime)+' / '+sec(totalDuration());$('seek').value=totalDuration()?Math.round(playTime/totalDuration()*1000):0;
 if(previewBusy){previewPending=true;return;}previewBusy=true;const s=sceneAt(playTime);
 try{const svg=await post('/api/preview',{scene:project.cenas[s.i],video:project.video,progress:s.progress,index:s.i,total:project.cenas.length});$('stage').innerHTML=svg;}
 catch(e){$('stage').textContent='Falha na prévia: '+e.message;}
 finally{previewBusy=false;if(previewPending){previewPending=false;setTimeout(showPreview,80);}}
}
async function listProjects(){const r=await api('/api/projects');$('projectSelect').innerHTML=r.projects.map(x=>`<option value="${esc(x)}">${esc(x)}</option>`).join('');return r.projects;}
async function load(name){if(dirty)await save();clearMediaPlayers();let r=await api('/api/project?name='+encodeURIComponent(name));project=r.project;projectName=name;selected=0;playTime=0;playing=false;dirty=false;$('projectSelect').value=name;$('saveInfo').textContent='✓ Carregado';drawEverything();refreshCache();}
async function refreshCache(){if(!project)return;try{let r=await api('/api/cache/status?name='+encodeURIComponent(projectName));cacheInfo=r.scenes;$('cacheTable').innerHTML=r.scenes.map(c=>`<div class="cacheItem"><b>${c.index}. ${esc(c.title)}</b><small><span class="${c.visual?'check':'missing'}">Visual ${c.visual?'✓':'·'}</span> · <span class="${c.audio?'check':'missing'}">Áudio ${c.audio?'✓':'·'}</span> · <span class="${c.voice?'check':'missing'}">Voz ${c.voice?'✓':'·'}</span></small><br><small>${c.seconds.toFixed(2)} s</small><br><button data-clear="${c.index}">Limpar cache desta cena</button></div>`).join('');}catch(e){$('cacheTable').textContent='Cache: '+e.message;}}
async function begin(mode,no_voice=false){if(busy)return toast('Já existe um trabalho em execução',true);try{await save();let j=await post('/api/job',{name:projectName,mode,scene:mode==='cena'?selected+1:undefined,no_voice});busy=true;$('downloads').innerHTML='';$('logBox').textContent='';trackJob(j.job);}catch(e){toast(e.message,true);}}
function trackJob(id){if(jobTimer)clearInterval(jobTimer);busy=true;$('statusBadge').textContent='Executando';
 const poll=async()=>{try{const j=await api('/api/job/'+id);$('progress').value=Math.round(j.progress*100);$('progressText').textContent=Math.round(j.progress*100)+'%';$('phase').textContent=j.phase;$('logBox').textContent=j.logs.join('\n');$('logBox').scrollTop=$('logBox').scrollHeight;
 if(['done','error'].includes(j.status)){
    clearInterval(jobTimer);jobTimer=null;busy=false;$('statusBadge').textContent=j.status==='done'?'Concluído':'Erro';
    if(j.status==='error'){toast(j.error,true);return;}
    let files=[];if(j.result.video)files.push(['MP4',j.result.video]);if(j.result.frames)files.push(['Quadros ZIP',j.result.frames]);if(j.result.batch)files.push(['Áudio ZIP',j.result.batch]);if(j.result.audio)files.push(['Mix WAV',j.result.audio]);
    $('downloads').innerHTML=files.map(([t,f])=>`<a download href="/api/output/${encodeURIComponent(f)}">↓ ${esc(t)} — ${esc(f)}</a>`).join('');toast(j.result.cached?'Resultado reutilizado do cache':'Produção concluída');refreshCache();
 }
 }catch(e){$('phase').textContent='Erro de conexão: '+e.message;}};
 poll();jobTimer=setInterval(poll,1200);switchPane('workPanel');}

function clearMediaPlayers(){
 const a=$('voicePlayer'),v=$('scenePlayer');
 try{a.pause();a.removeAttribute('src');a.load();v.pause();v.removeAttribute('src');v.load();v.hidden=true;}catch(e){}
 $('mediaStatus').textContent='Cena '+(selected+1)+': escolha o áudio ou vídeo para ouvir.';
}
async function playSceneAudio(kind){
 try{
  await save(); const a=$('voicePlayer');$('scenePlayer').pause();$('scenePlayer').hidden=true;
  a.pause();a.src='/api/scene/media?name='+encodeURIComponent(projectName)+'&scene='+(selected+1)+'&kind='+kind+'&ts='+Date.now();
  $('mediaStatus').textContent=kind==='voice'?'Locução gerada (sem música)':'Mixagem final da cena';
  await a.play();
 }catch(e){toast('Áudio indisponível: gere Áudio em lote ou Renderizar cena. '+e.message,true);}
}
async function watchSceneVideo(){
 try{
  await save();$('mediaStatus').textContent='Preparando prévia com os trechos já armazenados...';
  const r=await post('/api/scene/preview',{name:projectName,scene:selected+1});
  $('voicePlayer').pause();const v=$('scenePlayer');v.src=r.url;v.hidden=false;
  await v.play();$('mediaStatus').textContent='Prévia MP4 da cena '+(selected+1)+' com áudio.';
 }catch(e){$('mediaStatus').textContent='Para assistir, clique antes em Renderizar cena ou Renderizar MP4.';toast(e.message,true);}
}
async function listenAndroid(){
 try{await save();const r=await post('/api/tts/android',{name:projectName,scene:selected+1});
 $('mediaStatus').textContent=r.message;toast('Reprodução solicitada ao motor do Android');}
 catch(e){toast(e.message,true);}
}
function switchPane(id){selectedPane=id;document.querySelectorAll('.mobileTabs button').forEach(b=>b.classList.toggle('on',b.dataset.pane===id));document.querySelectorAll('.panel').forEach(p=>p.classList.toggle('mobileActive',p.id===id));}
function exportJSON(){let blob=new Blob([JSON.stringify(project,null,2)],{type:'application/json'});let u=URL.createObjectURL(blob);let a=document.createElement('a');a.href=u;a.download=projectName+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(u),2000);}
async function upload(file,path){if(!file)return;if(file.size>12e6)return toast('Arquivo máximo: 12 MB',true);
 let kind=path.endsWith('imagem.arquivo')?'image':'audio';const data=await new Promise((yes,no)=>{let fr=new FileReader();fr.onload=()=>yes(fr.result);fr.onerror=no;fr.readAsDataURL(file);});
 try{const r=await post('/api/upload',{kind,data,filename:file.name});setPath(path,r.filename);dirtyNow(true);drawEditor();toast('Arquivo importado: '+r.filename);}catch(e){toast(e.message,true);}}
function moveScene(i,shift){clearMediaPlayers();let j=i+shift;if(j<0||j>=project.cenas.length)return;[project.cenas[i],project.cenas[j]]=[project.cenas[j],project.cenas[i]];selected=j;playTime=startOf(selected);dirtyNow(true);}
function parseFields(e){let el=e.target;const path=el.dataset.path;if(path){let v=el.type==='checkbox'?el.checked:el.value;if(el.type==='number'){v=Number(v);if(!Number.isFinite(v))return;}setPath(path,v);
   if(path.endsWith('voice_text')){setPath(`cenas.${selected}.fala`,v);if(v.trim())setPath(`cenas.${selected}.audio.voice_enabled`,true);}
   if(path.endsWith('.id')&&!/^[A-Za-z0-9_-]{1,64}$/.test(v))return toast('ID inválido',true);
   if(path.startsWith('video.')){drawEverything();}
   dirtyNow(path.endsWith('.tipo')||path.endsWith('.fit'));return;
 }
 if(el.id==='preset'&&presets[el.value]){[project.video.width,project.video.height]=presets[el.value];dirtyNow(true);}
 if(el.id==='dataPairs'){
   let pts=el.value.trim().split(/\r?\n/).map(r=>r.split(/[,;\t]/).map(x=>x.trim())).filter(p=>p.length>=2&&Number.isFinite(Number(p[1]))).map(p=>[p[0],Number(p[1])]);
   project.cenas[selected].dados=pts;dirtyNow();
 }
 if(el.id==='itemsText'){project.cenas[selected].itens=el.value.split(/\r?\n/).map(x=>x.trim()).filter(Boolean);dirtyNow();}
 if(el.id==='cropInput'){
   const v=el.value.trim();const nums=v?v.split(/[ ,;]+/).map(Number):[];
   if(nums.length&&!(nums.length===4&&nums.every(x=>Number.isFinite(x)&&x>=0&&x<=1)))return toast('Recorte: quatro números entre 0 e 1',true);
   project.cenas[selected].imagem.crop=nums;dirtyNow();
 }
}
function bind(){
 $('projectSelect').onchange=e=>load(e.target.value).catch(x=>toast(x.message,true));
 $('saveButton').onclick=()=>save(true).then(()=>toast('Salvo no celular')).catch(e=>toast(e.message,true));
 $('newProject').onclick=async()=>{let n=prompt('Nome identificador, sem espaços:','novo_projeto');if(!n)return;try{let r=await post('/api/project/new',{name:n,titulo:'Meu documentário'});await listProjects();await load(r.name);toast('Projeto criado');}catch(e){toast(e.message,true);}};
 $('exportButton').onclick=exportJSON;$('importButton').onclick=()=>$('jsonFile').click();
 $('jsonFile').onchange=async e=>{const f=e.target.files[0];if(!f)return;try{const data=JSON.parse(await f.text());let n=prompt('Nome do projeto importado:',f.name.replace(/\.json$/i,'').replace(/[^A-Za-z0-9_-]/g,'_'));if(!n)return;await post('/api/project',{name:n,project:data});await listProjects();await load(n);toast('JSON importado e migrado');}catch(e){toast(e.message,true);}e.target.value='';};
 $('sceneList').onclick=e=>{let mv=e.target.closest('[data-shift]');if(mv)return moveScene(Number(mv.dataset.index),Number(mv.dataset.shift));let b=e.target.closest('[data-scene]');if(b)jump(Number(b.dataset.scene));};
 $('timeline').onclick=e=>{let b=e.target.closest('[data-scene]');if(b)jump(Number(b.dataset.scene));};
 $('addScene').onclick=()=>{project.cenas.splice(selected+1,0,sceneBase());selected++;playTime=startOf(selected);dirtyNow(true);};
 $('addSvgScene').onclick=()=>{let c=sceneBase();c.tipo='svg';c.titulo='ILUSTRAÇÃO VETORIAL';c.svg='<g class="layer" id="camada1"><title>Camada 1</title><circle cx="640" cy="360" r="125" fill="#d99a62"/></g>';project.cenas.splice(selected+1,0,c);selected++;playTime=startOf(selected);dirtyNow(true);};
 $('editSVG').onclick=async()=>{
  if(project.cenas[selected].tipo!=='svg')return toast('Selecione uma cena SVG ou use + SVG para criar uma.',true);
  const popup=window.open('about:blank','_blank');
  try{await save();const url='/vetor?name='+encodeURIComponent(projectName)+'&scene='+(selected+1);if(popup)popup.location.href=url;else window.location.href=url;}
  catch(e){if(popup)popup.close();toast('Não foi possível abrir o editor: '+e.message,true);}
 };

 $('playButton').onclick=()=>{playing=!playing;lastFrame=0;if(playing&&playTime>=totalDuration())playTime=0;$('playButton').textContent=playing?'Ⅱ':'▶';if(playing)requestAnimationFrame(tick);};
 $('seek').oninput=e=>{playTime=totalDuration()*Number(e.target.value)/1000;selected=sceneAt(playTime).i;drawSceneList();drawTimeline();showPreview();};
 document.querySelectorAll('.mobileTabs button').forEach(b=>b.onclick=()=>switchPane(b.dataset.pane));
 document.querySelectorAll('[data-edit]').forEach(b=>b.onclick=()=>{tab=b.dataset.edit;document.querySelectorAll('[data-edit]').forEach(k=>k.classList.toggle('on',k===b));drawEditor();});
 $('editor').addEventListener('change',parseFields);
 $('editor').onclick=e=>{
  let t=e.target;if(t.dataset.upload){assetPath=t.dataset.upload;$('mediaFile').accept=assetPath.endsWith('imagem.arquivo')?'image/*':'audio/*';$('mediaFile').click();return;}
  if(t.dataset.removeTrack!==undefined){project.cenas[selected].audio.tracks.splice(Number(t.dataset.removeTrack),1);dirtyNow(true);}
  if(t.id==='addTrack'){project.cenas[selected].audio.tracks.push({file:'',start:0,volume:.4,fade_in:0,fade_out:0,loop:false});dirtyNow(true);}
  if(t.id==='duplicateScene'){let dup=cp(project.cenas[selected]);dup.id='cena_'+Date.now();project.cenas.splice(++selected,0,dup);playTime=startOf(selected);dirtyNow(true);}
  if(t.id==='removeScene'){if(project.cenas.length<=1)return toast('O projeto precisa ter uma cena',true);if(!confirm('Excluir cena '+(selected+1)+'?'))return;project.cenas.splice(selected,1);selected=Math.max(0,selected-1);playTime=startOf(selected);dirtyNow(true);}
  if(t.id==='moveUp')moveScene(selected,-1);if(t.id==='moveDown')moveScene(selected,1);
  if(t.dataset.shape){const shapes={circle:'<circle cx="640" cy="360" r="135" fill="#d99a62"/>',rect:'<rect x="425" y="255" width="430" height="210" rx="65" fill="#d99a62"/>',path:'<path d="M250,510 Q460,200 640,450 T1030,250" fill="none" stroke="#d99a62" stroke-width="25"/>',text:'<text x="640" y="365" text-anchor="middle" font-size="76" fill="#d99a62">OLÁ</text>'};project.cenas[selected].svg+='\n'+shapes[t.dataset.shape];dirtyNow(true);}
 };
 $('mediaFile').onchange=e=>{upload(e.target.files[0],assetPath);e.target.value='';};
 $('listenVoice').onclick=()=>playSceneAudio('voice');$('listenMix').onclick=()=>playSceneAudio('audio');
 $('watchScene').onclick=watchSceneVideo;$('listenAndroid').onclick=listenAndroid;
 $('makeFrames').onclick=()=>begin('quadros');$('makeAudio').onclick=()=>begin('audio');$('mixAudio').onclick=()=>begin('mix');$('makeLite').onclick=()=>begin('render-leve');$('presentBtn').onclick=async()=>{try{await save();window.open('/captura?name='+encodeURIComponent(projectName),'_blank');}catch(e){toast(e.message,true);}};$('makeVideo').onclick=()=>begin('render');$('makeSilent').onclick=()=>begin('render',true);$('makeScene').onclick=()=>begin('cena');$('refreshCache').onclick=refreshCache;
 $('cacheTable').onclick=async e=>{let b=e.target.closest('[data-clear]');if(!b)return;const scene=Number(b.dataset.clear);if(!confirm('Remover cache visual e sonoro da cena '+scene+'?'))return;try{await post('/api/cache/clear',{name:projectName,scene});await refreshCache();toast('Cache da cena limpo');}catch(e){toast(e.message,true);}};
 document.addEventListener('keydown',e=>{if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='s'){e.preventDefault();save().catch(x=>toast(x.message,true));}});
 window.addEventListener('beforeunload',e=>{if(dirty){e.preventDefault();e.returnValue='';}});
}
async function syncVectorSave(name,scene){
 if(!project||projectName!==name)return;
 if(dirty){toast('Uma cena foi alterada no editor vetorial. Salve ou descarte suas alterações locais antes de recarregar.',true);return;}
 const keep=selected;
 try{
  let r=await api('/api/project?name='+encodeURIComponent(projectName));
  project=r.project;selected=Math.max(0,Math.min(keep,project.cenas.length-1));playTime=startOf(selected);
  drawEverything();refreshCache();toast('Desenho vetorial atualizado no Estúdio');
 }catch(e){toast('Falha ao atualizar a cena: '+e.message,true);}
}
async function init(){
 window.addEventListener('storage',e=>{
  if(e.key!=='estudioSvgVectorSave'||!e.newValue)return;
  try{const u=JSON.parse(e.newValue);syncVectorSave(u.name,u.scene);}catch(err){}
 });
 bind();try{let projects=await listProjects();let preferred=projects.includes('demo_organico')?'demo_organico':projects[0];if(!preferred)throw Error('Nenhum projeto encontrado');await load(preferred);switchPane('previewPanel');let a=await api('/api/jobs/active');if(a.job)trackJob(a.job);}catch(e){toast(e.message,true);$('stage').textContent='Falha ao iniciar: '+e.message;}}
init();
})();
