import test from 'node:test';
import assert from 'node:assert/strict';
import {parseSubtitleText,subtitleState,subtitleSVG} from '../web/subtitle-frame.mjs';
const scene={duracao:9,audio:{voice_text:'Olá mundo!',voice_delay:.12},legendas:{enabled:true,mode:'karaoke',effect:'none',max_words:5,cues:[{start:.12,end:.43,text:'Olá'},{start:.71,end:1.23,text:'mundo!'}]}};
test('SRT gera tempos por palavra e suporta pausas de fala',()=>{
 const srt='1\n00:00:00,120 --> 00:00:00,430\nOlá\n\n2\n00:00:00,710 --> 00:00:01,230\nmundo!';
 assert.deepEqual(parseSubtitleText(srt),scene.legendas.cues);
 assert.equal(subtitleState(scene,.2,9).words[0],'Olá');
 assert.ok(subtitleSVG(scene,.55,9,960,540).includes('Olá'));
 assert.equal(subtitleState(scene,3,9),null);
});
test('VTT e JSON são aceitos, dados externos não executam scripts',()=>{
 const vtt='WEBVTT\n\n00:00:00.300 --> 00:00:01.000\nA &amp; B';
 assert.equal(parseSubtitleText(vtt)[0].start,.3);
 const data=parseSubtitleText(JSON.stringify([{start:0,end:1,text:'<script>alert(1)</script>'}]));
 const copy={...scene,legendas:{...scene.legendas,cues:data}};
 assert.doesNotMatch(subtitleSVG(copy,.3,9,960,540),/<script>/);
 assert.throws(()=>parseSubtitleText('não é legenda'));
});
