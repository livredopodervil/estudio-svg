from __future__ import annotations
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
import xml.etree.ElementTree as ET

ROOT=Path(os.environ.get('RD_V3_ROOT') or Path(__file__).resolve().parents[1])


def adapter():
    spec=importlib.util.spec_from_file_location('m15_scene_animation',ROOT/'scene_animation.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    return m


def node_evaluate(records,animations,progress):
    node='''const v=require(process.argv[1]);const d=JSON.parse(process.argv[2]);console.log(JSON.stringify(v.evaluateRecords(d.records,d.animations,d.progress,{strict:true})))'''
    p=subprocess.run(['node','-e',node,str(ROOT/'web_player/v3/runtime.js'),json.dumps(dict(records=records,animations=animations,progress=progress))],capture_output=True,text=True,check=True)
    return json.loads(p.stdout)


class SingleEngineTests(unittest.TestCase):
    def setUp(self):self.mod=adapter()

    def test_articulation_11_repetitions_same_for_python_and_js(self):
        animations=[dict(alvo='leg',tipo='rotacao',de=-22,ate=22,inicio=0,fim=1,repeticoes=11,yoyo=True,easing='linear')]
        svg='<svg xmlns="http://www.w3.org/2000/svg"><line id="leg" x1="135" y1="67" x2="240" y2="120"/></svg>'
        records=[dict(id='leg',tag='line',attrs=dict(x1='135',y1='67',x2='240',y2='120'),bbox=dict(x=135,y=67,width=105,height=53),transform='',opacity='1')]
        for t in (0,.01,.125,.25,.5,.75,.999,1,.25):
            actual=ET.fromstring(self.mod.animate_svg_fragment(svg,animations,t))[0].get('transform')
            reference=node_evaluate(records,animations,t)[0]['transform']
            self.assertEqual(actual,reference)
            self.assertIn('135 67)',actual)

    def test_explicit_pivot_preferred(self):
        anim=[dict(alvo='path',tipo='rotacao',de=0,ate=90,inicio=0,fim=1)]
        svg='<svg><path id="path" d="M0 0L70 0" data-pivot-x="20" data-pivot-y="50"/></svg>'
        out=self.mod.animate_svg_fragment(svg,anim,.5)
        self.assertIn('20 50)',out)

    def test_missing_bbox_must_fail_not_silently_deviate(self):
        anim=[dict(alvo='path',tipo='rotacao',de=0,ate=90,inicio=0,fim=1)]
        svg='<svg><path id="path" d="M0 0L70 0"/></svg>'
        with self.assertRaisesRegex(RuntimeError,'Pivô indefinido'):
            self.mod.animate_svg_fragment(svg,anim,.5)

    def test_easing_cycles_and_staggered_tracks(self):
        anim=[dict(alvos=['leg','leg2'],tipo='rotacao',de=10,ate=70,inicio=0,fim=.6,intervalo=.2,repeticoes=2,yoyo=True,easing='sine.inOut')]
        svg='<svg><line id="leg" x1="2" y1="8" x2="5" y2="20"/><line id="leg2" x1="10" y1="5" x2="20" y2="12"/></svg>'
        at=ET.fromstring(self.mod.animate_svg_fragment(svg,anim,.25))
        self.assertIn('2 8)',at[0].get('transform'))
        self.assertIn('10 5)',at[1].get('transform'))

    def test_hd_uses_structural_svg_and_shared_runtime(self):
        code=(ROOT/'web/browser-render.mjs').read_text()
        self.assertIn("animation_engine:'v3'",code)
        self.assertIn('v3.animateV3Markup',code)
        self.assertIn('structuralPromise',code)
        m=(ROOT/'web/studio-v3-preview.mjs').read_text()
        self.assertIn('createDOMAnimator',m)
        self.assertNotIn('function pivotsFromPlayer',m)
        player=(ROOT/'web_player/v3/player.js').read_text()
        self.assertIn('createDOMAnimator',player)
        self.assertNotIn('const tracks=new Map();',player)
        self.assertIn('svg.setAttribute(\'width\'',m)
        self.assertIn('renderWidth:p.video.width',code)

if __name__=='__main__':unittest.main()
