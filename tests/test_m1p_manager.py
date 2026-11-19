import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from studio_project_manager_m1p import list_projects, project_path, manage, trash_list, archive

class ProjectManagerTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        (self.root/'a.json').write_text('{"titulo":"A"}')
        (self.root/'b.json').write_text('{"titulo":"B"}')
    def tearDown(self):self.tmp.cleanup()
    def test_move_rename_restores_json_identical(self):
        old=(self.root/'a.json').read_bytes()
        manage(self.root,'mkdir',folder='Ensino_ECG')
        manage(self.root,'move','a',folder='Ensino_ECG')
        self.assertEqual(project_path(self.root,'a'),self.root/'.pastas/Ensino_ECG/a.json')
        self.assertEqual(project_path(self.root,'a').read_bytes(),old)
        manage(self.root,'rename','a',new_name='ecg_basico')
        self.assertEqual(project_path(self.root,'ecg_basico').read_bytes(),old)
        self.assertEqual(list_projects(self.root)['folders']['ecg_basico'],'Ensino_ECG')
        with self.assertRaises(ValueError):manage(self.root,'rename','ecg_basico',new_name='b')
        self.assertEqual(project_path(self.root,'ecg_basico').read_bytes(),old)
    def test_trash_and_restore_preserve_and_do_not_touch_other_projects(self):
        original=(self.root/'a.json').read_bytes()
        action=manage(self.root,'trash','a')
        self.assertFalse((self.root/'a.json').exists())
        self.assertEqual(len(trash_list(self.root)),1)
        manage(self.root,'restore',token=action['token'])
        self.assertEqual((self.root/'a.json').read_bytes(),original)
        self.assertTrue((self.root/'b.json').exists())
    def test_reject_paths_and_symlinks(self):
        for folder in ('../../other','/tmp','hello world','.hidden','a/b'):
            with self.assertRaises(ValueError):manage(self.root,'mkdir',folder=folder)
        (self.root/'evil.json').symlink_to(self.root/'a.json')
        with self.assertRaises(ValueError):project_path(self.root,'evil')
    def test_archived_folder_project_is_recoverable(self):
        original=(self.root/'a.json').read_bytes()
        manage(self.root,'move','a',folder='Aula')
        archive(self.root,'a')
        self.assertFalse(project_path(self.root,'a').exists())
        archive(self.root,'a',restore=True)
        self.assertEqual(project_path(self.root,'a').read_bytes(),original)
    def test_last_project_not_deleted(self):
        manage(self.root,'trash','a')
        with self.assertRaises(ValueError):manage(self.root,'trash','b')

if __name__=='__main__':unittest.main()
