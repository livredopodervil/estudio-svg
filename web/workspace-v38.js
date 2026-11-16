/* Declarative SVG objects and tracks. Same scene_animation/timeline_easing contract.
   No DOM, no network, no separate animation runtime. */
(function(g){'use strict';
 const catalog=[['orbit','Sistema orbital'],['network','Rede de relações'],['wave','Onda / sinal'],['flow','Fluxo de dados'],['radar','Radar / medida'],['particles','Campo de partículas']];
 const motions=[['enter','Entrada rápida'],['pulse','Pulso contínuo'],['orbit','Rotação contínua'],['swing','Oscilação'],['rise','Elevação']];
 function motion(id,kind,duration){
   if(!/^[A-Za-z_][A-Za-z0-9_.:-]{0,80}$/.test(id)||!Number.isFinite(duration)||duration<.5||duration>600)throw Error('Objeto ou duração inválida');
   const end=Math.min(1,1.05/duration), cycles=Math.max(1,Math.min(21,Math.round(duration/1.6)));
   const a={alvo:id,inicio:0,fim:1,easing:'suave',repeticoes:0,yoyo:false,de:0,ate:0,de_x:0,de_y:0,ate_x:0,ate_y:0};
   if(kind==='enter')return [{...a,tipo:'translacao',fim:end,easing:'expo.out',de_x:-150},{...a,tipo:'fade',fim:end,ate:1}];
   if(kind==='rise')return [{...a,tipo:'translacao',fim:end,easing:'power2.out',de_y:110},{...a,tipo:'fade',fim:end,ate:1}];
   if(kind==='pulse')return [{...a,tipo:'escala',de:.88,ate:1.12,repeticoes:cycles-1,yoyo:true,easing:'sine.inOut'}];
   if(kind==='orbit')return [{...a,tipo:'rotacao',de:0,ate:360,repeticoes:Math.max(0,Math.min(20,Math.round(duration/3)-1)),easing:'linear'}];
   if(kind==='swing')return [{...a,tipo:'translacao',de_x:-36,ate_x:36,repeticoes:cycles-1,yoyo:true,easing:'sine.inOut'}];
   throw Error('Movimento desconhecido');
 }
 function object(kind,prefix,height,duration){
   if(!catalog.some(e=>e[0]===kind)||!/^obj_[a-z0-9_]{1,40}$/.test(prefix)||!Number.isFinite(height)||height<320||height>4800)throw Error('Componente inválido');
   const h=height, cy=h>900?h*.59:Math.min(h-165,Math.max(h*.62, h-230)), cx=640, R=Math.max(55,Math.min(205,h>900?h*.15:h*.19));
   let markup='',tracks=[],n=0;
   function id(){return prefix+'_'+(++n)}
   function add(tag,attr,move){const k=id();markup+=`<${tag} id="${k}" ${attr}/>`;if(move)tracks.push(...motion(k,move,duration));return k;}
   const pt=(a,r=R)=>[cx+r*Math.cos(a),cy+r*Math.sin(a)];
   if(kind==='orbit'){
     const colors=['#78d9df','#edbc77','#a8a9ff'];
     for(let i=0;i<3;i++){let r=R*(.53+.25*i);add('ellipse',`cx="${cx}" cy="${cy}" rx="${r*1.45}" ry="${r*.55}" fill="none" stroke="${colors[i]}" stroke-width="${3+i}" stroke-opacity=".78" transform="rotate(${i*52} ${cx} ${cy})"`,'orbit');}
     add('circle',`cx="${cx}" cy="${cy}" r="${R*.24}" fill="#f0c676" stroke="#ffe5bb" stroke-width="4"`,'pulse');
     for(let i=0;i<9;i++){const [x,y]=pt(i*Math.PI*2/9,R*1.6);add('circle',`cx="${x}" cy="${y}" r="${R*.045}" fill="${colors[i%3]}"`,'pulse');}
   }else if(kind==='network'){
     const nodes=Array.from({length:9},(_,i)=>pt(i*Math.PI*2/9,R*(i%2?1.38:1.65)));
     for(let i=0;i<nodes.length;i++){const [x,y]=nodes[i], [xx,yy]=nodes[(i+2)%nodes.length];add('line',`x1="${x}" y1="${y}" x2="${xx}" y2="${yy}" stroke="#79b4ce" stroke-opacity=".36" stroke-width="3"`);add('line',`x1="${cx}" y1="${cy}" x2="${x}" y2="${y}" stroke="#79b4ce" stroke-opacity=".48" stroke-width="3"`);}
     add('circle',`cx="${cx}" cy="${cy}" r="${R*.24}" fill="#e9b36f"`,'pulse');
     for(let i=0;i<nodes.length;i++){const [x,y]=nodes[i];add('circle',`cx="${x}" cy="${y}" r="${R*.10}" fill="${i%2?'#78cdd4':'#9fa7ef'}"`,'pulse');}
   }else if(kind==='wave'){
     let width=840, top=cy-R*.8,bottom=cy+R*.8;
     for(let i=0;i<5;i++)add('line',`x1="220" y1="${top+i*(bottom-top)/4}" x2="1060" y2="${top+i*(bottom-top)/4}" stroke="#8aa5bf" opacity=".22" stroke-width="2"`);
     for(let i=0;i<19;i++){let x=220+i*width/18,y=cy+R*.55*Math.sin(i*.65);add('rect',`x="${x-9}" y="${Math.min(cy,y)}" width="18" height="${Math.max(8,Math.abs(y-cy))}" rx="6" fill="${i%3?'#72d1d2':'#e9b66d'}"`,'pulse');}
     for(let q=0;q<2;q++){let points=Array.from({length:91},(_,i)=>`${220+i*width/90},${cy+R*(q?.3:.55)*Math.sin(i*.135+q*1.8)}`).join(' ');add('polyline',`points="${points}" fill="none" stroke="${q?'#e9b66d':'#a3efed'}" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"`,'swing');}
   }else if(kind==='flow'){
     for(let i=0;i<4;i++){const x=230+i*260;add('rect',`x="${x-95}" y="${cy-R*.36}" width="190" height="${R*.72}" rx="20" fill="#294d63" stroke="#7bbacb" stroke-width="3"`,'rise');markup+=`<text x="${x}" y="${cy+9}" text-anchor="middle" font-size="27" fill="#e9eef2">${['ENTRADA','PROCESSO','ANÁLISE','SAÍDA'][i]}</text>`;if(i<3){add('path',`d="M${x+100},${cy} h60 l-15,-12 m15,12 l-15,12" fill="none" stroke="#e8b66e" stroke-width="6" stroke-linecap="round"`,'swing');}}
   }else if(kind==='radar'){
     for(let i=1;i<=4;i++)add('circle',`cx="${cx}" cy="${cy}" r="${R*i/4}" fill="none" stroke="#86c4cc" stroke-opacity=".5" stroke-width="2"`);
     for(let i=0;i<8;i++){const [x,y]=pt(i*Math.PI/4);add('line',`x1="${cx}" y1="${cy}" x2="${x}" y2="${y}" stroke="#86c4cc" stroke-opacity=".3" stroke-width="2"`);}
     // Ellipse's own pivot is shared by the renderer and Player V3.
     add('ellipse',`cx="${cx}" cy="${cy}" rx="${R}" ry="${R*.12}" fill="#69ccd0" fill-opacity=".35" stroke="#a0edeb" stroke-width="3"`,'orbit');
     for(let i=0;i<6;i++){const [x,y]=pt(i*2.4,R*(.35+(i%3)*.22));add('circle',`cx="${x}" cy="${y}" r="${R*.06}" fill="#f2c275"`,'pulse');}
   }else{
     for(let i=0;i<24;i++){let a=i*2.39996,r=R*1.7*Math.sqrt((i+1)/24),[x,y]=pt(a,r);add('circle',`cx="${x}" cy="${y}" r="${5+i%5*3}" fill="${['#79d3d3','#ebba73','#a7a8ea'][i%3]}" opacity=".84"`,i%3?'pulse':'swing');}
   }
   return {markup,tracks,title:catalog.find(e=>e[0]===kind)[1]};
 }
 g.StudioWorkspaceV38={catalog,motions,motion,object};
})(typeof window!=='undefined'?window:globalThis);
