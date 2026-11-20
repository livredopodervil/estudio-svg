// RD Studio M2.3 - cancellable deadline for offline scene preparation.
export async function withDeadline(label,operation,{signal,ms=20000}={}){
 if(typeof label!=='string'||typeof operation!=='function'||!Number.isFinite(ms)||ms<10)throw Error('Prazo de preparação inválido');
 if(signal?.aborted)throw Error('Preparação cancelada.');
 const controller=new AbortController();
 let timer,handler;
 const timeout=new Promise((_,reject)=>{timer=setTimeout(()=>{controller.abort();reject(Error(`${label}: excedeu ${ms/1000} s. Verifique /api/preview, cenas SVG e mídia.`));},ms);});
 const cancelled=new Promise((_,reject)=>{
  if(signal){handler=()=>{controller.abort();reject(Error('Preparação cancelada.'));};signal.addEventListener('abort',handler,{once:true});}
 });
 try{return await Promise.race([Promise.resolve().then(()=>operation(controller.signal)),timeout,cancelled]);}
 finally{clearTimeout(timer);if(signal&&handler)signal.removeEventListener('abort',handler);}
}
