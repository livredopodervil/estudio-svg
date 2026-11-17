/* Timing policy for editor batches. No access to DOM or media. */
(function(g){'use strict';
 const valid=n=>Number.isFinite(n)&&n>=.5&&n<=600;
 function plan(scenes,first,last,mode,value){
   if(!Array.isArray(scenes)||!Number.isInteger(first)||!Number.isInteger(last)||first<0||last>=scenes.length||first>last||!['set','floor','scale'].includes(mode))throw Error('Intervalo ou operação inválida.');
   if(!Number.isFinite(value)||value<=0||(mode==='scale'?value>1200:!valid(value)))throw Error('Valor inválido: duração 0,5–600 s; fator positivo.');
   const edits=[];
   for(let i=first;i<=last;i++){
     const scene=scenes[i],before=Number(scene.duracao);
     if(!valid(before))throw Error('Duração inválida na cena '+(i+1));
     const raw=mode==='set'?value:mode==='floor'?Math.max(before,value):before*value;
     if(!valid(raw))throw Error('Resultado fora de 0,5–600 s na cena '+(i+1)+'. Nenhuma cena modificada.');
     const after=mode==='floor'&&raw===before?before:Math.round(raw*1000)/1000;
     if(after!==before)edits.push({scene,before,after});
   }
   return edits;
 }
 function apply(edits){if(edits.some(e=>Number(e.scene.duracao)!==e.before))throw Error('Cena alterada; recalcule.');for(const e of edits)e.scene.duracao=e.after;}
 function undo(edits,scenes){if(edits.some(e=>!scenes.includes(e.scene)||Number(e.scene.duracao)!==e.after))throw Error('Duração ou cena alterada depois da operação; desfazer bloqueado.');for(const e of edits)e.scene.duracao=e.before;}
 g.StudioTimingV37={plan,apply,undo};
})(typeof window!=='undefined'?window:globalThis);
