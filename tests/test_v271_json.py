"""Read-only validation endpoint for editable project/scene JSON."""
import json
import threading
import unittest
import urllib.error
import urllib.request

from app import Handler, ThreadingHTTPServer, PROJECTS


class JSONValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = 'http://127.0.0.1:' + str(cls.server.server_address[1]) + '/api/project/validate'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def send(self, data):
        req = urllib.request.Request(
            self.url, method='POST', data=json.dumps({'project': data}).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
        )
        return urllib.request.urlopen(req)

    def test_validates_without_writing_project(self):
        name = 'unit_v271_validation_should_not_exist'
        path = PROJECTS / (name + '.json')
        self.assertFalse(path.exists(), 'Teste exige que o identificador esteja livre')
        with self.send({'titulo': 'Teste', 'cenas': [{'tipo': 'svg', 'svg': '<rect x="10" y="20" width="80" height="60"/>'}]}) as r:
            output = json.load(r)
        self.assertTrue(output['ok'])
        self.assertEqual(output['project']['cenas'][0]['tipo'], 'svg')
        self.assertFalse(path.exists(), 'Validar nunca deve salvar em disco')

    def test_rejects_invalid_project(self):
        with self.assertRaises(urllib.error.HTTPError) as cm:
            self.send({'titulo': 'Invalido', 'cenas': []})
        self.assertEqual(cm.exception.code, 400)
        cm.exception.close()


if __name__ == '__main__':
    unittest.main()
