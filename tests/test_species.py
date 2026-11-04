import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from species import aggregate_scores, build_species, apply_reviews
from fish_gallery import write_gallery


class Classifier:
    labels = ['a', 'b']
    manifest = dict(model_id='fixture-only', revision='test', labels=labels,
                    catalog={'a': {'scientific_name': 'Species A'}, 'b': {'scientific_name': 'Species B'}})
    def __call__(self, path):
        if path.name == 'bad.jpg':
            raise ValueError('unreadable')
        return {'a': .9, 'b': .1}


class SpeciesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.out = Path(self.temp.name)
        self.tracks = [dict(track_id=1, raw_tracker_id=42, first_s=0, last_s=2, detections=3, best_confidence=.9), dict(track_id=2, first_s=1, last_s=3, detections=2, best_confidence=.9)]
        (self.out / 'tracks.csv').write_text('track_id\n1\n2\n')
        folder = self.out / 'similarity_samples' / '42'
        folder.mkdir(parents=True)
        (folder / '0.jpg').write_bytes(b'fixture')
        (folder / 'bad.jpg').write_bytes(b'bad')

    def build(self, **kwargs):
        return build_species(self.out, self.tracks, Classifier(), **kwargs)

    def test_aggregate_and_reject_invalid(self):
        self.assertEqual(aggregate_scores([{'a': .9, 'b': .1}, {'a': .1, 'b': .9}], ['a', 'b']), {'a': .5, 'b': .5})
        for scores in [{'a': float('nan'), 'b': 0}, {'a': 1}, {'a': .3, 'b': .3}]:
            with self.assertRaises(ValueError):
                aggregate_scores([scores], ['a', 'b'])

    def test_mapping_partial_failure_and_unknown(self):
        result = self.build()
        row = result['tracks'][0]
        self.assertEqual(row['species_id'], 'a')
        self.assertEqual(row['status'], 'provisional')
        self.assertEqual(len(row['samples']), 1)
        self.assertEqual(len(row['errors']), 1)
        # Fixture classifier returns scores even for absent files: hashing must reject these.
        self.assertEqual(result['tracks'][1]['reason'], 'no_usable_crops')
        result = self.build(threshold=.95)
        self.assertEqual(result['tracks'][0]['species_id'], 'unidentified')
        self.assertEqual(result['tracks'][0]['candidate_id'], 'a')
        result = self.build(margin=.95)
        self.assertEqual(result['tracks'][0]['species_id'], 'unidentified')

    @patch.dict('os.environ', {}, clear=True)
    def test_no_model_and_reproducible_export(self):
        result = build_species(self.out, self.tracks)
        self.assertTrue(all(r['species_id'] == 'unidentified' for r in result['tracks']))
        original = (self.out / 'species_export.json').read_bytes()
        build_species(self.out, self.tracks)
        self.assertEqual(original, (self.out / 'species_export.json').read_bytes())

    def test_reviews_override_preserve_predictions_and_rerun(self):
        result = self.build()
        payload = dict(dataset_sha256=result['dataset_sha256'], events=[dict(track_id=1, species_id='b', reviewer='Researcher', reviewed_at='2026-11-04T12:00:00-05:00', note='Visible markings')])
        apply_reviews(self.out, payload)
        apply_reviews(self.out, payload)
        self.build()
        exported = json.loads((self.out / 'species_export.json').read_text())
        self.assertEqual(exported['tracks'][0]['species_id'], 'b')
        self.assertEqual(exported['tracks'][0]['model_species_id'], 'a')
        self.assertEqual(len(exported['review_history']['events']), 1)
        payload['events'][0]['species_id'] = 'unidentified'
        apply_reviews(self.out, payload)
        self.assertEqual(json.loads((self.out / 'species_export.json').read_text())['tracks'][0]['species_id'], 'unidentified')
        (self.out / 'tracks.csv').write_text('changed')
        with self.assertRaises(ValueError):
            apply_reviews(self.out, payload)
        with self.assertRaises(ValueError):
            self.build()

    def test_missing_model_and_changed_run(self):
        with patch.dict('os.environ', {'OPENFISHID_SPECIES_MODEL': '/nonexistent/model'}), patch('species.LocalClassifier', side_effect=OSError('missing weights')):
            result = build_species(self.out, self.tracks)
        self.assertEqual(result['tracks'][0]['reason'], 'model_unavailable')
        self.assertIn('missing weights', result['tracks'][0]['errors'][0])
        payload = dict(dataset_sha256=result['dataset_sha256'], events=[dict(track_id=1, species_id='unidentified', reviewer='R', reviewed_at='2026-11-04T12:00:00Z')])
        (self.out / 'run.json').write_text('{"source": "other-video"}')
        with self.assertRaises(ValueError):
            apply_reviews(self.out, payload)

    def test_invalid_review_batch_is_atomic(self):
        result = self.build()
        payload = dict(dataset_sha256=result['dataset_sha256'], events=[dict(track_id=100, species_id='a', reviewer='R', reviewed_at='2026-11-04T12:00:00Z')])
        with self.assertRaises(ValueError):
            apply_reviews(self.out, payload)
        self.assertFalse((self.out / 'species_reviews.json').exists())

    @patch.dict('os.environ', {}, clear=True)
    def test_gallery_review_controls_and_escaping(self):
        with patch('fish_gallery.build_similarity', return_value=dict(status='unavailable', groups=[], message='Offline')):
            write_gallery(self.out, self.tracks, dict(total_frames=10, source_fps=1, model='<model>'))
        page = (self.out / 'fish_ID_gallery.html').read_text()
        self.assertIn('Mark reviewed', page)
        self.assertIn('species_review_import.json', page)
        self.assertIn('&lt;model&gt;', page)
        self.assertIn('model score unavailable', page)


if __name__ == '__main__':
    unittest.main()
