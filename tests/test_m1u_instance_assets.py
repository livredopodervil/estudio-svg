import tempfile,unittest,zipfile,json,io,sys
from pathlib import Path
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from studio_instance_assets import restore_instance_media
class Tests(unittest.TestCase):
    def test_instance_only_images_restored_and_existing_not_replaced(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);m=root/'midia';m.mkdir();a=root/'bundle.zip'
            im=Image.new('RGB',(12,9),'red');b=io.BytesIO();im.save(b,format='JPEG')
            obj={'instance_library':{'definitions':[{'id':'a','kind':'media','media':{'kind':'image','file':'a.jpg'}}]}}
            with zipfile.ZipFile(a,'w') as z:
                z.writestr('projetos/p.json',json.dumps(obj));z.writestr('midia/a.jpg',b.getvalue())
            self.assertEqual(restore_instance_media(a,m),['a.jpg'])
            self.assertEqual((m/'a.jpg').read_bytes(),b.getvalue())
            self.assertEqual(restore_instance_media(a,m),[])
    def test_reject_path_traversal(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d);m=r/'midia';m.mkdir();a=r/'t.zip'
            obj={'instance_library':{'definitions':[{'kind':'media','media':{'kind':'image','file':'../../evil.jpg'}}]}}
            with zipfile.ZipFile(a,'w') as z:z.writestr('projetos/p.json',json.dumps(obj))
            with self.assertRaises(ValueError):restore_instance_media(a,m)
if __name__=='__main__':unittest.main()
