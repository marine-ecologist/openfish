import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('trial',Path(__file__).resolve().parents[1]/'experiments/run_species_trial.py')
trial = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trial)

class TrialMetricsTests(unittest.TestCase):
    def test_rejection_and_confident_errors_have_correct_denominators(self):
        rows=[dict(truth='a',covered=True,**trial.classify({'a':.95,'b':.05})),
              dict(truth='b',covered=True,**trial.classify({'a':.99,'b':.01})),
              dict(truth='c',covered=False,**trial.classify({'a':.6,'b':.4})),
              dict(truth='c',covered=False,**trial.classify({'a':.99,'b':.01}))]
        result=trial.metrics(rows)
        self.assertEqual(result['top1_covered'],.5)
        self.assertEqual(result['accepted_precision'],1/3)
        self.assertEqual(result['absent_rejection_rate'],.5)
        self.assertEqual(result['confidently_wrong'],2)
        self.assertEqual(result['unidentified_rate'],.25)

    def test_empty_metrics_are_not_reported_as_accuracy(self):
        result=trial.metrics([])
        self.assertIsNone(result['top1_covered'])
        self.assertIsNone(result['accepted_precision'])

    def test_margin_rejects_tied_predictions(self):
        self.assertEqual(trial.classify({'a':.5,'b':.5})['assigned'],'unidentified')

if __name__=='__main__':unittest.main()
