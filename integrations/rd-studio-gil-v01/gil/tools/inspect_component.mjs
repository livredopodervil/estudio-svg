import {readFile,writeFile} from 'node:fs/promises';
import {compile} from '../src/model.mjs';
import {Timeline} from '../src/timeline.mjs';
const [input,output]=process.argv.slice(2);
const doc=compile(await readFile(input,'utf8')), t=new Timeline(doc);
t.sample(0);t.sample(doc.spec.stage.duration);
await writeFile(output,JSON.stringify({duration:doc.spec.stage.duration,cues:doc.cues.length,objects:doc.nodes.length}));
