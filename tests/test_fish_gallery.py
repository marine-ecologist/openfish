import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from fish_similarity import aggregate, cluster, build_similarity, CropSampler
from fish_gallery import write_gallery


class SimilarityTests(unittest.TestCase):
    def test_aggregation_normalizes_each_view(self):
        np.testing.assert_allclose(aggregate([[10, 0], [0, 1]]), [2**-.5, 2**-.5])
        for vectors in ([[0, 0]], [[float('nan'), 1]], [[1, 0], [-1, 0]]):
            with self.assertRaises(ValueError):
                aggregate(vectors)

    def test_complete_link_does_not_chain(self):
        vectors = {i: [np.cos(a), np.sin(a)] for i, a in enumerate([0, .6, 1.2], 1)}
        groups = cluster(vectors)
        self.assertEqual(sum(map(len, groups)), 3)
        self.assertEqual(len(groups), 2)
        self.assertEqual(cluster({}), [])
        self.assertEqual(cluster({7: [1, 0]}), [[7]])
        self.assertEqual(cluster({3: [1, 0], 1: [1, .01], 2: [-1, 0]}), [[1, 3], [2]])

    def test_partial_failure_and_raw_id_mapping(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder)
            samples = out / 'similarity_samples' / '42'
            samples.mkdir(parents=True)
            (samples / '0.jpg').touch()
            def encode(paths):
                if paths[0].parent == samples:
                    return [[1, 0], [1, .01]]
                raise ValueError('bad image')
            result = build_similarity(out, [{'track_id': 1, 'raw_tracker_id': '42'}, {'track_id': 2}], lambda: encode)
            self.assertEqual(result['groups'], [[1]])
            self.assertEqual(result['missing'], [2])
            self.assertEqual(json.loads((out / 'similarity.json').read_text())['status'], 'ready')

    def test_model_failure_is_nonfatal(self):
        with tempfile.TemporaryDirectory() as folder:
            def fail():
                raise OSError('offline')
            result = build_similarity(folder, [{'track_id': 1}], fail)
            self.assertEqual(result['status'], 'unavailable')
            self.assertEqual(result['missing'], [1])

    def test_sampler_bounded_and_rejects_tiny_crops(self):
        with tempfile.TemporaryDirectory() as folder:
            sampler = CropSampler(folder, 1)
            for frame in range(100):
                sampler.add(5, frame, .9, np.zeros((20, 20, 3), dtype=np.uint8))
            sampler.add(6, 0, 1, np.zeros((4, 4, 3), dtype=np.uint8))
            self.assertEqual(len(list(Path(folder).rglob('*.jpg'))), 4)

    def test_gallery_order_and_fallback(self):
        tracks = [dict(track_id=i, first_s=t, last_s=10, detections=5, best_confidence=.8) for i,t in [(1, 8), (2, 1), (3, 1)]]
        with tempfile.TemporaryDirectory() as folder:
            with patch('fish_gallery.build_similarity', return_value=dict(status='ready', groups=[[1, 2]], message='Appearance only')):
                write_gallery(folder, tracks, dict(total_frames=10, source_fps=1, model='<model>'))
            page = (Path(folder) / 'fish_ID_gallery.html').read_text()
            self.assertLess(page.index('Fish 0002'), page.index('Fish 0003'))
            self.assertLess(page.index('Fish 0003'), page.index('Fish 0001'))
            self.assertIn('data-group="0"', page)
            self.assertIn('&lt;model&gt;', page)
            self.assertIn('value="chronological"', page)
            with patch('fish_gallery.build_similarity', return_value=dict(status='unavailable', groups=[], message='Offline')):
                write_gallery(folder, tracks, dict(total_frames=10, source_fps=1, model='test'))
            self.assertIn('value="similarity" disabled', (Path(folder) / 'fish_ID_gallery.html').read_text())

if __name__ == '__main__':
    unittest.main()
