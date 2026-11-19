import test from 'node:test';
import assert from 'node:assert/strict';
import {objectRef, sceneEvent, createSharedSceneBridge} from '../web/studio-shared-scene.mjs';

test('identidade estável por espaço e identificador', () => {
  assert.deepEqual(objectRef('spatialseed', 'nucleo.u235'), {space: 'spatialseed', id: 'nucleo.u235'});
  assert.throws(() => objectRef('webgl2', 'x'));
  assert.throws(() => objectRef('svg', '../segredo'));
});
test('rejeita operação inválida antes de mover qualquer renderer', () => {
  const calls = [];
  const bridge = createSharedSceneBridge({spatialseed: {seek: t => calls.push(t)}});
  assert.throws(() => bridge.at(4, [{kind: 'set', target: objectRef('svg', 'x'), property: 'x', value: 4}]));
  assert.deepEqual(calls, []);
});
test('compartilha exatamente o tempo do Studio e roteia propriedades entre renderers', () => {
  const calls = [];
  const adapter = name => ({
    seek: t => calls.push(`${name}:seek:${t}`),
    set: (id, prop, v) => calls.push(`${name}:set:${id}:${prop}:${v}`),
    event: (id, e) => calls.push(`${name}:event:${id}:${e.type}`),
    renderAt: t => calls.push(`${name}:render:${t}`),
  });
  const bridge = createSharedSceneBridge({spatialseed: adapter('ss'), svg: adapter('svg')});
  const outcome = bridge.at(2.5, [
    {kind: 'set', target: objectRef('spatialseed', 'u235'), property: 'position.x', value: 12},
    {kind: 'set', target: objectRef('svg', 'label'), property: 'opacity', value: 0.8},
    {kind: 'event', target: objectRef('svg', 'label'), event: {
      type: 'fissao', source: objectRef('spatialseed', 'u235'), payload: {n: 2}
    }},
  ]);
  assert.deepEqual(outcome, {time: 2.5, operations: 3, spaces: ['spatialseed', 'svg']});
  assert.deepEqual(calls, [
    'ss:seek:2.5', 'svg:seek:2.5',
    'ss:set:u235:position.x:12', 'svg:set:label:opacity:0.8',
    'svg:event:label:fissao', 'ss:render:2.5', 'svg:render:2.5',
  ]);
});
test('eventos são envelopes tipados e limitados', () => {
  assert.throws(() => sceneEvent({type: '!!!', source: objectRef('svg', 'a')}));
  assert.throws(() => sceneEvent({type: 'a', source: objectRef('svg', 'a'), payload: 'x'.repeat(70000)}));
});
