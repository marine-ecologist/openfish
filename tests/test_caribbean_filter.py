import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'experiments'))
from filter_caribbean import mask_scores
from run_species_trial import classify

class CaribbeanFilterTests(unittest.TestCase):
    def test_excludes_pacific_without_manufacturing_confidence(self):
        original = {'sebastes_melanops': .95, 'acanthurus_coeruleus': .04, 'abudefduf_saxatilis': .01}
        filtered = mask_scores(original, {'acanthurus_coeruleus', 'abudefduf_saxatilis'})
        self.assertNotIn('sebastes_melanops', filtered)
        self.assertAlmostEqual(sum(filtered.values()), .05)
        self.assertEqual(classify(filtered)['assigned'], 'unidentified')
        self.assertEqual(original['sebastes_melanops'], .95)

    def test_keeps_valid_caribbean_high_score(self):
        filtered = mask_scores({'a': .9, 'b': .05, 'pacific': .05}, {'a', 'b'})
        self.assertEqual(classify(filtered)['assigned'], 'a')

if __name__=='__main__':unittest.main()
