// Shared analytical timeline and renderer; no second interpreter.
import {readFile,writeFile} from 'node:fs/promises';
import {join} from 'node:path';
import {compile} from '../src/model.mjs';
import {Timeline} from '../src/timeline.mjs';
import {renderSVG,ASSETS} from '../src/render-svg.mjs';
import {soundPlan} from '../src/audio.mjs';
const [source,out,fpsArg,durationArg]=process.argv.slice(2),fps=Number(fpsArg);
if(!source||!out||!Number.isInteger(fps)||fps<12||fps>30)throw Error('source, output, fps 12–30');
const d=compile(await readFile(source,'utf8')),timeline=new Timeline(d),stage=d.spec.stage;
const duration=durationArg?Number(durationArg):stage.duration;
if(!Number.isFinite(duration)||duration<=0||duration>Math.min(120,stage.duration))throw Error('Duração fora do intervalo 0–120 s e da composição');
const frames=Math.ceil(duration*fps),assets={};
for(const [key,path] of Object.entries(ASSETS))assets[key]='data:image/svg+xml;base64,'+(await readFile(new URL('../'+path,import.meta.url))).toString('base64');
await writeFile(join(out,'plan.json'),JSON.stringify({stage,fps,frames,duration:frames/fps,cues:soundPlan(d,timeline).filter(c=>c.start<frames/fps)},null,2));
for(let i=0;i<frames;i++){const frame=timeline.sample(i/fps);await writeFile(join(out,`frame-${String(i).padStart(5,'0')}.svg`),renderSVG(frame,{assetResolver:k=>assets[k]}).svg);}
