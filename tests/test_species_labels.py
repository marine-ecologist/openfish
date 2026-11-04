import json
import unittest
import test_training as fixture
from training import TrainingStore
from species_labels import title

class SpeciesLabelTests(unittest.TestCase):
    setUp=fixture.TrainingTests.setUp
    def test_three_parrot_labels_and_no_other_variants(self):
        for tag in ['J','IP','TP']:
            key='sparisoma_viride__'+tag
            self.assertEqual(title(self.store.catalog[key]),'Sparisoma viride ['+tag+']')
        self.assertNotIn('acanthurus_coeruleus__TP',self.store.catalog)
    def test_old_known_phase_migrates_without_separate_active_field(self):
        self.store.data['labels']['1']=dict(track_id=1,status='species',species_id='sparisoma_viride',phase='initial',reviewer='R',note='',approved=[],reviewed_at='2026-11-04')
        self.store.path.write_text(json.dumps(self.store.data))
        reopened=TrainingStore(self.out,self.tracks)
        self.assertEqual(reopened.label(1)['species_id'],'sparisoma_viride__IP')
        self.assertNotIn('phase',reopened.label(1))
    def test_combined_export(self):
        self.store.save(1,'species','sparisoma_viride__TP','R','',[self.store.samples[1][0]['sha256']])
        self.store.save(2,'unidentified',None,'R','',[])
        data=json.loads((self.store.export()/'manifest.json').read_text())
        self.assertEqual(data['samples'][0]['label'],'Sparisoma viride [TP]')
        self.assertEqual(data['samples'][0]['scientific_name'],'Sparisoma viride')
        self.assertNotIn('phase',data['samples'][0])
