(()=>{'use strict';
const $=id=>document.getElementById(id), cp=o=>JSON.parse(JSON.stringify(o));
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const types=['globo','linha','barras','numero','cartoes','arvore','svg','foto','espacial'];
const names={globo:'Globo',linha:'Linhas',barras:'Barras',numero:'Número',cartoes:'Cartões',arvore:'Árvore fractal',svg:'SVG personalizado',foto:'Fotografia',espacial:'Espacial 3D (experimental)'};
const presets={'16:9':[1280,720],'9:16':[720,1280],'1:1':[800,800],'4:5':[800,1000],'21:9':[1260,540]};
const sceneBase=()=>({id:'cena_'+Date.now(),tipo:'cartoes',duracao:7,titulo:'NOVA CENA',subtitulo:'Descreva o assunto',fala:'',categoria:'ESTÚDIO SVG',fonte:'',movimento:'suave',itens:['Novo item','Mais uma informação'],dados:[[1,1],[2,2],[3,3]],valor:'',unidade:'',sufixo:'',destaque:'',svg:'<circle cx="650" cy="350" r="160" fill="#e8a770"/>',animacoes:[],video_clipe:{arquivo:'',x:.5,y:.56,w:.70,h:.40,fit:'cover',inicio:0,repetir:true,opacidade:1,audio_enabled:false,audio_volume:1},imagem:{arquivo:'',fit:'cover',align_x:.5,align_y:.5,bg:'#241b1a',crop:[],modo:'quadro',x:.73,y:.58,w:.41,h:.65,frame:true},cores:{fundo:'#241b1a',destaque:'#d99a62',texto:'#fff1da'},audio:{voice_text:'',voice_enabled:false,voice_file:'',voice_volume:1,voice_delay:.12,music_file:'',music_volume:.16,duck_music:false,tracks:[]}});
let previewRaf=0,lastPreviewDraw=-Infinity;
let previewRate=1,timingHistory=null,fitResult=null,workspaceBusy=false,librarySerial=0;
let clipPreviewFile='',clipPreviewScene=-1,clipEditing=false,clipGesture=null;
let project=null,projectName='',selected=0,tab='scene',dirty=false,saving=false,playing=false,playTime=0,lastFrame=0,previewBusy=false,previewPending=false,jobTimer=null,busy=false,assetPath=null,cacheInfo=null,selectedPane='previewPanel';
const api=async(path,options={})=>{const response=await fetch(path,options);const kind=response.headers.get('Content-Type')||'';let v=kind.includes('json')?await response.json():await response.text();if(!response.ok){const err=Error(v.error||'HTTP '+response.status);err.status=response.status;throw err;}return v;};
const post=(path,body)=>api(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
function toast(t,bad=false){const el=$('toast');el.textContent=t;el.style.borderColor=bad?'#e58b7d':'#c7996c';el.classList.add('show');setTimeout(()=>el.classList.remove('show'),3600);}
function sec(t){return Math.floor(t/60).toString().padStart(2,'0')+':'+Math.floor(t%60).toString().padStart(2,'0');}
let effectiveTiming=null;
function effectiveLengths(){return effectiveTiming?.owner===project&&effectiveTiming.signature===audioSignature(project)?effectiveTiming.lengths:null;}
function sceneSeconds(i,lengths=effectiveLengths()){const nominal=Number(project.cenas[i].duracao);return Math.max(nominal,lengths?.[i]||nominal);}
function totalDuration(){const lengths=effectiveLengths();return project.cenas.reduce((n,c,i)=>n+sceneSeconds(i,lengths),0);}
function startOf(i){const lengths=effectiveLengths();return project.cenas.slice(0,i).reduce((n,c,j)=>n+sceneSeconds(j,lengths),0);}
function sceneAt(t){const lengths=effectiveLengths();let sum=0;for(let i=0;i<project.cenas.length;i++){let d=sceneSeconds(i,lengths),nominal=Number(project.cenas[i].duracao);if(t<sum+d||i===project.cenas.length-1)return {i,progress:Math.max(0,Math.min(1,(t-sum)/Math.max(.5,nominal)))};sum+=d;}return {i:0,progress:0};}
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
 h+=field('Trilha global contínua (não reiniciar em cada cena)','trilha_continua','checkbox',null,
   'Quando ativada, a música atravessa os cortes entre cenas sem reiniciar. O mix final e o MP4 usam a mesma trilha.');
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
 if(sType('espacial')){
  h+='<div class="sectionTitle">Cena espacial · V3 experimental</div>';
  h+='<p class="fieldHint">Câmera 3D, objetos e keyframes. Prévia e exportação usam o mesmo motor determinístico de projeção SVG. Recursos avançados do SpatialSeed ainda não estão integrados.</p>';
  h+='<button id="editSpatial" class="primary">◈ Editar cena espacial</button>';
 }
 if(sType('svg')){
  h+=field('Fragmento SVG (sem <svg> externo)',`cenas.${selected}.svg`,'textarea');
  h+='<div class="inline"><button data-shape="circle">+ Círculo</button><button data-shape="rect">+ Retângulo</button><button data-shape="path">+ Curva</button><button data-shape="text">+ Texto</button></div>';
 }
 h+=renderAnimations();
 h+='<div class="sectionTitle">Imagem ou prancha de fotos</div>';
 h+=`<div class="inline"><button data-upload="cenas.${selected}.imagem.arquivo" class="primary">▧ Importar imagem</button><button id="imageComposerOpen" ${project.cenas[selected].imagem.arquivo?'':'disabled'}>✂ Recortar e posicionar</button></div>`;
 const fromScenes=[...new Set(project.cenas.map(c=>c.imagem?.arquivo).filter(Boolean))];
 if(fromScenes.length){h+='<div class="formField"><label>Reutilizar imagem já importada</label><select id="reuseImage"><option value="">Selecionar…</option>'+fromScenes.map(a=>`<option value="${esc(a)}" ${a===project.cenas[selected].imagem.arquivo?'selected':''}>${esc(a)}</option>`).join('')+'</select></div>';}
 h+=field('Nome do arquivo importado',`cenas.${selected}.imagem.arquivo`);
 h+=field('Exibição da imagem',`cenas.${selected}.imagem.modo`,'select', [['quadro','Quadro móvel'],['fundo','Plano de fundo']]);
 h+='<p class="fieldHint">Recorte uma área de uma prancha de fotografias e arraste-a sobre o quadro do vídeo. A mesma imagem pode ser reutilizada sem novo upload.</p>';
 h+='<div class="fieldGrid2">';
 h+=field('Ajuste',`cenas.${selected}.imagem.fit`,'select', [['cover','Preencher'],['contain','Mostrar inteira'],['stretch','Esticar']]);
 h+=field('Moldura',`cenas.${selected}.imagem.frame`,'checkbox');
 h+='</div>';
 h+='<div class="sectionTitle">Clipe de vídeo na cena</div>';
 h+='<div class="inline"><button id="importClip" type="button">▣ Importar vídeo</button><button id="recordCamera" type="button">● Gravar câmera</button><button id="editClipVisual" type="button" '+(project.cenas[selected].video_clipe.arquivo?'':'disabled')+'>▣ Posicionar visualmente</button><button id="removeClip" type="button" '+(project.cenas[selected].video_clipe.arquivo?'':'disabled')+'>✕ Remover vídeo da cena</button></div>';
 h+='<div class="inline"><button id="insertGIL" type="button">Inserir GIL nativa</button><button id="insertNativeDemo" type="button">▶ Demonstração GIL</button><button id="insertGILLegacy" type="button">GIL / SpatialSeed → MP4 (legado)</button><button id="openGIL" type="button">Abrir editor GIL</button>'+(project.cenas[selected].componente_gil?'<button id="sourceGIL" type="button">Baixar fonte GIL</button><button id="editGILWorkspace" type="button">Editar composição</button>':'')+'</div>';
 if(project.cenas[selected].componente_gil)h+='<p class="fieldHint">Componente '+esc(project.cenas[selected].componente_gil.origin)+' · '+Number(project.cenas[selected].componente_gil.duration).toFixed(2)+' s · derivado MP4</p>';
 if(project.cenas[selected].gil_nativo){h+='<p class="fieldHint">GIL nativa · '+Number(project.cenas[selected].gil_nativo.duration).toFixed(2)+' s · sem MP4 intermediário</p><div class="inline"><button id="editNativeGIL" type="button">Editar fonte nativa</button><button id="downloadNativeGIL" type="button">Baixar GIL</button><button id="removeNativeGIL" type="button">Remover camada GIL</button></div><div class="fieldGrid4">';
 for(const [key,title] of [['x','Centro X'],['y','Centro Y'],['w','Largura'],['h','Altura'],['opacidade','Opacidade']])h+=field(title+' (0 a 1)',`cenas.${selected}.gil_nativo.${key}`,'number');
 h+='</div>'+field('Fundo opaco',`cenas.${selected}.gil_nativo.opaque`,'checkbox');}
 h+=field('Arquivo do clipe',`cenas.${selected}.video_clipe.arquivo`);h+=field('Incluir som original',`cenas.${selected}.video_clipe.audio_enabled`,'checkbox');h+=field('Volume do clipe',`cenas.${selected}.video_clipe.audio_volume`,'number');
 h+='<p class="fieldHint">O som do clipe entra na mixagem. Salve alterações sonoras antes de reproduzir. Se a mídia já for a locução, não será duplicada.</p>';
 h+='<div class="fieldGrid4">';
 for(const [key,title] of [['x','Centro X'],['y','Centro Y'],['w','Largura'],['h','Altura']])h+=field(title+' (0 a 1)',`cenas.${selected}.video_clipe.${key}`,'number');
 h+='</div>';
 h+=field('Ajuste',`cenas.${selected}.video_clipe.fit`,'select',[['cover','Preencher quadro'],['contain','Mostrar inteiro']]);
 h+=field('Início no arquivo (s)',`cenas.${selected}.video_clipe.inicio`,'number');
 h+=field('Repetir até o fim da cena',`cenas.${selected}.video_clipe.repetir`,'checkbox');
 h+=field('Opacidade do vídeo (0 a 1)',`cenas.${selected}.video_clipe.opacidade`,'number');
 h+='<div class="separator"></div><div class="inline"><button id="duplicateScene">Duplicar cena</button><button id="removeScene">Excluir cena</button><button id="moveUp">↑ Subir</button><button id="moveDown">↓ Descer</button></div>';
 return h;
}
function animationTargets(scene){
 const options=[];
 if(scene.imagem?.arquivo)options.push(['__imagem__','Imagem da cena']);
 if(scene.tipo==='svg'&&scene.svg){
  for(const m of scene.svg.matchAll(/\bid=["']([A-Za-z_][A-Za-z0-9_.:-]{0,80})["']/g)){
   if(!options.some(v=>v[0]===m[1])&&!m[1].startsWith('camada'))options.push([m[1],m[1]]);
  }
 }
 options.push(['__titulo__','Título da cena'],['__subtitulo__','Subtítulo da cena'],['__conteudo__','Conteúdo gráfico da cena']);
 return options;
}
function renderAnimations(){
 const scene=project.cenas[selected],animations=scene.animacoes||(scene.animacoes=[]);
 const options=animationTargets(scene);
 let h='<div class="sectionTitle">Animações dos elementos</div>';
 h+='<p class="fieldHint">Selecione o ID de um objeto no SVG ou a fotografia da cena. Cada animação atua entre duas frações da duração da cena (0 a 1). A prévia e o MP4 usam os mesmos valores.</p>';
 h+='<div class="inline"><button id="addAnimation" '+(options.length?'':'disabled')+'>+ Animação</button><button id="sampleAnimation">Criar exemplo animado</button></div>';
 h+='<div class="formField"><label>Inspecionar animação no tempo <output id="animationProgress">0%</output></label><input type="range" id="animationSeek" min="0" max="100" step="1" value="0"></div>';
 if(!options.length)h+='<p class="smallNote">Para animar, importe uma imagem ou salve uma cena com objetos identificados pelo editor SVG.</p>';
 animations.forEach((a,i)=>{
  const prefix=`cenas.${selected}.animacoes.${i}`;
  const kinds=[['translacao','Translação'],['rotacao','Rotação'],['escala','Escala'],['fade','Fade / Opacidade']];
  const targetOptions=options.some(v=>v[0]===a.alvo)?options:[[a.alvo,a.alvo],...options];
  h+=`<div class="track animationCard"><div class="trackHead"><strong>Animação ${i+1}</strong><button data-remove-animation="${i}">Excluir</button></div>`;
  h+=field('Objeto',prefix+'.alvo','select',targetOptions);
  h+=field('Movimento',prefix+'.tipo','select',kinds);
  h+=`<div class="fieldGrid2">${field('Início (0–1)',prefix+'.inicio','number')}${field('Fim (0–1)',prefix+'.fim','number')}</div>`;
  h+=field('Interpolação',prefix+'.easing','select',[['suave','Suave'],['linear','Linear'],['power1.in','Acelerar'],['power1.out','Desacelerar'],['power1.inOut','Acelerar/desacelerar'],['power2.out','Desaceleração forte'],['power2.inOut','Cinematográfica'],['power3.inOut','Curva intensa'],['sine.inOut','Seno suave'],['expo.out','Exponencial'],['back.out','Recuo / impulso'],['bounce.out','Quicar']]);
  h+=`<div class="fieldGrid2">${field('Repetições (0–20)',prefix+'.repeticoes','number')}${field('Alternar direção (yoyo)',prefix+'.yoyo','checkbox')}</div>`;
  if(a.tipo==='translacao'){
   h+=`<div class="fieldGrid4">${field('X inicial (px)',prefix+'.de_x','number')}${field('Y inicial (px)',prefix+'.de_y','number')}${field('X final (px)',prefix+'.ate_x','number')}${field('Y final (px)',prefix+'.ate_y','number')}</div>`;
  }else{
   const unit={rotacao:'graus',escala:'fator',fade:'0 a 1'}[a.tipo];
   h+=`<div class="fieldGrid2">${field('De ('+unit+')',prefix+'.de','number')}${field('Até ('+unit+')',prefix+'.ate','number')}</div>`;
  }
  h+='</div>';
 });
 return h;
}
function addSceneAnimation(){
 const a=animationTargets(project.cenas[selected]);if(!a.length)return toast('Primeiro crie um objeto SVG ou importe uma imagem',true);
 project.cenas[selected].animacoes.push({alvo:a[0][0],tipo:'translacao',inicio:0,fim:1,easing:'suave',repeticoes:0,yoyo:false,de:0,ate:0,de_x:0,de_y:0,ate_x:150,ate_y:0});
 dirtyNow(true);
}
async function openImageComposer(){
 const s=project.cenas[selected],image=s.imagem;if(!image.arquivo)return toast('Importe uma imagem primeiro',true);
 try{await window.StudioImageComposer.open({
  url:'/api/media/image?file='+encodeURIComponent(image.arquivo),
  config:image,video:project.video,
  onChange:result=>{s.imagem={...s.imagem,...result};dirtyNow(true);toast('Imagem/recorte aplicado. Use Salvar para gravar o projeto.');}
 });}catch(e){toast(e.message,true);}
}
function requestImageFile(){assetPath=`cenas.${selected}.imagem.arquivo`;$('mediaFile').accept='image/*';$('mediaFile').click();}
function openOrCreateSVG(){
 if(project.cenas[selected].tipo!=='svg'){
  if(!confirm('Esta cena não é SVG. Criar uma nova cena vetorial sem alterar a atual?'))return;
  $('addSvgScene').click();
 }
 $('editSVG').click();
}
function sType(...choices){return choices.includes(project.cenas[selected].tipo);}
function sImgCrop(){return (project.cenas[selected].imagem.crop||[]).join(', ');}
function renderAudio(){let h='<div class="sectionTitle">Narração e áudio da cena '+(selected+1)+'</div><div class="inline"><button id="voiceThisShortcut">Gerar voz desta cena</button><button id="voiceAllShortcut">Gerar todas as vozes</button><button id="voiceTimingShortcut">Adequar duração à voz</button></div>';
 h+=field('Ativar narração',`cenas.${selected}.audio.voice_enabled`,'checkbox');
 h+=field('Texto para voz neural',`cenas.${selected}.audio.voice_text`,'textarea','', 'Síntese gerada apenas quando você tocar em Áudio em lote.');
 h+=field('Voz gravada (substitui o texto neural)',`cenas.${selected}.audio.voice_file`);
 h+=action(`cenas.${selected}.audio.voice_file`,'Importar locução pronta');
 h+='<button id="recordVoice">● Gravar narração pelo microfone</button><button id="exportVoiceMp3" type="button">↓ Baixar narração MP3</button>';
 h+='<div class="inline"><button id="removeVoiceFile" type="button">✕ Remover locução gravada</button><button id="removeSceneMusic" type="button">✕ Remover música da cena</button><button id="removeSceneAudio" type="button">✕ Remover arquivos de áudio (manter texto)</button><button id="enableSceneAudio" type="button">Reativar som</button></div>';
 h+=field('Cena completamente silenciosa, inclusive música global',`cenas.${selected}.audio.muted`,'checkbox');
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
 try{const name=projectName,snapshot=JSON.stringify(project);const saved=JSON.parse(snapshot);await post('/api/project',{name,project:saved});const signature=audioSignature(saved),audioChanged=signature!==savedAudioSignature;savedAudioSignature=signature;dirty=name!==projectName||JSON.stringify(project)!==snapshot;if(audioChanged||name!==projectName){stopWorkspace();stopTransport(true);effectiveTiming=null;await refreshEffectiveTiming();}$('saveInfo').textContent=dirty?'● Alterações posteriores ao salvamento':'✓ Salvo no aparelho';}finally{saving=false;}}
function drawSceneList(){const l=$('sceneList');l.innerHTML=project.cenas.map((s,i)=>`<div class="sceneItem ${i===selected?'active':''}"><button class="scenePick" data-scene="${i}"><small>${String(i+1).padStart(2,'0')} · ${esc(names[s.tipo]||s.tipo)} · ${s.duracao}s</small><b>${esc(s.titulo||'Sem título')}</b><small>${s.audio.voice_enabled?'♫ voz':'sem voz'}</small></button><div class="sceneOrder"><button data-shift="-1" data-index="${i}">↑</button><button data-shift="1" data-index="${i}">↓</button></div></div>`).join('');$('sceneCount').textContent=project.cenas.length;}
function drawTimeline(){const scale=Number($('timelineZoom')?.value)||12;const l=$('timeline');l.innerHTML=project.cenas.map((s,i)=>`<div class="sceneStrip ${selected===i?'active':''}" style="width:${Math.max(42,sceneSeconds(i)*scale)}px"><button data-scene="${i}" title="${esc(s.titulo)}"><small>${i+1} · ${startOf(i).toFixed(1)}s</small><b>${esc(s.titulo)}</b><small>${sceneSeconds(i).toFixed(2)}s${sceneSeconds(i)>Number(s.duracao)+.001?' (ajust.)':''} ${s.audio.voice_enabled?'♫':''}</small></button><button class="trimHandle" data-trim="${i}" aria-label="Arrastar para ajustar duração da cena ${i+1}" title="Arraste para ajustar duração"></button></div>`).join('');}
function bindTimeline(){const l=$('timeline');$('timelineZoom').oninput=drawTimeline;l.addEventListener('pointerdown',e=>{const grip=e.target.closest('[data-trim]');if(!grip||e.button!==0||!project||saving||busy)return;e.preventDefault();e.stopPropagation();stopWorkspace();const target=project.cenas[Number(grip.dataset.trim)],orig=Number(target.duracao),owner=project,scale=Number($('timelineZoom').value)||12,x=e.clientX,strip=grip.parentElement;let val=orig;grip.setPointerCapture(e.pointerId);grip.onpointermove=ev=>{val=Math.max(.5,Math.min(600,Math.round((orig+(ev.clientX-x)/scale)*20)/20));strip.style.width=Math.max(42,val*scale)+'px';strip.querySelector('button small:last-child').textContent=val.toFixed(2)+'s';};const finish=ev=>{grip.onpointermove=grip.onpointerup=grip.onpointercancel=null;if(ev.type!=='pointercancel'&&owner===project&&project.cenas.includes(target)&&Math.abs(val-orig)>.001){target.duracao=val;selected=project.cenas.indexOf(target);playTime=startOf(selected);dirtyNow(true);}else drawTimeline();};grip.onpointerup=finish;grip.onpointercancel=finish;});}
function drawEverything(){if(!project)return;drawSceneList();drawTimeline();drawEditor();objectEditor?.refresh();if(!$('workspaceLibrary').hidden)libraryTargets();$('stage').style.aspectRatio=project.video.width+'/'+project.video.height;const ratio=project.video.width/project.video.height;$('previewFullHost').style.setProperty('--preview-aspect',ratio);const shell=$('stageShell');shell.style.width=project.video.height>project.video.width?Math.max(160,Math.round(Math.min(window.innerWidth*.92,window.innerHeight*.70*ratio)))+'px':'';document.body.classList.toggle('portraitProject',project.video.height>project.video.width);$('formatInfo').textContent=`${project.video.width} × ${project.video.height} · ${project.video.fps} FPS`;showPreview();}
function jump(i){clipEditingEnabled(false);clearMediaPlayers();selected=Math.max(0,Math.min(project.cenas.length-1,i));playTime=startOf(selected);drawEverything();}
function tick(ts){previewRaf=0;if(!playing)return;const next=Math.min(totalDuration(),playTime+(lastFrame?Math.max(0,ts-lastFrame)/1000*previewRate:0));lastFrame=ts;playTime=transportTime(next);
 if(playTime>=totalDuration()){playing=false;$('playButton').textContent='▶';}
 const ix=sceneAt(playTime).i;if(ix!==selected){clearMediaPlayers();selected=ix;drawSceneList();drawTimeline();drawEditor();objectEditor?.refresh();}
 showPreview();if(playing)previewRaf=requestAnimationFrame(tick);else{stopTransport();$('stageClip').pause();objectRuntime?.pauseObjects($('stageShell'));objectEditor?.paint();}
}
function clampClip(v,lo,hi){return Math.max(lo,Math.min(hi,v));}
function clipEditingEnabled(enabled){
 clipEditing=!!enabled&&!!project?.cenas[selected]?.video_clipe?.arquivo;
 const button=$('toggleClipEdit');button.hidden=!project?.cenas[selected]?.video_clipe?.arquivo;
 button.textContent=clipEditing?'✓ Concluir posicionamento':'▣ Posicionar vídeo';
 $('stageShell').classList.toggle('clip-editing',clipEditing);
 updateClipBox();
}
function updateClipBox(){
 const box=$('clipBox'),scene=project?.cenas[selected],clip=scene?.video_clipe;
 if(!clip||!clip.arquivo){box.style.display='none';return;}
 box.style.display=clipEditing?'block':'none';
 Object.assign(box.style,{left:100*(clip.x-clip.w/2)+'%',top:100*(clip.y-clip.h/2)+'%',width:clip.w*100+'%',height:clip.h*100+'%'});
 const host=$('stageClip');
 Object.assign(host.style,{left:100*(clip.x-clip.w/2)+'%',top:100*(clip.y-clip.h/2)+'%',width:clip.w*100+'%',height:clip.h*100+'%'});
}
function initClipGesture(){
 const box=$('clipBox');
 box.addEventListener('pointerdown',e=>{
  if(!clipEditing||!project?.cenas[selected]?.video_clipe?.arquivo)return;
  if(clipGesture)return;
  const clip=project.cenas[selected].video_clipe;
  clipGesture={id:e.pointerId,index:selected,mode:e.target.closest('.clipResize')?'resize':'move',
      clientX:e.clientX,clientY:e.clientY,original:{x:clip.x,y:clip.y,w:clip.w,h:clip.h}};
  box.setPointerCapture(e.pointerId);e.preventDefault();e.stopPropagation();
 });
 box.addEventListener('pointermove',e=>{
  if(!clipGesture||clipGesture.id!==e.pointerId||clipGesture.index!==selected)return;
  const clip=project.cenas[selected].video_clipe;
  const bounds=$('stageShell').getBoundingClientRect();
  const dx=(e.clientX-clipGesture.clientX)/Math.max(1,bounds.width);
  const dy=(e.clientY-clipGesture.clientY)/Math.max(1,bounds.height);
  const c=clipGesture.original;
  if(clipGesture.mode==='move'){
    clip.x=clampClip(c.x+dx,0,1);clip.y=clampClip(c.y+dy,0,1);
  }else{
    const w=clampClip(c.w+dx,.08,1),h=clampClip(c.h+dy,.08,1);
    clip.w=w;clip.h=h;
    clip.x=clampClip(c.x-c.w/2+w/2,0,1);
    clip.y=clampClip(c.y-c.h/2+h/2,0,1);
  }
  updateClipBox();e.preventDefault();
 });
 const finish=e=>{
  if(!clipGesture||clipGesture.id!==e.pointerId)return;
  clipGesture=null;dirtyNow(true);
 };
 box.addEventListener('pointerup',finish);box.addEventListener('pointercancel',finish);
}
function syncPreviewVideo(sceneIndex,position){
 const host=$('stageClip'),clip=project.cenas[sceneIndex]?.video_clipe||{};
 if(!clip.arquivo){host.hidden=true;host.pause();clipPreviewFile='';clipEditingEnabled(false);return;}
 const key=clip.arquivo;
 if(key!==clipPreviewFile||sceneIndex!==clipPreviewScene){
   clipPreviewFile=key;clipPreviewScene=sceneIndex;
   host.src='/api/media/clip?file='+encodeURIComponent(key);host.load();
 }
 const left=100*(clip.x-clip.w/2),top=100*(clip.y-clip.h/2);
 Object.assign(host.style,{left:left+'%',top:top+'%',width:clip.w*100+'%',height:clip.h*100+'%',objectFit:clip.fit,opacity:String(clip.opacidade)});
 host.hidden=false;host.loop=!!clip.repetir;host.muted=true;host.playbackRate=previewRate;
 $('toggleClipEdit').hidden=false;updateClipBox();
 const t=Number(clip.inicio||0)+Math.min(position,1-1e-8)*Number(project.cenas[sceneIndex].duracao);
 if(host.readyState>=1&&Number.isFinite(t)){
   const duration=host.duration;
   if(!clip.repetir&&Number.isFinite(duration)&&duration>0&&t>=duration){host.hidden=true;host.pause();return;}
   const target=clip.repetir&&Number.isFinite(duration)&&duration>0?t%duration:t;
   if(!host.seeking&&Math.abs(host.currentTime-target)>(playing?.65:.08))try{host.currentTime=target;}catch(e){}
 }
 if(playing&&position<1){if(host.paused)host.play().catch(()=>{});}else if(!host.paused)host.pause();
}
let nativeModule=null,nativePending=null,nativeFailed=false,nativeCurrent=null;
let objectRuntime=null,objectEditor=null;
function syncSceneObjects(scene,progress){
 if(!project)return;const layers=scene?.objetos_midia||[];
 if(objectRuntime)objectRuntime.syncObjects($('stageShell'),layers,Number(scene?.duracao||0)*Math.min(progress,1-1e-8),project.video,playing&&progress<1,previewRate,m=>gilStatus(m,true));
 objectEditor?.paint();
}
async function initObjects(){
 try{objectRuntime=await import('/scene-objects.mjs');const editor=await import('/scene-object-editor.mjs');objectEditor=editor.installEditor({scene:()=>project?.cenas[selected],local:()=>project?Math.max(0,playTime-startOf(selected)):0,playing:()=>playing,stop:stopWorkspace,seek:t=>{stopWorkspace();playTime=startOf(selected)+Math.min(Number(project.cenas[selected].duracao)-.0001,Math.max(0,t));showPreview();},changed:()=>dirtyNow(true),activate:()=>{clipEditingEnabled(false);switchPane('previewPanel');},preview:showPreview,notify:toast,audio:()=>{tab='audio';document.querySelectorAll('[data-edit]').forEach(b=>b.classList.toggle('on',b.dataset.edit==='audio'));drawEditor();switchPane('editPanel');},legacyClip:()=>{tab='scene';document.querySelectorAll('[data-edit]').forEach(b=>b.classList.toggle('on',b.dataset.edit==='scene'));drawEditor();switchPane('editPanel');$('editClipVisual')?.scrollIntoView({block:'center'});},dimensions:()=>project.video,example:id=>api('/api/workspace/gil-example?id='+encodeURIComponent(id)),upload:async(file,kind)=>{if(kind==='video')return (await uploadChunked(file,'video')).filename;const data=await new Promise((resolve,reject)=>{const fr=new FileReader();fr.onload=()=>resolve(fr.result);fr.onerror=reject;fr.readAsDataURL(file);});return (await post('/api/upload',{kind:'image',data,filename:file.name})).filename;}});objectEditor.refresh();showPreview();}
 catch(e){$('addSceneObject').disabled=true;gilStatus('Editor de objetos indisponível: '+e.message,true);}
}

function nativeRuntime(){return nativeModule?Promise.resolve(nativeModule):(nativePending??=import('/gil-native.mjs').then(m=>{nativeModule=m;return m;}).catch(err=>{nativePending=null;throw err;}));}
function syncNative(scene,position){
 const shell=$('stageShell'), layer=scene?.gil_nativo||null, time=Number(scene?.duracao||0)*position;
 nativeCurrent={layer,time,dimensions:project?.video};
 if(nativeModule){nativeModule.updateLayer(shell,layer,time,project.video);return;}
 if(!layer||nativeFailed||nativePending)return;
 nativeRuntime().then(m=>{const n=nativeCurrent;if(n)m.updateLayer(shell,n.layer,n.time,n.dimensions);}).catch(e=>{if(!nativeFailed)gilStatus('GIL nativa indisponível: '+e.message,true);nativeFailed=true;});
}
async function showPreview(){if(!project)return;
 const nativeScene=sceneAt(playTime);syncNative(project.cenas[nativeScene.i],nativeScene.progress);syncSceneObjects(project.cenas[nativeScene.i],nativeScene.progress);
 $('timeInfo').textContent=sec(playTime)+' / '+sec(totalDuration());$('seek').value=totalDuration()?Math.round(playTime/totalDuration()*1000):0;
 const now=performance.now();if(playing&&now-lastPreviewDraw<100)return;if(previewBusy){previewPending=true;return;}lastPreviewDraw=now;previewBusy=true;const s=sceneAt(playTime),owner=project;
 try{const svg=await post('/api/preview',{scene:project.cenas[s.i],video:project.video,progress:s.progress,index:s.i,total:project.cenas.length});if(project===owner&&sceneAt(playTime).i===s.i){$('stage').innerHTML=svg;syncPreviewVideo(s.i,sceneAt(playTime).progress);syncSceneObjects(project.cenas[s.i],sceneAt(playTime).progress);}}
 catch(e){$('stage').textContent='Falha na prévia: '+e.message;}
 finally{previewBusy=false;if(previewPending){previewPending=false;if(!playing)setTimeout(showPreview,80);}}
}
async function listProjects(){const r=await api('/api/projects');$('projectSelect').innerHTML=r.projects.map(x=>`<option value="${esc(x)}">${esc(x)}</option>`).join('');return r.projects;}
async function load(name){if(dirty)await save();fitResult=null;timingHistory=null;clipEditingEnabled(false);clearMediaPlayers();clipPreviewFile='';clipPreviewScene=-1;let r=await api('/api/project?name='+encodeURIComponent(name));project=r.project;effectiveTiming=null;savedAudioSignature=audioSignature(project);projectName=name;selected=0;playTime=0;playing=false;dirty=false;$('projectSelect').value=name;$('saveInfo').textContent='✓ Carregado';await refreshEffectiveTiming();drawEverything();refreshCache();}
function acceptEffectiveTiming(owner,name,signature,scenes){
 if(project!==owner||name!==projectName||signature!==audioSignature(project)||playing||!audioSnapshotMatches()||scenes.length!==project.cenas.length||!scenes.every((c,i)=>c.id===project.cenas[i].id&&Number.isFinite(c.seconds)))return false;
 const i=sceneAt(playTime).i,local=playTime-startOf(i);effectiveTiming={owner,signature,lengths:scenes.map(c=>c.seconds)};playTime=Math.min(totalDuration(),startOf(i)+Math.min(local,sceneSeconds(i)));return true;
}
async function refreshEffectiveTiming(){if(!project||!audioSnapshotMatches())return;const owner=project,name=projectName,signature=audioSignature(project);try{const r=await api('/api/preview/timing?name='+encodeURIComponent(name));if(acceptEffectiveTiming(owner,name,signature,r.scenes)){drawTimeline();showPreview();}}catch(e){$('transportStatus').textContent='Duração efetiva indisponível: '+e.message;}}
async function refreshCache(){if(!project)return;const owner=project,name=projectName,signature=audioSignature(project);try{let r=await api('/api/cache/status?name='+encodeURIComponent(name));if(project!==owner||name!==projectName||signature!==audioSignature(project))return;cacheInfo=r.scenes;if(acceptEffectiveTiming(owner,name,signature,r.scenes)){drawTimeline();showPreview();}$('cacheTable').innerHTML=r.scenes.map(c=>`<div class="cacheItem"><b>${c.index}. ${esc(c.title)}</b><small><span class="${c.visual?'check':'missing'}">Visual ${c.visual?'✓':'·'}</span> · <span class="${c.audio?'check':'missing'}">Áudio ${c.audio?'✓':'·'}</span> · <span class="${c.voice?'check':'missing'}">Voz ${c.voice?'✓':'·'}</span></small><br><small>${c.seconds.toFixed(2)} s</small><br><button data-clear="${c.index}">Limpar cache desta cena</button></div>`).join('');}catch(e){$('cacheTable').textContent='Cache: '+e.message;}}
async function begin(mode,no_voice=false){if(busy)return toast('Já existe um trabalho em execução',true);try{await save();let j=await post('/api/job',{name:projectName,mode,scene:['cena','voz-mp3','audio-cena'].includes(mode)?selected+1:undefined,no_voice});busy=true;$('downloads').innerHTML='';$('logBox').textContent='';trackJob(j.job);}catch(e){toast(e.message,true);}}
function trackJob(id){if(jobTimer)clearInterval(jobTimer);busy=true;$('statusBadge').textContent='Executando';
 const poll=async()=>{try{const j=await api('/api/job/'+id);$('progress').value=Math.round(j.progress*100);$('progressText').textContent=Math.round(j.progress*100)+'%';$('phase').textContent=j.phase;$('logBox').textContent=j.logs.join('\n');$('logBox').scrollTop=$('logBox').scrollHeight;
 if(['done','error'].includes(j.status)){
    clearInterval(jobTimer);jobTimer=null;busy=false;$('statusBadge').textContent=j.status==='done'?'Concluído':'Erro';
    if(j.status==='error'){toast(j.error,true);return;}
    let files=[];if(j.result.html)files.push(['HTML autônomo',j.result.html]);if(j.result.video)files.push(['MP4',j.result.video]);if(j.result.frames)files.push(['Quadros ZIP',j.result.frames]);if(j.result.batch)files.push(['Áudio ZIP',j.result.batch]);if(j.result.audio)files.push([j.result.audio.endsWith('.mp3')?'Áudio MP3':j.result.audio.endsWith('.opus')?'Áudio Opus':'Mix WAV',j.result.audio]);
    $('downloads').innerHTML=files.map(([t,f])=>`<a download href="/api/output/${encodeURIComponent(f)}">↓ ${esc(t)} — ${esc(f)}</a>`).join('');toast(j.result.cached?'Resultado reutilizado do cache':'Produção concluída');refreshCache();
 }
 }catch(e){
   if(e.status===404){
     if(jobTimer)clearInterval(jobTimer);
     jobTimer=null;busy=false;
     $('statusBadge').textContent='Tarefa expirada';
     $('phase').textContent='A tarefa não existe mais no servidor. Inicie uma nova renderização.';
     $('progress').value=0;$('progressText').textContent='0%';
     return;
   }
   $('phase').textContent='Erro de conexão: '+e.message;
 }};
 jobTimer=setInterval(poll,1200);poll();switchPane('workPanel');}

// The cached scene mix is the clock while it is audible. Seek only at an
// explicit navigation/resume or source change, never on each visual frame.
let savedAudioSignature='';
function audioSignature(p){if(!p)return '';const keys=['voz','velocidade_voz','motor_voz','modelo_piper','voz_espeak','velocidade_espeak','encaixe_voz','trilha','trilha_continua','volume_musica','volume_voz'];return JSON.stringify([keys.map(k=>p[k]),p.video?.draw_fps,p.cenas.map(c=>[c.id,c.duracao,c.audio, c.video_clipe?.arquivo&&c.video_clipe.audio_enabled?[c.video_clipe.arquivo,c.video_clipe.audio_volume,c.video_clipe.inicio,c.video_clipe.repetir]:null,(c.objetos_midia||[]).filter(o=>o.kind==='video'&&o.audio_enabled!==false).map(o=>[o.file,o.start,o.end,o.offset,o.loop,o.audio_volume??1])])]);}
function audioSnapshotMatches(){return !!savedAudioSignature&&savedAudioSignature===audioSignature(project);}
let transportKey='',transportFallback=false,transportEpoch=0,transportOffset=0,transportPending=false,transportBlocked=false,transportSeek=true,transportDeadline=0;
function stopTransport(reset=false){const a=$('transportAudio');if(!a)return;a.pause();transportSeek=true;if(reset){transportEpoch++;transportKey='';transportPending=false;transportBlocked=false;a.onerror=null;a.removeAttribute('src');a.load();}}
function transportTime(next){
 const a=$('transportAudio');if(!project||!playing||!$('previewSound').checked||(dirty&&!audioSnapshotMatches())){if(!a.paused)stopTransport();return next;}
 const {i}=sceneAt(playTime),c=project.cenas[i],key=projectName+'|'+i,begin=startOf(i),end=begin+sceneSeconds(i),now=performance.now();
 if(c.audio?.muted){if(!a.paused)stopTransport();return next;}
 function source(kind){transportOffset=kind==='voice'?Number(c.audio.voice_delay||0):0;transportSeek=true;transportPending=false;transportDeadline=performance.now()+(kind==='audio'?60000:5000);a.src='/api/scene/media?name='+encodeURIComponent(projectName)+'&scene='+(i+1)+'&kind='+kind+(kind==='audio'?'&prepare=1':'');a.load();}
 if(key!==transportKey){transportKey=key;transportFallback=false;transportBlocked=false;const epoch=++transportEpoch;a.onerror=()=>{if(epoch!==transportEpoch||key!==transportKey)return;if(!transportFallback&&c.audio.voice_enabled){transportFallback=true;source('voice');$('transportStatus').textContent='Sem mix em cache; tentando a voz.';}else{transportBlocked=true;$('transportStatus').textContent='Áudio da cena indisponível; gere a voz ou o mix.';}};$('transportStatus').textContent='Preparando áudio da cena (voz, clipes e faixas)…';source('audio');}
 const local=playTime-begin-transportOffset;
 if(transportBlocked||a.error)return next;
 if(local<0){transportDeadline=now+5000;return Math.min(next,begin+transportOffset);}
 if(now>transportDeadline&&(transportSeek||(!a.ended&&(a.paused||a.seeking||a.readyState<2)))){transportBlocked=true;a.pause();$('transportStatus').textContent='Áudio não carregou; prévia visual continua.';return next;}
 if(a.readyState<1)return playTime;
 if(Number.isFinite(a.duration)&&local>=a.duration-.025){a.pause();return next;}
 a.playbackRate=previewRate;a.volume=transportFallback?Math.min(1,Math.max(0,Number(project.volume_voz??1)*Number(c.audio.voice_volume??1))):1;
 if(transportSeek){transportSeek=false;if(Math.abs(a.currentTime-local)>.06){try{a.currentTime=Math.max(0,local);}catch{transportBlocked=true;return next;}}}
 if(a.ended&&!a.seeking)return next;
 if(a.paused&&!transportPending){transportPending=true;const epoch=transportEpoch;a.play().catch(err=>{if(epoch!==transportEpoch||err.name==='AbortError')return;transportBlocked=true;$('transportStatus').textContent='Reprodução de áudio bloqueada; pause e reproduza novamente.';}).finally(()=>{if(epoch===transportEpoch)transportPending=false;});}
 if(a.seeking||a.paused||a.readyState<2)return playTime;
 transportDeadline=now+5000;if(!transportFallback)$('transportStatus').textContent='Mix da cena sincronizado';
 const audioTime=begin+transportOffset+a.currentTime;
 // Avoid stalling at the end of a short voice-only file or a rounding error.
 if(audioTime>=end-.015)return Math.min(totalDuration(),end);
 return Math.max(playTime,Math.min(end,audioTime));
}
function syncTransport(){transportTime(playTime);}
function clearMediaPlayers(){
 stopTransport(true);const a=$('voicePlayer'),v=$('scenePlayer');
 try{a.pause();a.removeAttribute('src');a.load();v.pause();v.removeAttribute('src');v.load();v.hidden=true;}catch(e){}
 $('mediaStatus').textContent='Cena '+(selected+1)+': escolha o áudio ou vídeo para ouvir.';
}
async function openPlayback(path){if(!project||saving)return;const name=projectName,original=JSON.stringify(project);stopWorkspace();const popup=window.open('about:blank','_blank');if(popup)popup.opener=null;try{await save(true);if(name!==projectName||JSON.stringify(project)!==original||dirty)throw Error('Projeto mudou; salve e tente novamente.');const url=path+encodeURIComponent(name);if(popup)popup.location.replace(new URL(url,location.href).href);else if(confirm('A abertura em outra aba foi bloqueada. Abrir nesta janela?'))location.href=url;}catch(e){if(popup)popup.close();toast(e.message,true);}}
async function playSceneAudio(kind){
 stopWorkspace();try{
  await save(); const a=$('voicePlayer');$('scenePlayer').pause();$('scenePlayer').hidden=true;
  a.pause();a.src='/api/scene/media?name='+encodeURIComponent(projectName)+'&scene='+(selected+1)+'&kind='+kind+(kind==='audio'?'&prepare=1':'')+'&ts='+Date.now();
  $('mediaStatus').textContent=kind==='voice'?'Locução gerada (sem música)':'Mixagem final da cena';
  await a.play();
 }catch(e){toast('Áudio indisponível: gere Áudio em lote ou Renderizar cena. '+e.message,true);}
}
async function watchSceneVideo(){
 stopWorkspace();try{
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
function jsonDocument(){return $('jsonMode').value==='scene'?project.cenas[selected]:project;}
function fillJsonText(){
 if(!project)return;
 $('jsonText').value=JSON.stringify(jsonDocument(),null,2);
 $('jsonMessage').textContent='Texto carregado do projeto em memória. Nenhuma alteração aplicada.';
}
function openJson(){
 if(!project)return;
 $('jsonMode').value='scene';fillJsonText();$('jsonDialog').showModal();
}
function jsonCandidate(){
 const edited=JSON.parse($('jsonText').value);
 if(!edited||typeof edited!=='object'||Array.isArray(edited))throw Error('O JSON deve representar um objeto.');
 if($('jsonMode').value==='project')return edited;
 const scenes=project.cenas.slice();scenes[selected]=edited;
 return {...project,cenas:scenes};
}
async function checkJson(apply=false){
 const msg=$('jsonMessage');msg.textContent='Validando…';
 try{
  const candidate=jsonCandidate();
  const result=await post('/api/project/validate',{project:candidate});
  if(!result.ok||!result.project)throw Error('O servidor não retornou um projeto válido');
  if(apply){
   project=result.project;
   selected=Math.min(selected,project.cenas.length-1);
   playTime=startOf(selected);
   dirtyNow(true);
   msg.textContent='Aplicado ao projeto em memória. Use Salvar para persistir.';
   $('jsonDialog').close();toast('JSON aplicado. Salve para persistir.');
  }else{
   msg.textContent='JSON válido para o esquema do Estúdio. Nenhum arquivo modificado. A normalização pode descartar campos desconhecidos.';
  }
 }catch(e){msg.textContent='ERRO: '+e.message;}
}

async function uploadChunked(file,kind,desiredName=''){
 if(!file||file.size<1||file.size>250_000_000)throw Error('Arquivo vazio ou maior que 250 MB');
 const size=960_000,start=await post('/api/upload/chunks',{op:'start',filename:file.name,size:file.size,kind});
 let index=0;
 try{
  for(let offset=0;offset<file.size;offset+=size){
   const data=await new Promise((resolve,reject)=>{let reader=new FileReader();reader.onload=()=>resolve(String(reader.result).split(',')[1]);reader.onerror=reject;reader.readAsDataURL(file.slice(offset,offset+size));});
   await post('/api/upload/chunks',{op:'append',upload_id:start.upload_id,index:index++,data});
  }
  return await post('/api/upload/chunks',{op:'finish',upload_id:start.upload_id,name:desiredName});
 }catch(error){post('/api/upload/chunks',{op:'abort',upload_id:start.upload_id}).catch(()=>{});throw error;}
}
function attachVoice(index,filename){let scene=project.cenas[index];if(!scene)throw Error('Cena de origem removida');scene.audio.voice_file=filename;scene.audio.voice_enabled=true;scene.audio.muted=false;dirtyNow(true);toast('Gravação vinculada. Texto da narração preservado; use Salvar.');}
function attachVideo(index,filename){let scene=project.cenas[index];if(!scene)throw Error('Cena de origem removida');scene.video_clipe.arquivo=filename;scene.video_clipe.audio_enabled=true;scene.video_clipe.audio_volume=1;delete scene.componente_gil;dirtyNow(true);toast('Clipe importado. Use Posicionar vídeo na prévia.');if(index===selected)clipEditingEnabled(true);}
async function captureMedia(kind){const index=selected;
 if(!window.StudioRecorder)return toast('Módulo de gravação não disponível',true);
 window.StudioRecorder.open(kind,async(file,useCameraAudio)=>{
   const r=await uploadChunked(file,kind);
   if(kind==='audio')attachVoice(index,r.filename);
   else{attachVideo(index,r.filename);if(useCameraAudio){attachVoice(index,r.filename);project.cenas[index].video_clipe.audio_enabled=false;dirtyNow(true);}else{project.cenas[index].video_clipe.audio_enabled=false;dirtyNow(true);}}
 },{script:String(project.cenas[index]?.audio?.voice_text||project.cenas[index]?.fala||''),title:project.cenas[index]?.titulo||''});
}
const WORKSPACE='http://127.0.0.1:8877';
function inWorkspace(){return window.parent!==window&&location.origin==='http://127.0.0.1:8784';}
window.addEventListener('message',e=>{if(!inWorkspace()||e.source!==parent||e.origin!==WORKSPACE||e.data?.protocol!=='rd-workspace-1')return;if(e.data.type==='deactivate'){stopWorkspace();clearMediaPlayers();return;}if(e.data.type==='gil-source'&&typeof e.data.source==='string'&&e.data.source.length<=250000){if(!project){toast('Selecione um projeto e uma cena primeiro.',true);return;}if(objectEditor)objectEditor.openSource(e.data.source,'workspace.gil');else if(confirm('Inserir composição GIL na cena '+(selected+1)+' — '+project.cenas[selected].titulo+'?'))importGIL(new File([e.data.source],'workspace.gil',{type:'text/plain'}));}});
let gilRendering=false;
let forceGilLegacy=false;
function gilStatus(text,bad=false){const e=$('gilNativeStatus');e.hidden=false;e.textContent=text;e.style.color=bad?'#ee8d84':'';toast(text,bad);}
async function demoNativeGIL(){
 if(!project||gilRendering)return;
 const owner=project,target=project.cenas[selected];
 try{const r=await api('/api/workspace/gil-example?id=native-demo');if(owner!==project||project.cenas[selected]!==target)throw Error('A cena mudou durante a leitura');await importNativeGIL(new File([r.source],r.name,{type:'text/plain'}));}
 catch(e){gilStatus('Demonstração GIL: '+e.message,true);}
}
async function importNativeGIL(file){
 if(!file||gilRendering||!project)return;
 const owner=project,target=project.cenas[selected],old=target.gil_nativo;
 if(old&&!confirm('Substituir somente a camada GIL nativa desta cena?'))return;
 gilRendering=true;
 try{
  if(file.size>250000)throw Error('Fonte acima de 250 kB');
  if(file.size===0)throw Error('Arquivo vazio. Use Demonstração GIL para testar.');
  const source=(await file.text()).replace(/^\uFEFF/,'');
  if(!source.trim())throw Error('Fonte vazia. Use Demonstração GIL para testar.');
  if(/^\s*gil3\b/i.test(source)||/\.gil3$/i.test(file.name))throw Error('GIL3 3.0 é uma gramática gráfica anterior, ainda sem adaptador temporal. O original foi preservado.');
  const runtime=await nativeRuntime(),info=runtime.prepare(source);
  if(info.cues&&!confirm('Esta versão não reproduz os efeitos GIL. Importar somente a parte visual, preservando a fonte?'))return;
  if(info.duration<.5||info.duration>60)throw Error('Duração suportada: 0,5–60 s');
  const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(source)))).map(v=>v.toString(16).padStart(2,'0')).join('');
  if(project!==owner||!owner.cenas.includes(target)||target.gil_nativo!==old)throw Error('A cena foi alterada durante a importação');
  const layer={format:'gil-timeline-0.1',origin:'gil',origin_sha256:hash,source,source_sha256:hash,duration:info.duration,x:old?.x??.5,y:old?.y??.5,w:old?.w??1,h:old?.h??1,opacidade:old?.opacidade??1,opaque:old?.opaque??false};
  if(Math.abs(target.duracao-info.duration)>.05&&confirm('Ajustar a duração da cena para '+info.duration.toFixed(2)+' s?'))target.duracao=info.duration;
  target.gil_nativo=layer;nativeFailed=false;stopWorkspace();showDrawer(null);selected=owner.cenas.indexOf(target);playTime=startOf(selected);switchPane('previewPanel');dirtyNow(true);gilStatus('GIL nativa inserida · '+info.duration.toFixed(1)+' s. Pressione ▶ ou mova o cursor da timeline. Salve para persistir.');
 }catch(e){gilStatus('GIL nativa: '+e.message,true);}finally{gilRendering=false;}
}
async function importGIL(file,legacy=false){
 if(!file||gilRendering||!project)return;
 if(/\.gil3$/i.test(file.name))return gilStatus('GIL3 3.0: formato anterior ainda sem adaptador temporal. Nenhuma alteração feita.',true);
 if(!legacy&&!/\.(spatialseed|json)$/i.test(file.name))return importNativeGIL(file);
 const targetProject=project,target=project.cenas[selected],oldClip=target.video_clipe.arquivo;
 if(file.size>250000)return toast('Fonte acima de 250 kB',true);
 if(oldClip&&!confirm('Substituir o clipe visual desta cena? A narração e as faixas de áudio atuais permanecem.'))return;
 const value=prompt('Duração do trecho em segundos (vazio = composição inteira; máximo 60 s)',String(Math.min(60,target.duracao)));if(value===null)return;
 const duration=value.trim()===''?null:Number(value);if(duration!==null&&(!Number.isFinite(duration)||duration<.5||duration>60))return toast('Duração inválida',true);
 const effects=confirm('Incluir efeitos sonoros da GIL como faixa de áudio separada? A narração será preservada.');
 if(effects&&target.audio.tracks.length>=20)return toast('Limite de 20 faixas sonoras',true);
 const format=/\.(spatialseed|json)$/i.test(file.name)?'spatialseed':'gil';
 if(format==='spatialseed'&&!confirm('Conversão experimental de caixas e grupos. Câmera/luz novas; animações e materiais nativos não serão reproduzidos integralmente. Continuar?'))return;
 gilRendering=true;toast('Renderizando composição localmente…');$('saveInfo').textContent='Renderizando componente GIL…';
 try{const r=await post('/api/component/gil',{source:await file.text(),format,duration,fps:24,long_side:960,effects});
   if(project!==targetProject||!project.cenas.includes(target)||target.video_clipe.arquivo!==oldClip){toast('A cena mudou durante o render. Mídia preservada: '+r.filename,true);return;}
   if(r.effects&&target.audio.tracks.length>=20){toast('Limite de faixas atingido; mídia preservada: '+r.filename,true);return;}
   Object.assign(target.video_clipe,{arquivo:r.filename,inicio:0,repetir:false,fit:'contain'});target.componente_gil=r.component;
   if(r.effects)target.audio.tracks.push({file:r.filename,start:0,volume:.5,fade_in:0,fade_out:0,loop:false});
   if(Math.abs(target.duracao-r.duration)>.05&&confirm('Ajustar a duração da cena para '+r.duration.toFixed(2)+' s? O ajuste de narração do projeto continua válido.'))target.duracao=r.duration;
   dirtyNow(true);toast('Composição inserida. Salve o projeto; edite a narração em Áudio.');
 }catch(e){toast('Falha na composição: '+e.message,true);$('saveInfo').textContent='Composição não inserida';}
 finally{gilRendering=false;}
}
function downloadGIL(){const c=project?.cenas[selected]?.componente_gil;if(!c)return;const url=URL.createObjectURL(new Blob([c.source],{type:'text/plain'}));const a=document.createElement('a');a.href=url;a.download='componente-'+c.source_sha256.slice(0,12)+'.gil';a.click();setTimeout(()=>URL.revokeObjectURL(url),3000);}
async function importClip(file){if(!file)return;const index=selected;try{const r=await uploadChunked(file,'video');attachVideo(index,r.filename);}catch(e){toast('Falha ao importar vídeo: '+e.message,true);}}
function animationJump(fraction){playTime=startOf(selected)+Math.min(.999,Math.max(0,fraction))*Number(project.cenas[selected].duracao);playing=false;$('playButton').textContent='▶';lastFrame=0;showPreview();}
function sampleAnimation(){const animations=project.cenas[selected].animacoes;
 animations.push({alvo:'__titulo__',tipo:'fade',inicio:0,fim:.35,easing:'suave',de:0,ate:1,de_x:0,de_y:0,ate_x:0,ate_y:0});
 animations.push({alvo:'__conteudo__',tipo:'translacao',inicio:0,fim:.7,easing:'suave',de:0,ate:0,de_x:-170,de_y:0,ate_x:0,ate_y:0});
 dirtyNow(true);animationJump(.05);toast('Exemplo criado. Arraste a barra de tempo para visualizar.');}
async function upload(file,path){if(!file)return;if(file.size>12e6)return toast('Arquivo máximo: 12 MB',true);
 let kind=path.endsWith('imagem.arquivo')?'image':'audio';const data=await new Promise((yes,no)=>{let fr=new FileReader();fr.onload=()=>yes(fr.result);fr.onerror=no;fr.readAsDataURL(file);});
 try{const r=await post('/api/upload',{kind,data,filename:file.name});setPath(path,r.filename);dirtyNow(true);drawEditor();toast('Arquivo importado: '+r.filename);if(kind==='image')await openImageComposer();}catch(e){toast(e.message,true);}}
function moveScene(i,shift){clearMediaPlayers();let j=i+shift;if(j<0||j>=project.cenas.length)return;[project.cenas[i],project.cenas[j]]=[project.cenas[j],project.cenas[i]];selected=j;playTime=startOf(selected);dirtyNow(true);}
function parseFields(e){let el=e.target;const path=el.dataset.path;if(path){let v=el.type==='checkbox'?el.checked:el.value;if(el.type==='number'){v=Number(v);if(!Number.isFinite(v))return;}if(path.includes('.gil_nativo.')&&el.type==='number')v=Math.max(/\.(w|h)$/.test(path)?.08:0,Math.min(1,v));setPath(path,v);
   if(path.endsWith('.video_clipe.arquivo')){const i=Number(path.split('.')[1]);if(project.cenas[i])delete project.cenas[i].componente_gil;}
   if(path.endsWith('voice_text')){setPath(`cenas.${selected}.fala`,v);if(v.trim())setPath(`cenas.${selected}.audio.voice_enabled`,true);}
   if(path.endsWith('.id')&&!/^[A-Za-z0-9_-]{1,64}$/.test(v))return toast('ID inválido',true);
   if(path.startsWith('video.')){drawEverything();}
   dirtyNow(path.endsWith('.tipo')||path.endsWith('.fit')||path.includes('.animacoes.')&&(path.endsWith('.tipo')||path.endsWith('.alvo')));return;
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
function showDrawer(id){for(const key of ['timingDialog','workspaceProjects','workspaceLibrary'])$(key).hidden=key!==id;if(id)$(id).scrollIntoView({block:'start',behavior:'smooth'});}
function stopWorkspace(){playing=false;cancelAnimationFrame(previewRaf);previewRaf=0;lastFrame=0;$('playButton').textContent='▶';$('stageClip').pause();objectRuntime?.pauseObjects($('stageShell'));stopTransport();objectEditor?.paint();}
function bindTiming(){
 const dialog=$('timingDialog');
 const range=()=>{if(!project)throw Error('Selecione um projeto.');const scope=$('timingScope').value,first=scope==='all'?0:scope==='current'?selected:Number($('timingFirst').value)-1,last=scope==='all'?project.cenas.length-1:scope==='current'?selected:Number($('timingLast').value)-1;if(!Number.isInteger(first)||!Number.isInteger(last)||first<0||last<first||last>=project.cenas.length)throw Error('Intervalo inválido');return {first,last};};
 const snapshot=()=>JSON.stringify({project,...range()});
 const makePlan=()=>{
   const {first,last}=range(),mode=$('timingMode').value;
   if(mode==='fit'){
      if(!fitResult||fitResult.project!==project||fitResult.snapshot!==snapshot())throw Error('Meça os arquivos de voz para a seleção atual.');
      return fitResult.rows.filter(r=>r.status==='ok'&&r.after!==r.before).map(r=>({scene:project.cenas[r.index],before:r.before,after:r.after,other:r.other_audio||r.clip}));
   }
   const raw=$('timingValue').value;if(!raw.trim())throw Error('Informe um valor.');return window.StudioTimingV37.plan(project.cenas,first,last,mode,Number(raw));
 };
 const summary=()=>{
   $('timingRange').hidden=$('timingScope').value!=='range';
   const mode=$('timingMode').value,scale=mode==='scale',fit=mode==='fit';$('timingValueField').hidden=fit;$('timingMeasure').hidden=!fit;$('timingValueLabel').textContent=scale?'Fator (ex.: 1,5)':'Segundos';$('timingValue').min=scale?'0.001':'0.5';$('timingValue').max=scale?'1200':'600';
   $('timingUndo').disabled=!(timingHistory&&timingHistory.project===project)||saving||workspaceBusy;
   $('timingRows').innerHTML='';
   try{const list=makePlan(),delta=list.reduce((n,e)=>n+e.after-e.before,0);$('timingSummary').textContent=list.length+' cenas alteradas · total nominal: '+(totalDuration()+delta).toFixed(2)+' s';$('timingApply').disabled=!list.length||saving||workspaceBusy;
     if(fit){$('timingRows').innerHTML=fitResult.rows.map(r=>`<div><b>${r.index+1}. ${esc(r.title)}</b><small>${r.status==='ok'?Number(r.before).toFixed(2)+' → '+Number(r.after).toFixed(2)+' s · voz '+Number(r.voice_seconds).toFixed(2)+' s'+(r.other_audio||r.clip?' · possui outras mídias':''):esc(r.status)}</small></div>`).join('');}
   }catch(e){$('timingSummary').textContent=e.message;$('timingApply').disabled=true;}
 };
 $('batchTiming').onclick=()=>{if(!project)return;stopWorkspace();$('timingFirst').max=$('timingLast').max=project.cenas.length;$('timingFirst').value=1;$('timingLast').value=project.cenas.length;fitResult=null;summary();showDrawer('timingDialog');};
 for(const id of ['timingScope','timingMode','timingFirst','timingLast','timingValue'])$(id).addEventListener('input',summary);
 $('timingClose').onclick=$('timingCloseTop').onclick=()=>showDrawer(null);
 $('timingMeasure').onclick=async()=>{if(workspaceBusy||!project)return;try{const snap=snapshot(),p=project;workspaceBusy=true;$('timingMeasure').disabled=true;$('timingSummary').textContent='Medindo locuções prontas…';const r=await post('/api/workspace/voice-plan',{project:cp(project),...range()});if(project!==p||snapshot()!==snap)throw Error('A seleção ou o projeto mudou; meça novamente.');fitResult={project:p,snapshot:snap,rows:r.rows};}catch(e){fitResult=null;toast(e.message,true);}finally{workspaceBusy=false;$('timingMeasure').disabled=false;summary();}};
 $('timingApply').onclick=()=>{if(saving||workspaceBusy)return;try{const edits=makePlan();if(!edits.length)return;if(edits.some(e=>e.after<e.before&&(e.other||e.scene.video_clipe?.arquivo||e.scene.audio?.tracks?.length||e.scene.audio?.music_file||project.trilha))&&!confirm('Reduzir cenas pode cortar a reprodução de clipes, música e efeitos. Os arquivos não serão apagados. Aplicar?'))return;window.StudioTimingV37.apply(edits);timingHistory={project,edits};fitResult=null;stopWorkspace();playTime=startOf(selected);dirtyNow(true);summary();toast('Durações atualizadas. Salve para persistir.');}catch(e){toast(e.message,true);summary();}};
 $('timingUndo').onclick=()=>{if(saving||!timingHistory||timingHistory.project!==project)return;try{window.StudioTimingV37.undo(timingHistory.edits,project.cenas);timingHistory=null;fitResult=null;stopWorkspace();playTime=startOf(selected);dirtyNow(true);summary();toast('Último lote desfeito.');}catch(e){toast(e.message,true);}};
 $('previewFull').onclick=async()=>{try{const el=$('previewFullHost');if(document.fullscreenElement===el)await document.exitFullscreen();else if(el.requestFullscreen)await el.requestFullscreen();else throw Error('Tela cheia indisponível; abra em Apresentar.');}catch(e){toast(e.message,true);}};$('stageShell').addEventListener('dblclick',()=>{if(document.fullscreenElement===$('previewFullHost'))document.exitFullscreen()?.catch(()=>{});});$('previewFullExit').onclick=()=>document.exitFullscreen?.().catch(e=>toast(e.message,true));
 $('previewRate').onchange=()=>{previewRate=Number($('previewRate').value)||1;$('stageClip').playbackRate=previewRate;lastFrame=0;};
 $('stageClip').addEventListener('loadedmetadata',()=>{if(!project)return;const s=sceneAt(playTime);if(clipPreviewScene===s.i)syncPreviewVideo(s.i,s.progress);});
}
function libraryTargets(){if(!project)return;const el=$('motionTarget'),old=el.value;el.innerHTML=animationTargets(project.cenas[selected]).map(([id,title])=>`<option value="${esc(id)}">${esc(title)}</option>`).join('');if([...el.options].some(o=>o.value===old))el.value=old;}
function insertLibraryObject(kind){if(!project||saving)return;try{
 const fresh=$('libraryNewScene').checked,old=project.cenas[selected];if(!fresh&&old.tipo!=='svg')throw Error('Selecione uma cena SVG ou marque Criar nova cena.');if(fresh&&project.cenas.length>=150)throw Error('Limite de 150 cenas.');
 const c=fresh?sceneBase():old, parser=new DOMParser();const height=Math.round(1280*project.video.height/project.video.width);
 let root,logicalHeight=height;
 if(fresh){root=parser.parseFromString(`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 ${height}"/>`,'image/svg+xml').documentElement;}
 else {const source=c.svg.trim();root=parser.parseFromString(/^<svg(?:\s|>)/i.test(source)?source:`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720">${source}</svg>`,'image/svg+xml').documentElement;const vb=(root.getAttribute('viewBox')||'0 0 1280 720').trim().split(/[ ,]+/).map(Number);if(root.localName!=='svg'||vb.length!==4||vb[0]!==0||vb[1]!==0||vb[2]!==1280||!Number.isFinite(vb[3]))throw Error('Use um SVG canônico 0 0 1280 H para inserir neste desenho.');logicalHeight=vb[3];}
 const prefix='obj_'+Date.now().toString(36)+'_'+(++librarySerial).toString(36),obj=window.StudioWorkspaceV38.object(kind,prefix,logicalHeight,fresh?8:Number(c.duracao));
 if((fresh?0:c.animacoes.length)+obj.tracks.length>32)throw Error('Limite de 32 faixas da cena. Crie uma nova cena ou remova animações.');
 const node=parser.parseFromString(`<svg xmlns="http://www.w3.org/2000/svg">${obj.markup}</svg>`,'image/svg+xml').documentElement;if(node.localName!=='svg')throw Error('Objeto inválido');
 for(const item of [...node.children])root.appendChild(root.ownerDocument.importNode(item,true));const svg=new XMLSerializer().serializeToString(root);if(svg.length>2000000)throw Error('SVG excede limite.');
 if(fresh){Object.assign(c,{tipo:'svg',titulo:obj.title.toUpperCase(),subtitulo:'',categoria:'',fonte:'',duracao:8,cores:{fundo:'#101c2b',destaque:'#79cdd2',texto:'#edf4f7'},animacoes:[],movimento:'linear'});project.cenas.splice(selected+1,0,c);selected++;}
 c.svg=svg;c.animacoes.push(...obj.tracks);stopWorkspace();playTime=startOf(selected);dirtyNow(true);libraryTargets();toast('Objeto inserido. Salve para persistir.');
 }catch(e){toast(e.message,true);}}
async function refreshWorkspaceProjects(){if(!project)return;const target=project;try{const [r,a]=await Promise.all([post('/api/workspace/inventory',{project:cp(project)}),api('/api/workspace/archived')]);if(project!==target)return;$('workspaceInventory').innerHTML=r.files.length?r.files.map(f=>`<div><b>${esc(f.file)}</b><small>${f.present?(f.bytes/1024).toFixed(1)+' KiB':'Ausente'} · ${esc(f.uses.join(' · '))}</small></div>`).join(''):'<p class="info">Sem mídia referenciada neste projeto.</p>';$('archivedList').innerHTML=a.projects.length?a.projects.map(n=>`<div><b>${esc(n)}</b><button data-restore-project="${esc(n)}">Restaurar</button></div>`).join(''):'<p class="info">Nenhum projeto arquivado.</p>';}catch(e){toast(e.message,true);}}
async function changeProjectArchive(action,n){if(!project||saving||workspaceBusy||busy||gilRendering)return toast('Aguarde concluir a operação atual.',true);if(!confirm((action==='archive'?'Arquivar ':'Restaurar ')+n+'? As mídias serão preservadas.'))return;workspaceBusy=true;const freeze=[document.querySelector('.top'),document.querySelector('main.workspace'),document.querySelector('.mobileTabs'),$('workspaceProjects')];freeze.forEach(el=>el.inert=true);try{const snap=JSON.stringify(project);await save();if(JSON.stringify(project)!==snap)throw Error('O projeto mudou durante o salvamento. Tente novamente.');await post('/api/workspace/archive',{action,name:n,confirm:n});let list=await listProjects();if(action==='archive'){dirty=false;await load(list[0]);}await refreshWorkspaceProjects();toast(action==='archive'?'Projeto arquivado':'Projeto restaurado');}catch(e){toast(e.message,true);}finally{freeze.forEach(el=>el.inert=false);workspaceBusy=false;}}
function bindWorkspace(){
 $('manageProjects').onclick=()=>{showDrawer('workspaceProjects');refreshWorkspaceProjects();};$('closeProjects').onclick=()=>showDrawer(null);$('projectInventory').onclick=refreshWorkspaceProjects;$('projectBundleShortcut').onclick=()=>$('exportBundle').click();$('archiveProject').onclick=()=>changeProjectArchive('archive',projectName);$('archivedList').onclick=e=>{let b=e.target.closest('[data-restore-project]');if(b)changeProjectArchive('restore',b.dataset.restoreProject);};
 $('openLibrary').onclick=()=>{if(!project)return;libraryTargets();showDrawer('workspaceLibrary');};$('closeLibrary').onclick=()=>showDrawer(null);
 $('objectCatalog').innerHTML=window.StudioWorkspaceV38.catalog.map(([id,title],i)=>`<button type="button" data-library-object="${id}"><svg viewBox="${id==='wave'||id==='flow'?'110 315 1060 300':'365 220 550 480'}" aria-hidden="true">${window.StudioWorkspaceV38.object(id,'obj_tile_'+i,720,8).markup}</svg>${esc(title)}</button>`).join('');
 $('objectCatalog').onclick=e=>{let b=e.target.closest('[data-library-object]');if(b)insertLibraryObject(b.dataset.libraryObject);};
 $('motionPreset').innerHTML=window.StudioWorkspaceV38.motions.map(([k,t])=>`<option value="${k}">${esc(t)}</option>`).join('');
 $('applyMotion').onclick=()=>{if(!project||saving)return;try{const c=project.cenas[selected],target=$('motionTarget').value;if(!animationTargets(c).some(([id])=>id===target))throw Error('Selecione novamente o objeto');const a=window.StudioWorkspaceV38.motion(target,$('motionPreset').value,Number(c.duracao));if(c.animacoes.length+a.length>32)throw Error('Limite de 32 faixas da cena');c.animacoes.push(...a);stopWorkspace();playTime=startOf(selected);dirtyNow(true);toast('Movimento aplicado. Salve para persistir.');}catch(e){toast(e.message,true);}};
 $('gilLibraryDownload').onclick=async()=>{try{const r=await api('/api/workspace/gil-example?id='+encodeURIComponent($('gilLibrarySelect').value));const url=URL.createObjectURL(new Blob([r.source],{type:'text/plain'}));const link=document.createElement('a');link.href=url;link.download=r.name;link.click();setTimeout(()=>URL.revokeObjectURL(url),3000);toast('Fonte GIL baixada. Abra no editor GIL para exportar componente HTML nativo.');}catch(e){toast(e.message,true);}};
 $('workspaceGILLink').onclick=e=>{if(inWorkspace()){e.preventDefault();parent.postMessage({protocol:'rd-workspace-1',type:'navigate',to:'gil'},WORKSPACE);}}; $('gilLibraryFile').onclick=()=>{if(objectEditor)objectEditor.open();else{forceGilLegacy=false;$('gilFile').click();}};$('gilLibraryInsert').onclick=async()=>{if(objectEditor){objectEditor.open($('gilLibrarySelect').value);return;}if(gilRendering||!project)return;const scene=project.cenas[selected];try{const r=await api('/api/workspace/gil-example?id='+encodeURIComponent($('gilLibrarySelect').value));if(project.cenas[selected]!==scene)throw Error('A cena mudou durante a leitura');await importGIL(new File([r.source],r.name,{type:'text/plain'}));}catch(e){toast(e.message,true);}};
 $('quickNarration').onclick=()=>{if(!project)return;showDrawer(null);tab='audio';document.querySelectorAll('[data-edit]').forEach(b=>b.classList.toggle('on',b.dataset.edit==='audio'));drawEditor();switchPane('editPanel');$('editPanel').scrollIntoView({block:'start'});};
}
function bind(){
 bindTiming();bindWorkspace();
 $('studio-v3-vetorial-link').onclick=e=>{e.preventDefault();openPlayback('/player-v3/?project=');};
 const layers=window.StudioLayersV36.connect({get:()=>({project,selected,projectName,playing}),change:()=>dirtyNow(true),notify:toast,jump});
 $('openLayersV36').onclick=()=>layers.open();
 $('projectSelect').onchange=e=>{if(workspaceBusy||saving){e.target.value=projectName;return toast('Aguarde a operação atual.',true);}showDrawer(null);load(e.target.value).catch(x=>toast(x.message,true));};
 window.addEventListener('resize',()=>{if(project){const portrait=project.video.height>project.video.width;const ratio=project.video.width/project.video.height;$('stageShell').style.width=portrait?Math.max(160,Math.round(Math.min(window.innerWidth*.92,window.innerHeight*.70*ratio)))+'px':'';}});
 $('saveButton').onclick=()=>save(true).then(()=>toast('Salvo no celular')).catch(e=>toast(e.message,true));
 $('newProject').onclick=async()=>{let n=prompt('Nome identificador, sem espaços:','novo_projeto');if(!n)return;try{let r=await post('/api/project/new',{name:n,titulo:'Meu documentário'});await listProjects();await load(r.name);toast('Projeto criado');}catch(e){toast(e.message,true);}};
 $('exportButton').onclick=exportJSON;
 $('exportBundle').onclick=async()=>{try{await save();window.location.href='/api/project/bundle?name='+encodeURIComponent(projectName);}catch(e){toast('Não foi possível preparar ZIP: '+e.message,true);}};
 $('importBundle').onclick=()=>$('bundleFile').click();
 $('bundleFile').onchange=async e=>{const f=e.target.files[0];if(!f)return;
   const suggested=f.name.replace(/\.zip$/i,'').replace(/[^A-Za-z0-9_-]/g,'_').slice(0,52);
   const desired=prompt('Nome do projeto importado (será renomeado se já existir):',suggested||'importado');
   if(desired===null){e.target.value='';return;}
   try{const r=await uploadChunked(f,'bundle',desired);await listProjects();await load(r.name);toast('ZIP importado: '+r.name+' ('+Object.keys(r.media).length+' mídias)');}
   catch(err){toast('Falha ao importar ZIP: '+err.message,true);}e.target.value='';};
 $('importButton').onclick=()=>$('jsonFile').click();
 $('editJson').onclick=()=>{lastJsonMode='scene';openJson();};
 $('closeJson').onclick=()=>$('jsonDialog').close();
 let lastJsonMode='scene';$('jsonMode').onchange=()=>{if($('jsonText').value!==JSON.stringify(lastJsonMode==='scene'?project.cenas[selected]:project,null,2)&&!confirm('Descartar alterações não aplicadas no texto JSON?')){$('jsonMode').value=lastJsonMode;return;}lastJsonMode=$('jsonMode').value;fillJsonText();};
 $('refreshJson').onclick=()=>{if(confirm('Recarregar JSON e descartar edições não aplicadas?'))fillJsonText();};
 $('validateJson').onclick=()=>checkJson(false);$('applyJson').onclick=()=>checkJson(true);

 $('jsonFile').onchange=async e=>{const f=e.target.files[0];if(!f)return;try{const data=JSON.parse(await f.text());let n=prompt('Nome do projeto importado:',f.name.replace(/\.json$/i,'').replace(/[^A-Za-z0-9_-]/g,'_'));if(!n)return;await post('/api/project',{name:n,project:data});await listProjects();await load(n);toast('JSON importado e migrado');}catch(e){toast(e.message,true);}e.target.value='';};
 $('sceneList').onclick=e=>{let mv=e.target.closest('[data-shift]');if(mv)return moveScene(Number(mv.dataset.index),Number(mv.dataset.shift));let b=e.target.closest('[data-scene]');if(b)jump(Number(b.dataset.scene));};
 bindTimeline();$('timeline').onclick=e=>{let b=e.target.closest('[data-scene]');if(b)jump(Number(b.dataset.scene));};
 $('addScene').onclick=()=>{project.cenas.splice(selected+1,0,sceneBase());selected++;playTime=startOf(selected);dirtyNow(true);};
 $('addSpatialScene').onclick=()=>{let c=sceneBase();c.tipo='espacial';c.titulo='CENA ESPACIAL';c.espacial={camera:{azimute:28,elevacao:18,distancia:9},objetos:[{id:'centro',tipo:'esfera',cor:'#67bfe9',posicao:[-1.5,0,0]},{id:'bloco',tipo:'cubo',cor:'#e4a46d',posicao:[1.3,0,0]}],animacoes:[{alvo:'bloco',propriedade:'rotacao_y',inicio:0,fim:1,de:0,ate:360}]};project.cenas.splice(selected+1,0,c);selected++;playTime=startOf(selected);dirtyNow(true);};
 $('addSvgScene').onclick=()=>{let c=sceneBase();c.tipo='svg';c.titulo='ILUSTRAÇÃO VETORIAL';c.svg='<g class="layer" id="camada1"><title>Camada 1</title><circle cx="640" cy="360" r="125" fill="#d99a62"/></g>';project.cenas.splice(selected+1,0,c);selected++;playTime=startOf(selected);dirtyNow(true);};
 $('openSvgFromTop').onclick=openOrCreateSVG;
 $('quickImage').onclick=()=>project.cenas[selected].imagem.arquivo?openImageComposer():requestImageFile();
 $('editSVG').onclick=async()=>{
  if(project.cenas[selected].tipo!=='svg')return toast('Selecione uma cena SVG ou use + SVG para criar uma.',true);
  const popup=window.open('about:blank','_blank');
  try{await save();const url='/vetor?name='+encodeURIComponent(projectName)+'&scene='+(selected+1);if(popup)popup.location.href=url;else window.location.href=url;}
  catch(e){if(popup)popup.close();toast('Não foi possível abrir o editor: '+e.message,true);}
 };

 $('nativeDemoPreview').onclick=()=>objectEditor?objectEditor.open('native-demo'):demoNativeGIL();
 $('playButton').onclick=()=>{playing=!playing;lastFrame=0;if(playing&&playTime>=totalDuration())playTime=0;$('playButton').textContent=playing?'Ⅱ':'▶';if(playing){if(transportBlocked)stopTransport(true);transportBlocked=false;transportSeek=true;transportDeadline=performance.now()+5000;$('voicePlayer').pause();$('scenePlayer').pause();if(dirty&&!audioSnapshotMatches()&&$('previewSound').checked)$('transportStatus').textContent='Salve o projeto para ouvir o áudio correspondente.';syncTransport();cancelAnimationFrame(previewRaf);previewRaf=requestAnimationFrame(tick);}else{cancelAnimationFrame(previewRaf);previewRaf=0;$('stageClip').pause();objectRuntime?.pauseObjects($('stageShell'));stopTransport();objectEditor?.paint();}}; $('previewSound').onchange=()=>{stopTransport(true);syncTransport();};
 $('seek').oninput=e=>{if(!project)return;transportSeek=true;transportBlocked=false;transportDeadline=performance.now()+5000;lastFrame=0;playTime=totalDuration()*Number(e.target.value)/1000;selected=sceneAt(playTime).i;drawSceneList();drawTimeline();drawEditor();objectEditor?.refresh();showPreview();syncTransport();};
 document.querySelectorAll('.mobileTabs button').forEach(b=>b.onclick=()=>switchPane(b.dataset.pane));
 document.querySelectorAll('[data-edit]').forEach(b=>b.onclick=()=>{tab=b.dataset.edit;document.querySelectorAll('[data-edit]').forEach(k=>k.classList.toggle('on',k===b));drawEditor();});
 $('editor').addEventListener('change',parseFields);
 $('editor').addEventListener('change',e=>{if(e.target.id==='reuseImage'&&e.target.value){project.cenas[selected].imagem.arquivo=e.target.value;dirtyNow(true);}});
 $('editor').onclick=async e=>{
  let t=e.target;if(t.dataset.upload){assetPath=t.dataset.upload;$('mediaFile').accept=assetPath.endsWith('imagem.arquivo')?'image/*':'audio/*';$('mediaFile').click();return;}
  if(t.id==='editSpatial'){
   const popup=window.open('about:blank','_blank');
   try{await save();const url='/espacial?name='+encodeURIComponent(projectName)+'&scene='+(selected+1);if(popup)popup.location.href=url;else location.href=url;}catch(err){if(popup)popup.close();toast(err.message,true);}
   return;
  }
  if(t.id==='imageComposerOpen'){openImageComposer();return;}
  if(t.id==='voiceThisShortcut'){begin('audio-cena');return;}
  if(t.id==='voiceAllShortcut'){begin('audio');return;}
  if(t.id==='voiceTimingShortcut'){$('batchTiming').click();$('timingMode').value='fit';$('timingMode').dispatchEvent(new Event('input'));return;}
  if(t.id==='addAnimation'){addSceneAnimation();return;}
  if(t.id==='sampleAnimation'){sampleAnimation();return;}
  if(t.id==='insertNativeDemo'){if(objectEditor)objectEditor.open('native-demo');else await demoNativeGIL();return;}
  if(t.id==='insertGIL'){if(objectEditor)objectEditor.open();else toast('Editor de objetos indisponível',true);return;}if(t.id==='insertGILLegacy'){if(!gilRendering){forceGilLegacy=true;$('gilFile').click();}return;}
  if(t.id==='removeNativeGIL'){if(confirm('Remover somente a camada GIL nativa?')){delete project.cenas[selected].gil_nativo;dirtyNow(true);}return;}
  if(t.id==='editNativeGIL'||t.id==='downloadNativeGIL'){const c=project.cenas[selected].gil_nativo;if(!c)return;if(t.id==='editNativeGIL'&&inWorkspace()){parent.postMessage({protocol:'rd-workspace-1',type:'edit-gil',source:c.source},WORKSPACE);return;}const url=URL.createObjectURL(new Blob([c.source],{type:'text/plain'}));const a=document.createElement('a');a.href=url;a.download='nativo-'+c.source_sha256.slice(0,12)+'.gil';a.click();setTimeout(()=>URL.revokeObjectURL(url),3000);return;}
  if(t.id==='sourceGIL'){downloadGIL();return;}
  if(t.id==='openGIL'){if(inWorkspace())parent.postMessage({protocol:'rd-workspace-1',type:'navigate',to:'gil'},WORKSPACE);else location.href='http://127.0.0.1:8791/';return;}
  if(t.id==='editGILWorkspace'){const source=project?.cenas[selected]?.componente_gil?.source;if(inWorkspace()&&source)parent.postMessage({protocol:'rd-workspace-1',type:'edit-gil',source},WORKSPACE);else downloadGIL();return;}
  if(t.id==='importClip'){$('clipFile').click();return;}
  if(t.id==='recordCamera'){captureMedia('video');return;}
  if(t.id==='recordVoice'){captureMedia('audio');return;}
  if(t.id==='removeSceneAudio'){
    if(!confirm('Remover somente os arquivos vinculados de locução, música e efeitos? O texto do roteiro e a voz neural serão preservados.'))return;
    const au=project.cenas[selected].audio;
    Object.assign(au,{voice_file:'',music_file:'',tracks:[],muted:false});
    clearMediaPlayers();dirtyNow(true);toast('Arquivos desvinculados. Texto preservado. Salve o projeto.');return;
  }
  if(t.id==='removeVoiceFile'){
    project.cenas[selected].audio.voice_file='';clearMediaPlayers();dirtyNow(true);toast('Locução gravada desvinculada; texto preservado.');return;
  }
  if(t.id==='removeSceneMusic'){
    project.cenas[selected].audio.music_file='';clearMediaPlayers();dirtyNow(true);toast('Trilha específica removida da cena.');return;
  }
  if(t.id==='enableSceneAudio'){
    project.cenas[selected].audio.muted=false;dirtyNow(true);toast('Som reativado. Vincule novas mídias ou use a trilha global.');return;
  }
  if(t.id==='exportVoiceMp3'){begin('voz-mp3');return;}
  if(t.id==='editClipVisual'){if(!project.cenas[selected].video_clipe.arquivo)return toast('Importe um vídeo primeiro',true);clipEditingEnabled(true);switchPane('previewPanel');return;}
  if(t.id==='removeClip'){
    const clip=project.cenas[selected].video_clipe;
    if(!clip?.arquivo)return;
    if(!confirm('Remover o vídeo desta cena? O arquivo original e a narração permanecem preservados.'))return;
    clip.arquivo='';delete project.cenas[selected].componente_gil;
    clipEditingEnabled(false);
    const video=$('stageClip');video.pause();video.hidden=true;video.removeAttribute('src');video.load();
    clipPreviewFile='';clipPreviewScene=-1;
    dirtyNow(true);toast('Vídeo desvinculado da cena. Salve o projeto.');return;
  }
  if(t.dataset.removeAnimation!==undefined){project.cenas[selected].animacoes.splice(Number(t.dataset.removeAnimation),1);dirtyNow(true);return;}
  if(t.dataset.removeTrack!==undefined){project.cenas[selected].audio.tracks.splice(Number(t.dataset.removeTrack),1);dirtyNow(true);}
  if(t.id==='addTrack'){project.cenas[selected].audio.tracks.push({file:'',start:0,volume:.4,fade_in:0,fade_out:0,loop:false});dirtyNow(true);}
  if(t.id==='duplicateScene'){let dup=cp(project.cenas[selected]);dup.id='cena_'+Date.now();project.cenas.splice(++selected,0,dup);playTime=startOf(selected);dirtyNow(true);}
  if(t.id==='removeScene'){if(project.cenas.length<=1)return toast('O projeto precisa ter uma cena',true);if(!confirm('Excluir cena '+(selected+1)+'?'))return;project.cenas.splice(selected,1);selected=Math.max(0,selected-1);playTime=startOf(selected);dirtyNow(true);}
  if(t.id==='moveUp')moveScene(selected,-1);if(t.id==='moveDown')moveScene(selected,1);
  if(t.dataset.shape){const shapes={circle:'<circle cx="640" cy="360" r="135" fill="#d99a62"/>',rect:'<rect x="425" y="255" width="430" height="210" rx="65" fill="#d99a62"/>',path:'<path d="M250,510 Q460,200 640,450 T1030,250" fill="none" stroke="#d99a62" stroke-width="25"/>',text:'<text x="640" y="365" text-anchor="middle" font-size="76" fill="#d99a62">OLÁ</text>'};project.cenas[selected].svg+='\n'+shapes[t.dataset.shape];dirtyNow(true);}
 };
 $('mediaFile').onchange=e=>{upload(e.target.files[0],assetPath);e.target.value='';};
 $('gilFile').onchange=e=>{const legacy=forceGilLegacy;forceGilLegacy=false;importGIL(e.target.files[0],legacy);e.target.value='';};
 $('clipFile').onchange=e=>{importClip(e.target.files[0]);e.target.value='';};
 $('editor').addEventListener('input',e=>{if(e.target.id==='animationSeek'){
   const val=Number(e.target.value);$('animationProgress').textContent=val+'%';animationJump(val/100);
 }});
 $('listenVoice').onclick=()=>playSceneAudio('voice');$('listenMix').onclick=()=>playSceneAudio('audio');
 $('watchScene').onclick=watchSceneVideo;$('listenAndroid').onclick=listenAndroid;
 $('exportHtml').onclick=()=>begin('export-html');$('exportHtmlSilent').onclick=()=>begin('export-html-silent');$('exportMp3').onclick=()=>begin('audio-mp3');$('exportOpus').onclick=()=>begin('audio-opus');$('toggleClipEdit').onclick=()=>clipEditingEnabled(!clipEditing);initClipGesture();
 $('makeFrames').onclick=()=>begin('quadros');$('makeAudio').onclick=()=>begin('audio');$('makeSceneVoice').onclick=()=>begin('audio-cena');$('autoExtendVoice').onclick=()=>{project.encaixe_voz='estender';dirtyNow(true);toast('Renderização configurada para estender a cena até concluir a locução. Salve o projeto.');};$('mixAudio').onclick=()=>begin('mix');$('makeLite').onclick=()=>begin('render-leve');$('presentBtn').onclick=()=>openPlayback('/captura?name=');$('makeVideo').onclick=()=>begin('render');$('makeSilent').onclick=()=>begin('render',true);$('makeScene').onclick=()=>begin('cena');$('refreshCache').onclick=refreshCache;
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
let browserExport=null,browserOutputURL=null,browserOutputCleanup=null;
function clearBrowserOutput(){if(browserOutputURL)URL.revokeObjectURL(browserOutputURL);browserOutputURL=null;browserOutputCleanup?.().catch(console.warn);browserOutputCleanup=null;}
async function initBrowserRender(){
 const b=$('browserExport'),cancel=$('browserExportCancel'),canvas=$('browserRenderCanvas'),report=$('browserExportStatus'),download=$('browserDownload');
 try{const {exportBrowser}=await import('/browser-render.mjs');b.disabled=false;
 b.onclick=async()=>{if(!project||browserExport||busy||saving)return toast('Aguarde concluir a operação atual.',true);
  stopWorkspace();switchPane('previewPanel');const owner=cp(project),controller=new AbortController();browserExport=controller;b.disabled=true;cancel.hidden=false;canvas.hidden=false;report.textContent='Preparando exportação…';download.hidden=true;clearBrowserOutput();
  const play=$('playButton'),seek=$('seek'),wasPlay=play.disabled,wasSeek=seek.disabled;play.disabled=true;seek.disabled=true;
  try{const result=await exportBrowser(owner,{canvas,signal:controller.signal,status:msg=>{report.textContent=msg;}});browserOutputCleanup=result.cleanup||null;browserOutputURL=URL.createObjectURL(result.blob);download.href=browserOutputURL;download.download=(owner.titulo||'estudio').replace(/[^a-zA-Z0-9_-]+/g,'-').slice(0,80)+'.'+result.ext;download.textContent='Baixar vídeo · '+result.ext.toUpperCase();download.hidden=false;report.textContent=`Concluído: ${(result.blob.size/1048576).toFixed(2)} MiB · ${result.frames}/${result.totalFrames} quadros desenhados · ${result.missed} passos perdidos (encoder não medido).`;}
  catch(e){report.textContent='Exportação não concluída: '+e.message;}
  finally{browserExport=null;b.disabled=false;cancel.hidden=true;canvas.hidden=true;play.disabled=wasPlay;seek.disabled=wasSeek;showPreview();}
 };cancel.onclick=()=>browserExport?.abort();
 }catch(e){report.textContent='Exportação web indisponível: '+e.message;}
 window.addEventListener('pagehide',()=>{browserExport?.abort();if(browserOutputURL)URL.revokeObjectURL(browserOutputURL);});
}
async function init(){
 window.addEventListener('storage',e=>{
  if(e.key!=='estudioSvgVectorSave'||!e.newValue)return;
  try{const u=JSON.parse(e.newValue);syncVectorSave(u.name,u.scene);}catch(err){}
 });
 bind();void initObjects();void initBrowserRender();try{let projects=await listProjects();let requested=new URLSearchParams(location.search).get('project');let preferred=projects.includes(requested)?requested:projects.includes('demo_organico')?'demo_organico':projects[0];if(!preferred)throw Error('Nenhum projeto encontrado');await load(preferred);switchPane('previewPanel');let a=await api('/api/jobs/active');if(a.job)trackJob(a.job);if(inWorkspace())parent.postMessage({protocol:'rd-workspace-1',type:'ready'},WORKSPACE);}catch(e){toast(e.message,true);$('stage').textContent='Falha ao iniciar: '+e.message;}}
init();
})();
