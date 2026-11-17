import unittest
from pathlib import Path
from schema import media_objects_dict
from standalone_html import HTML_TEMPLATE


class MediaContractV3134(unittest.TestCase):
    def test_style_survives_normalization(self):
        example={'id':'test_1','label':'Exemplo','kind':'image','file':'photo.png',
                 'start':0,'end':4,'corner_radius':.15,'border_width':3,
                 'shadow_blur':12,'border_color':'#fefefe','shadow_color':'#112233'}
        obj=media_objects_dict([example])[0]
        for name in ['corner_radius','border_width','border_color','shadow_blur','shadow_color']:
            self.assertEqual(obj[name],example[name])

    def test_invalid_colors_are_rejected(self):
        example={'id':'test_1','kind':'image','file':'photo.png','start':0,'end':4,'border_color':'expression(foo)'}
        with self.assertRaises(ValueError):media_objects_dict([example])

    def test_shared_audio_gate_present_in_standalone_template(self):
        self.assertIn('%%RD_MEDIA_GATE%%',HTML_TEMPLATE)
        self.assertIn('RDMediaGate.create(audio)',HTML_TEMPLATE)
        self.assertIn('if(playing||starting)return',HTML_TEMPLATE)
