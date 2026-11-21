#!/usr/bin/env node
// RD_V3_ANIMATION_CANONICAL_15: stdin JSONL -> V3 evaluator -> stdout JSONL.
'use strict';
const readline=require('node:readline');
const runtime=require('./runtime.js');
const rl=readline.createInterface({input:process.stdin,crlfDelay:Infinity});
rl.on('line',line=>{
 try{
  const req=JSON.parse(line);
  let result;
  if(req.op==='evaluate')result=runtime.evaluateRecords(req.records||[],req.animations||[],req.progress||0,{strict:true});
  else if(req.op==='ease')result=runtime.ease(req.progress,req.mode);
  else if(req.op==='progress')result=runtime.progress(req.animation,req.progress);
  else throw Error('Operação inválida');
  process.stdout.write(JSON.stringify({ok:true,result})+'\n');
 }catch(err){process.stdout.write(JSON.stringify({ok:false,error:String(err.message||err)})+'\n');}
});
