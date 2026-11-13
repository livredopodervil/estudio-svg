"""Regressões para V3 Alpha 4: timeline determinística e JSON de LLM."""
import math
import unittest

from timeline_easing import EASINGS, ease, progress
from schema import animation_dict, normalize
from scene_animation import animate_svg_fragment, effects
from spatial_scene import normalize_spatial, pose, camera_pose, default_spatial


class TimelineAlpha4(unittest.TestCase):
    def test_easings_exact_boundaries(self):
        for name in EASINGS:
            with self.subTest(name=name):
                self.assertAlmostEqual(ease(0, name), 0)
                self.assertAlmostEqual(ease(1, name), 1)
                self.assertTrue(math.isfinite(ease(.37,name)))

    def test_repeated_yoyo_and_final_frame(self):
        a={'inicio':0,'fim':1,'easing':'linear','repeticoes':1,'yoyo':True}
        self.assertAlmostEqual(progress(a,.0),0)
        self.assertAlmostEqual(progress(a,.25),.5)
        self.assertAlmostEqual(progress(a,.5),1)
        self.assertAlmostEqual(progress(a,.75),.5)
        self.assertAlmostEqual(progress(a,1),0)

    def test_repeat_no_yoyo_final(self):
        a={'inicio':.2,'fim':.8,'easing':'linear','repeticoes':2,'yoyo':False}
        self.assertAlmostEqual(progress(a,.4),0)
        self.assertAlmostEqual(progress(a,.8),1)
        self.assertAlmostEqual(progress(a,1),1)

    def test_stagger_targets_expands_with_offsets(self):
        a=animation_dict([{'alvos':['a','b','c'],'tipo':'fade','inicio':0,'fim':.2,
                           'intervalo':.15,'de':0,'ate':1,'easing':'expo.out'}])
        self.assertEqual([x['alvo'] for x in a],['a','b','c'])
        self.assertEqual([x['inicio'] for x in a],[0,.15,.3])
        self.assertEqual([round(x['fim'],5) for x in a],[.2,.35,.5])

    def test_invalid_inputs_are_bounded(self):
        a=animation_dict([{'alvo':'__titulo__','tipo':'escala','repeticoes':999,'yoyo':True,'easing':'evil','inicio':0,'fim':1}])
        self.assertEqual(a[0]['easing'],'suave')
        self.assertEqual(a[0]['repeticoes'],20)
        self.assertTrue(a[0]['yoyo'])

    def test_svg_effects_with_yoyo_differ_by_time(self):
        a=animation_dict([{'alvo':'dot','tipo':'translacao','inicio':0,'fim':1,
                           'de_x':0,'ate_x':200,'repeticoes':1,'yoyo':True,'easing':'linear'}])
        s='<svg xmlns="http://www.w3.org/2000/svg"><circle id="dot" cx="40" cy="40" r="12"/></svg>'
        at_mid=animate_svg_fragment(s,a,.5)
        at_end=animate_svg_fragment(s,a,1)
        self.assertIn('translate(200.0000 0.0000)',at_mid)
        self.assertIn('translate(0.0000 0.0000)',at_end)

    def test_spatial_scale_yoyo(self):
        spatial=normalize_spatial({'objetos':[{'id':'s','tipo':'esfera'}],
            'animacoes':[{'alvo':'s','propriedade':'escala','inicio':0,'fim':1,
                          'de':1,'ate':2,'repeticoes':1,'yoyo':True,'easing':'linear'}]})
        obj=spatial['objetos'][0]
        self.assertAlmostEqual(pose(obj,spatial['animacoes'],.5)[2],2)
        self.assertAlmostEqual(pose(obj,spatial['animacoes'],1)[2],1)

    def test_camera_uses_same_ease(self):
        spatial=normalize_spatial({'objetos':[], 'camera':{'azimute':0},
            'animacoes':[{'alvo':'__camera__','propriedade':'azimute','inicio':0,'fim':1,
                          'de':0,'ate':180,'repeticoes':1,'yoyo':True,'easing':'linear'}]})
        self.assertAlmostEqual(camera_pose(spatial['camera'],spatial['animacoes'],.5)['azimute'],180)
        self.assertAlmostEqual(camera_pose(spatial['camera'],spatial['animacoes'],1)['azimute'],0)

    def test_preserve_old_animation_contract(self):
        proj=normalize({'titulo':'antigo','video':{'width':720,'height':1280},'cenas':[
            {'tipo':'svg','duracao':3,'titulo':'A','animacoes':[{'alvo':'obj','tipo':'fade','inicio':0,'fim':1,'de':0,'ate':1}]}]})
        self.assertEqual(proj['cenas'][0]['animacoes'][0]['easing'],'suave')
        self.assertEqual(proj['cenas'][0]['animacoes'][0]['repeticoes'],0)
        self.assertEqual(proj['versao'],'3.0.0-alpha.4')


if __name__=='__main__':unittest.main()
