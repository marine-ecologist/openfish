import json
import shutil
import tempfile
import unittest
from pathlib import Path
from PIL import Image
from project_io import export_project, import_project, result_folder, source_video
from species import dataset_identity
from training import TrainingStore

class ProjectTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.video=self.root/'camera.mp4';self.video.write_bytes(b'original video fixture')
        self.run=self.root/'run';self.run.mkdir()
        (self.run/'run.json').write_text(json.dumps(dict(source=str(self.video))))
        (self.run/'summary.json').write_text(json.dumps(dict(source=str(self.video))))
        (self.run/'tracks.csv').write_text('track_id\n1\n');(self.run/'detections.csv').write_text('frame,track_id\n0,1\n')
        (self.run/'fishcount_tracked.mp4').write_bytes(b'playback fixture')
        (self.run/'crops').mkdir();Image.new('RGB',(50,50),'blue').save(self.run/'crops/fish_0001.jpg')
        self.store=TrainingStore(self.run,[dict(track_id=1)]);species=next(iter(self.store.catalog))
        self.store.save(1,'species',species,'Reviewer','Verified',[self.store.samples[1][0]['sha256']])
        (self.run/'training_drafts.json').write_text(json.dumps(dict(dataset_sha256=self.store.fingerprint,drafts={})))
    def test_move_round_trip_and_reexport_after_edits(self):
        self.store.save(1,'species','sparisoma_viride','Reviewer','Phase checked',[self.store.samples[1][0]['sha256']],phase='terminal')
        fingerprint=dataset_identity(self.run);package=export_project(self.run,self.root/'package')
        self.video.unlink();shutil.rmtree(self.run)
        (package/'.DS_Store').write_bytes(b'Finder metadata')
        imported=import_project(package,self.root/'other-computer/projects');results=result_folder(imported)
        self.assertEqual(dataset_identity(results),fingerprint)
        self.assertEqual(source_video(results),imported/'video/original.mp4')
        self.assertEqual(source_video(results).read_bytes(),b'original video fixture')
        store=TrainingStore(results,[dict(track_id=1)]);self.assertEqual(store.label(1)['phase'],'terminal');self.assertTrue(store.complete);self.assertTrue(store.export().exists())
        store.save(1,'unidentified',None,'Second reviewer','Uncertain',[])
        # Edited local project is exported afresh, with updated checksums.
        newer=export_project(results,self.root/'new-package')
        another=import_project(newer,self.root/'third-computer/projects')
        self.assertEqual(TrainingStore(result_folder(another),[dict(track_id=1)]).label(1)['status'],'unidentified')
    def test_tamper_is_rejected_without_partial_import(self):
        package=export_project(self.run,self.root/'package');(package/'results/tracks.csv').write_text('changed')
        with self.assertRaises(ValueError):import_project(package,self.root/'library')
        self.assertFalse((self.root/'library').exists())
    def test_traversal_and_symlinks_rejected(self):
        package=export_project(self.run,self.root/'package');manifest=json.loads((package/'project.json').read_text());manifest['source_video']='../camera.mp4';(package/'project.json').write_text(json.dumps(manifest))
        with self.assertRaises(ValueError):import_project(package,self.root/'library')
        manifest['source_video']='video/original.mp4';(package/'project.json').write_text(json.dumps(manifest));(package/'link').symlink_to(self.video)
        with self.assertRaises(ValueError):import_project(package,self.root/'library')
    def test_missing_original_and_existing_destination(self):
        with self.assertRaises(ValueError):export_project(self.run,self.run)
        self.video.unlink()
        with self.assertRaises(ValueError):export_project(self.run,self.root/'package')
        self.assertFalse((self.root/'package').exists())

if __name__=='__main__':unittest.main()
