import unittest
import test_training as fixture
from fish_phase import normalize_phase
from training import TrainingStore
import json

class FishPhaseTests(unittest.TestCase):
    setUp=fixture.TrainingTests.setUp
    def test_phase_round_trip_and_export(self):
        species='sparisoma_viride'
        self.store.save(1,'species',species,'R','Visible markings',[self.store.samples[1][0]['sha256']],phase='initial')
        self.store.save(2,'unidentified',None,'R','',[])
        reopened=TrainingStore(self.out,self.tracks)
        self.assertEqual(reopened.label(1)['phase'],'initial')
        exported=json.loads((reopened.export()/'manifest.json').read_text())
        self.assertEqual(exported['samples'][0]['phase'],'initial')
        self.assertEqual(exported['tracks'][1]['phase'],'not_applicable')
    def test_invalid_nonparrot_phase_and_unknown_code(self):
        with self.assertRaises(ValueError):normalize_phase('acanthurus_coeruleus',self.store.catalog,'terminal')
        with self.assertRaises(ValueError):normalize_phase('scarus_vetula',self.store.catalog,'female')
        self.assertEqual(normalize_phase('scarus_vetula',self.store.catalog),'unassessed')
    def test_legacy_labels_get_unassessed_without_invented_phase(self):
        self.store.save(1,'species','scarus_vetula','R','',[])
        data=json.loads(self.store.path.read_text());data['labels']['1'].pop('phase');self.store.path.write_text(json.dumps(data))
        self.assertEqual(TrainingStore(self.out,self.tracks).label(1)['phase'],'unassessed')
