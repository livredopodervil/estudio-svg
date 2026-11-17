/* Document snapshots for studio editing. Project JSON is never sent anywhere by this module. */
(function(root){'use strict';
 class DocumentHistory {
  constructor(limit=64,maxBytes=16*1024*1024){this.limit=limit;this.maxBytes=maxBytes;this.clear();}
  clear(){this.owner=null;this.current='';this.past=[];this.future=[];this.lastKey='';this.lastTime=0;}
  reset(owner){this.clear();this.owner=owner;this.current=JSON.stringify(owner);}
  record(owner,key=''){
   if(this.owner!==owner){this.reset(owner);return false;}
   const next=JSON.stringify(owner);if(next===this.current)return false;
   const now=Date.now(),merge=key&&this.lastKey===key&&now-this.lastTime<700&&this.past.length>0;
   if(!merge)this.past.push(this.current);
   while(this.past.length>this.limit||this.past.reduce((sum,s)=>sum+s.length,0)>this.maxBytes)this.past.shift();
   this.future.length=0;this.current=next;this.lastKey=key;this.lastTime=now;return true;
  }
  travel(owner,backwards){
   if(owner!==this.owner)return false;
   // A change in progress not yet signalled by dirtyNow is not silently discarded.
   if(JSON.stringify(owner)!==this.current)return false;
   const source=backwards?this.past:this.future,destination=backwards?this.future:this.past;
   if(!source.length)return false;destination.push(this.current);this.current=source.pop();
   const restored=JSON.parse(this.current);
   for(const key of Object.keys(owner))delete owner[key];
   Object.assign(owner,restored);this.lastKey='';return true;
  }
  undo(owner){return this.travel(owner,true);}
  redo(owner){return this.travel(owner,false);}
  get canUndo(){return this.past.length>0;}
  get canRedo(){return this.future.length>0;}
 }
 root.StudioDocumentHistory=DocumentHistory;
})(typeof window!=='undefined'?window:globalThis);
