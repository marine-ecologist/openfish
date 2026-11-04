import csv
import json
import tempfile
import unittest
from pathlib import Path
from PIL import Image
from training import TrainingStore

class TrainingTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.out=Path(self.temp.name)
        (self.out/'tracks.csv').write_text('track_id,raw_tracker_id\n1,42\n2,43\n')
        (self.out/'run.json').write_text(json.dumps(dict(source='/survey/video.mp4')))
        (self.out/'crops').mkdir();Image.new('RGB',(50,40),'red').save(self.out/'crops/fish_0001.jpg');Image.new('RGB',(40,40),'blue').save(self.out/'crops/fish_0002.jpg')
        self.tracks=[dict(track_id=1,raw_tracker_id=42),dict(track_id=2,raw_tracker_id=43)]
        self.store=TrainingStore(self.out,self.tracks)
    def test_save_reopen_gate_and_deterministic_export(self):
        with self.assertRaises(ValueError):self.store.export()
        key=next(iter(self.store.catalog));approved=[self.store.samples[1][0]['sha256']]
        self.store.save(1,'species',key,'Reviewer','Checked',approved)
        self.store.save(2,'unidentified',None,'Reviewer','Unclear',[])
        reopened=TrainingStore(self.out,self.tracks);self.assertTrue(reopened.complete)
        destination=reopened.export();self.assertEqual(destination,reopened.export())
        manifest=json.loads((destination/'manifest.json').read_text());self.assertEqual(manifest['training_images'],1)
        self.assertTrue((destination/manifest['samples'][0]['image']).exists())
        with (destination/'tracks.csv').open() as stream:self.assertEqual(len(list(csv.DictReader(stream))),2)
    def test_modified_crop_and_track_table_are_rejected(self):
        key=next(iter(self.store.catalog));self.store.save(1,'species',key,'R','',[self.store.samples[1][0]['sha256']]);self.store.save(2,'excluded',None,'R','',[])
        Image.new('RGB',(50,40),'green').save(self.out/'crops/fish_0001.jpg')
        with self.assertRaises(ValueError):self.store.export()
        (self.out/'tracks.csv').write_text('changed')
        with self.assertRaises(ValueError):TrainingStore(self.out,self.tracks)
    def test_species_requires_reviewer_and_approved_crop(self):
        key=next(iter(self.store.catalog))
        with self.assertRaises(ValueError):self.store.save(1,'species',key,'R','',[])
        with self.assertRaises(ValueError):self.store.save(1,'unidentified',None,'','',[])
        self.assertFalse(self.store.path.exists())
