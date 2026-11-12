#!/usr/bin/env python3
"""Testes sem rede do adaptador do SVG-Edit (módulo externo não incluído)."""
import os, sys, tempfile, unittest, threading, urllib.request, urllib.error, json, base64, io
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from svg_graphic import clean_svg,render_fragment
from app import Handler, ThreadingHTTPServer, PROJECTS

class SvgGraphTests(unittest.TestCase):
 def test_layers_gradient_safety(self):
  with tempfile.TemporaryDirectory() as d:
   svg='''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 300">
    <defs><linearGradient id="a"><stop stop-color="#ff8899"/></linearGradient></defs>
    <g class="layer" id="grupo"><title>Gráfico</title>
     <circle cx="100" cy="100" r="80" fill="url(#a)" onclick="alert(1)"/>
     <script>alert(1)</script><image href="https://bad.invalid/a.png"/>
    </g></svg>'''
   s=clean_svg(svg,d)
   self.assertIn('class="layer"',s)
   self.assertIn('url(#a)',s)
   self.assertNotIn('onclick',s)
   self.assertNotIn('script',s)
   self.assertNotIn('https:',s)
 def test_asset_img(self):
  with tempfile.TemporaryDirectory() as d:
   im=Image.new('RGBA',(8,8),(25,155,80,140));o=io.BytesIO();im.save(o,'PNG')
   img='data:image/png;base64,'+base64.b64encode(o.getvalue()).decode()
   svg=f'<svg xmlns="http://www.w3.org/2000/svg"><g class="layer"><image href="{img}"/></g></svg>'
   s=clean_svg(svg,d);self.assertIn('asset:',s)
   self.assertEqual(len(list(Path(d).glob('*'))),1)
   r=render_fragment(s,d);self.assertIn('data:image/png;base64,',r)
 def test_entity_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(ValueError):clean_svg('<!DOCTYPE svg [<!ENTITY x SYSTEM "file:///etc/passwd">]><svg>&x;</svg>',d)

class HttpTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
  cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
  cls.base='http://127.0.0.1:'+str(cls.server.server_address[1])
  cls.filename='unit_svg_v25';cls.path=PROJECTS/(cls.filename+'.json')
  cls.path.write_text(json.dumps({'titulo':'Test','cenas':[{'tipo':'svg','duracao':3,'svg':'<circle cx="50" cy="50" r="25"/>'}]}))
 @classmethod
 def tearDownClass(cls):
  cls.server.shutdown();cls.server.server_close()
  cls.path.unlink(missing_ok=True)
  cls.path.with_suffix('.vector-backup.json').unlink(missing_ok=True)
 def test_html_routes(self):
  for route in ['/vetor','/vetor.js','/vetor.css']:
   with urllib.request.urlopen(self.base+route) as r:self.assertEqual(r.status,200)
 def test_read_write_conflict(self):
  params=f'?name={self.filename}&scene=1';base=self.base+'/api/svg/document'
  orig=json.load(urllib.request.urlopen(base+params))
  request=urllib.request.Request(base,data=json.dumps({'name':self.filename,'scene':1,'revision':orig['revision'],'svg':orig['svg'].replace('r="25"','r="26"')}).encode(),method='POST',headers={'Content-Type':'application/json'})
  with urllib.request.urlopen(request) as r:self.assertEqual(r.status,200)
  with self.assertRaises(urllib.error.HTTPError) as err:urllib.request.urlopen(request)
  self.assertEqual(err.exception.code,400)

if __name__=='__main__':unittest.main(verbosity=2)
