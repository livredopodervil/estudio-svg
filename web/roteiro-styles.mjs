// Catálogo RD Studio. Referências conceituais externas documentadas em docs/ROTEIRO_02.md.
// Implementações novas, sem copiar assets nem depender de geradores externos.
export const STYLES=Object.freeze([
 {id:'editorial',name:'Editorial de dados',bg:'#14242c',fg:'#f2eee0',accent:'#ffb96a',accent2:'#61cbbf',font:67,entry:'esquerda',exit:'dissolver',note:'Uma afirmação, um dado e uma linha de base'},
 {id:'neon',name:'Neon técnico',bg:'#091323',fg:'#bffff5',accent:'#eb61b4',accent2:'#3cdde2',font:69,entry:'crescer',exit:'direita',note:'Sinais e contrastes de laboratório'},
 {id:'blueprint',name:'Desenho de engenharia',bg:'#102c4c',fg:'#dfedff',accent:'#ffca66',accent2:'#79c6ff',font:62,entry:'subir',exit:'dissolver',note:'Precisão e diagramas em destaque'},
 {id:'paper',name:'Papel e tinta',bg:'#f0e3c5',fg:'#28221d',accent:'#b64e35',accent2:'#607956',font:67,entry:'esquerda',exit:'encolher',note:'Cores de impressão e recortes'},
 {id:'signal',name:'Terminal / matriz',bg:'#0b1714',fg:'#b9f6d5',accent:'#d0ee65',accent2:'#56ae89',font:64,entry:'direita',exit:'dissolver',note:'Telemetria e caracteres de máquina'},
 {id:'cinema',name:'Cinema de arquivo',bg:'#16161b',fg:'#f4e3cd',accent:'#d6a971',accent2:'#a9b6bd',font:70,entry:'dissolver',exit:'dissolver',note:'Composição sóbria com pausas'},
 {id:'science',name:'Biologia / microscopia',bg:'#102f2c',fg:'#e0fff0',accent:'#b4e17f',accent2:'#6ac9ba',font:62,entry:'crescer',exit:'subir',note:'Diagrama orgânico e cores instrumentais'},
 {id:'brutal',name:'Tipografia brutalista',bg:'#f7e957',fg:'#151515',accent:'#e33f45',accent2:'#222222',font:77,entry:'descer',exit:'esquerda',note:'Contraste, assimetria e blocos'},
 {id:'noir',name:'Âmbar e sombra',bg:'#201528',fg:'#ffe2b4',accent:'#ea9738',accent2:'#7869a2',font:67,entry:'subir',exit:'encolher',note:'Luz quente sobre profundidade escura'},
 {id:'cartoon',name:'Quadrinhos',bg:'#f6e9de',fg:'#212430',accent:'#e84c48',accent2:'#4b8bc8',font:72,entry:'crescer',exit:'direita',note:'Gestos amplos e leitura rápida'},
 {id:'retro',name:'Televisor analógico',bg:'#1a262f',fg:'#e3e8e3',accent:'#ff8b71',accent2:'#88babb',font:63,entry:'direita',exit:'dissolver',note:'Paleta analógica e movimento contido'},
 {id:'botanical',name:'Art nouveau vegetal',bg:'#19382e',fg:'#e7edd4',accent:'#d5b77e',accent2:'#98be8f',font:68,entry:'subir',exit:'dissolver',note:'Ramos e moldura geométrica orgânica'}
]);
export function styleById(id){return STYLES.find(s=>s.id===id)||STYLES[0];}
export function createStyleBase({style='editorial',text='UMA IDEIA GANHA MOVIMENTO',subtitle='ROTEIRO • GIL',duration=8}={}){
 const p=styleById(style),d=Number(duration),title=String(text).trim().slice(0,100),sub=String(subtitle).trim().slice(0,90);
 if(!title||!Number.isFinite(d)||d<.5||d>60)throw Error('Título vazio ou duração fora de 0,5–60 segundos.');
 // Não contém áudio interno nem referências a mídia externa. A cena possui áudio independente.
 return `gil timeline 0.1 {\nstage ${JSON.stringify({width:1280,height:720,duration:d,background:p.bg,camera:'cam'})}\nresource camres camera {"z":15,"fov":45}\nresource head text ${JSON.stringify({text:title,fontSize:p.font,color:p.fg,layer:5})}\nresource sub text ${JSON.stringify({text:sub,fontSize:30,color:p.accent,layer:6})}\nresource dot shape.circle ${JSON.stringify({size:1.1,color:p.accent2,layer:2})}\nresource bar shape.rect ${JSON.stringify({width:6,height:.12,color:p.accent,layer:2})}\nobject cam camres - {}\nobject titulo head - {"y":0.75,"opacity":1}\nobject subtitulo sub - {"y":-1.0,"opacity":1}\nobject figura dot - {"x":3.6,"y":-2.45,"opacity":1}\nobject faixa bar - {"x":-2.5,"y":-2.75,"opacity":1}\n}\n`;
}
export function createStyleScript({style='editorial',duration=8}={}){
 const p=styleById(style),d=Number(duration);if(!Number.isFinite(d)||d<3||d>60)throw Error('Demonstração requer de 3 a 60 segundos.');
 const at=x=>Number(x.toFixed(2)),a=at(Math.min(1.1,d*.2)),b=at(Math.min(.9,d*.16)),end=at(d-Math.max(1.1,d*.18));
 return `roteiro 0.2 {\n  // Tempo absoluto: marcas independentes da taxa de quadros.\n  marca inicio 0s\n  marca destaque ${at(d*.4)}s\n  marca final ${end}s\n  em inicio {\n    paralelo {\n      entrada titulo ${p.entry} durante ${a}s\n      entrada subtitulo dissolver durante ${at(a+.25)}s\n      entrada figura crescer durante ${b}s\n    }\n  }\n  em destaque {\n    pulso figura durante ${b}s\n  }\n  em final {\n    paralelo {\n      saida titulo ${p.exit} durante 1s\n      saida subtitulo dissolver durante 1s\n      saida figura encolher durante 1s\n    }\n  }\n}\n`;
}
