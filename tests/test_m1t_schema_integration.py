"""Teste opt-in do schema real: preservação da biblioteca no ciclo JSON."""
import copy
import unittest
import schema

class SchemaInstances(unittest.TestCase):
    def test_roundtrip_and_legacy(self):
        original=schema.default_project()
        norm=schema.normalize(original)
        self.assertNotIn('instance_library',norm)
        self.assertNotIn('instances',norm['cenas'][0])
        project=copy.deepcopy(norm)
        project['instance_library']={
            'format':'rd-instance-library-1',
            'definitions':[
                {'id':'photo','kind':'media','media':{
                    'id':'photo','kind':'image','file':'sample.jpg','x':.5,'y':.5,'w':.3,'h':.3,
                    'start':0,'end':5}},
                {'id':'group','kind':'group','children':[
                    {'id':'one','ref':'photo','transform':{'matrix':[1,0,0,1,-.1,0]}},
                    {'id':'two','ref':'photo','transform':{'matrix':[1,0,0,1,.1,0]}}
                ]}
            ]}
        project['cenas'][0]['instances']=[{'id':'r1','ref':'group','start':0,'end':5}]
        saved=schema.normalize(project)
        again=schema.normalize(saved)
        self.assertEqual(saved,again)
        self.assertEqual(len(saved['instance_library']['definitions']),2)
        self.assertEqual(saved['cenas'][0]['instances'][0]['ref'],'group')
    def test_reject_dangling_reference(self):
        project=schema.default_project()
        project['instance_library']={'format':'rd-instance-library-1','definitions':[]}
        project['cenas'][0]['instances']=[{'id':'r','ref':'missing'}]
        with self.assertRaises(ValueError):schema.normalize(project)

if __name__=='__main__':unittest.main()
