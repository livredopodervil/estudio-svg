"""M1X regression tests against the real Studio schema."""
import unittest
from schema import normalize

CAM = {'position':[0,1,10],'quaternion':[0,0,0,1],
       'focusDistance':10,'fov':55,'near':0.1,'far':1000}


def project(viewport=None):
    scene={'tipo':'svg','duracao':10,'titulo':'Teste WebGL'}
    if viewport is not None:
        scene['spatialseed_viewport']=viewport
    return {'video':{'width':720,'height':1280,'fps':24,'draw_fps':6},'cenas':[scene]}


class NativeViewportSchemaTests(unittest.TestCase):
    def test_save_open_preserves_native_source_and_camera(self):
        v={'enabled':True,'source':'{"project":"native","objects":[]}',
           'camera_keys':[{'t':0,'camera':CAM},
                          {'t':5,'camera':{**CAM,'position':[1,2,3]}}]}
        a=normalize(project(v));b=normalize(a)
        self.assertEqual(a['cenas'][0]['spatialseed_viewport'],b['cenas'][0]['spatialseed_viewport'])

    def test_toggle_off_does_not_delete_source(self):
        v={'enabled':False,'source':'{"objects":[]}',
           'camera_keys':[{'t':0,'camera':CAM}]}
        self.assertEqual(normalize(project(v))['cenas'][0]['spatialseed_viewport']['source'],v['source'])

    def test_bad_camera_timing_and_source_rejected(self):
        for v in [
            {'enabled':True,'source':'','camera_keys':[{'t':5,'camera':CAM},{'t':2,'camera':CAM}]},
            {'enabled':True,'source':'alert(1)','camera_keys':[]},
            {'enabled':True,'source':'','camera_keys':[{'t':0,'camera':{**CAM,'fov':0}}]},
        ]:
            with self.subTest(v=v),self.assertRaises(ValueError): normalize(project(v))

    def test_non_webgl_project_not_modified(self):
        self.assertNotIn('spatialseed_viewport',normalize(project())['cenas'][0])

if __name__=='__main__': unittest.main()
