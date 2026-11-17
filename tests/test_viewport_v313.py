import unittest
from schema import media_objects_dict
class ViewportTests(unittest.TestCase):
 def test_affine_fields_are_optional_and_persist(self):
  base={'id':'obj_1','kind':'image','file':'test.png','start':0,'end':4}
  self.assertNotIn('shear',media_objects_dict([base])[0])
  pose={'shear':.6,'pivot_x':.2,'pivot_y':-.4}
  self.assertEqual({k:media_objects_dict([{**base,**pose}])[0][k] for k in pose},pose)
