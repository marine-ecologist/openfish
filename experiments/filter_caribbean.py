"""Re-score the unchanged pilot with the full explicit CoReFish regional catalogue.

Keep original probability mass: masking does not renormalize scores or manufacture
confidence. This is a limited regional catalogue, not all Caribbean fish taxa.
"""
import collections
import hashlib
import json
import sys
from pathlib import Path
from run_species_trial import classify, metrics, write_table


def mask_scores(scores, allowed):
    filtered = {k: v for k, v in scores.items() if k in allowed}
    if len(filtered) < 2:
        raise ValueError('At least two allowed model classes are required')
    return filtered


def run(root):
    root = Path(root)
    crosswalk = json.loads((root/'crosswalk.json').read_text())
    allowed = {r['model_name'].lower().replace(' ', '_') for r in crosswalk if r['model_name']}
    rows = json.loads((root/'crop_scores.json').read_text())
    grouped = collections.defaultdict(list)
    for row in rows: grouped[row['track_id']].append(row)
    summary = {}
    for method, threshold, margin in [('softmax', .8, .2), ('cosine', .7, .05)]:
        crops, first, tracks = [], [], []
        for ident, views in sorted(grouped.items()):
            views.sort(key=lambda r: r['view'])
            truth = views[0]['truth'].lower().replace(' ', '_')
            match = next((r['model_name'] for r in crosswalk if r['scientific_name'] == views[0]['truth']), None)
            if match: truth = match.lower().replace(' ', '_')
            info = dict(track_id=ident, truth=truth, covered=views[0]['model_class'] is not None)
            scores = [mask_scores(v[method], allowed) for v in views]
            crops.extend(dict(**info, **classify(s, threshold, margin)) for s in scores)
            first.append(dict(**info, **classify(scores[0], threshold, margin)))
            mean = {k: sum(s[k] for s in scores)/len(scores) for k in sorted(scores[0])}
            tracks.append(dict(**info, **classify(mean, threshold, margin)))
        (root/f'caribbean_{method}_track_predictions.json').write_text(json.dumps(tracks, indent=2)+'\n')
        summary[method] = dict(threshold=threshold, margin=margin, crop=metrics(crops), single_view_track=metrics(first), multi_view_track=metrics(tracks))
        confusion = collections.Counter((r['truth'], r['assigned']) for r in tracks)
        write_table(root/f'caribbean_{method}_confusion.csv', [dict(truth=a, predicted=b, count=n) for (a,b),n in sorted(confusion.items())], ['truth','predicted','count'])
    result = dict(methods=summary, regional_filter=dict(name='Explicit CoReFish Caribbean species catalogue',
        allowed_model_classes=sorted(allowed), count=len(allowed),
        source='https://warplab.github.io/corefish/', crosswalk_sha256=hashlib.sha256((root/'crosswalk.json').read_bytes()).hexdigest(),
        scope='Full explicit CoReFish species crosswalk, including taxa absent from this pilot; not an exhaustive Caribbean checklist.',
        score_policy='Mask only; original softmax probabilities are not renormalized. Original score/margin gates retained.',
        caveat='Post-hoc regional comparison; unchanged observations and reference labels. Not an independent validation.'))
    (root/'caribbean_benchmark_results.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({m:s['multi_view_track'] for m,s in summary.items()}, indent=2))
    print('Allowed model classes:', len(allowed))

if __name__ == '__main__': run(sys.argv[1])
