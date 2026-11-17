/* RD Studio — shared HTMLMediaElement start/stop coordination.
   Works as a standalone inline script and in each web player. No dependencies. */
(function(global){
  'use strict';
  function create(media){
    if(!media || typeof media.play !== 'function' || typeof media.pause !== 'function')throw new TypeError('HTMLMediaElement necessário');
    let generation=0, wanted=false, pending=null;
    function stop(){wanted=false;++generation;media.pause();pending=null;}
    function start(){
      if(wanted && pending)return pending;
      if(wanted && !media.paused)return Promise.resolve(true);
      wanted=true;const ticket=++generation;
      let promise;
      try{promise=Promise.resolve(media.play());}catch(error){promise=Promise.reject(error);}
      const result=promise.then(()=>ticket===generation&&wanted).catch(error=>{
        if(ticket!==generation||!wanted)return false; // intentionally cancelled
        // AbortError from an external pause/load is a real interruption unless cancelled.
        throw error;
      });
      pending=result;
      void result.finally(()=>{if(ticket===generation)pending=null;}).catch(()=>{});
      return result;
    }
    return Object.freeze({start,stop,get wanted(){return wanted;},get pending(){return !!pending;}});
  }
  global.RDMediaGate=Object.freeze({create});
})(typeof window!=='undefined'?window:globalThis);
