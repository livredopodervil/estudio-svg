import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {geometry,dragPose} from '../web/viewport-affine.mjs';
const editor=readFileSync(new URL('../web/scene-object-editor.mjs',import.meta.url),'utf8');
const gizmo=readFileSync(new URL('../web/viewport-gizmo.mjs',import.meta.url),'utf8');
const styles=readFileSync(new URL('../web/style.css',import.meta.url),'utf8');
const capture=readFileSync(new URL('../web/captura.js',import.meta.url),'utf8');
test('single visual transform mode with layer-order and property actions',()=>{
 assert.match(editor,/\['select','⤧','Transformar:/);
 assert.match(editor,/\['raise','↑'/);
 assert.match(editor,/\['lower','↓'/);
 assert.match(editor,/document\.body\.append\(dock\)/);
 assert.match(editor,/visualViewport/);
 assert.match(styles,/\.rdViewportToolDock\{position:fixed/);
 assert.match(gizmo,/tool='select'/);
 assert.match(gizmo,/begin\(e,'move'\)/);
});
test('corner scale, rotation, skew and pivot are independent handles',()=>{
 const obj={x:.5,y:.5,w:.4,h:.4,rotation:0,shear:0,pivot_x:0,pivot_y:0};
 const pose={...obj,rz:0};const g=geometry(pose,400,260);
 const from=g.at(1,1);
 assert(dragPose(obj,pose,400,260,'1,1',from,{x:from.x+25,y:from.y+25}).w>obj.w);
 assert.notEqual(dragPose(obj,pose,400,260,'rotate',{x:250,y:100},{x:150,y:100}).rotation,0);
 assert.notEqual(dragPose(obj,pose,400,260,'shear',{x:150,y:100},{x:180,y:100}).shear,0);
 assert.notEqual(dragPose(obj,pose,400,260,'pivot',{x:0,y:0},{x:12,y:10}).pivot_x,0);
});
test('presentation delegates native layers to the same editor compositor',()=>{
 assert.match(capture,/import\('\/gil-native\.mjs'\)/);
 assert.match(capture,/import\('\/scene-objects\.mjs'\)/);
 assert.match(capture,/gil\.updateLayer/);
 assert.match(capture,/objects\.syncObjects/);
});
