"""Render inspectable pilot predictions with expert reference labels and track views."""
import base64
import collections
import html
import json
import sys
from pathlib import Path

root=Path(sys.argv[1]);results=json.loads((root/'benchmark_results.json').read_text())
predictions=json.loads((root/'softmax_track_predictions.json').read_text())
cosine={p['track_id']:p for p in json.loads((root/'cosine_track_predictions.json').read_text())}
crops=collections.defaultdict(list)
for row in json.loads((root/'crop_scores.json').read_text()):crops[row['track_id']].append(row)
name=lambda s:html.escape(s.replace('_',' '))
page='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>CoReFish species pilot</title><style>
body{font:16px system-ui;background:#eef5f4;color:#143132;margin:32px}main{max-width:1200px;margin:auto}p{line-height:1.6}article{background:white;padding:20px;border-radius:12px;margin:20px 0}.views{display:flex;gap:12px;flex-wrap:wrap}.view{width:30%;min-width:200px}img{width:100%;height:180px;object-fit:contain;background:#102a2b}table{border-collapse:collapse}td,th{padding:10px;border:1px solid #aac4c0;text-align:left}.wrong{color:#972c27}.right{color:#166148}</style></head><body><main><h1>CoReFish species pilot</h1>
<p><a href="fish_ID_gallery.html">Review your footage</a> · <a href="benchmark_results.json">Full metrics and provenance</a></p>
<p>61 expert-labelled tracks · 183 crops · 33 species. Fishial covers 24 of these species (45 tracks); nine species (16 tracks) are outside its catalogue. No fine-tuning. First/middle/last eligible views; at most two tracks per species. Generic labels excluded.</p>
<p>Exploratory pilot with unknown training overlap. These small, correlated samples do not establish general accuracy. Scores are uncalibrated. Appearance groups are not used for identification.</p><table><tr><th>Method</th><th>Top-1, covered tracks</th><th>Top-3, covered tracks</th><th>Accepted</th><th>Correct accepted</th><th>Outside-catalogue rejected</th></tr>'''
for method in ('softmax','cosine'):
    for scope in ('single_view_track','multi_view_track'):
        m=results['methods'][method][scope]
        percent=lambda x:'—' if x is None else f'{x:.1%}'
        page+=f'<tr><td>{method} · {scope.replace("_"," ")}</td><td>{percent(m["top1_covered"])}</td><td>{percent(m["top3_covered"])}</td><td>{m["accepted_n"]}/61</td><td>{m["accepted_n"]-m["confidently_wrong"]}</td><td>{percent(m["absent_rejection_rate"])}</td></tr>'
page+='</table><p>Softmax gate: ≥0.8, margin ≥0.2. Cosine gate: ≥0.7, margin ≥0.05. These were fixed before scoring. Cosine values are similarity scores, not probabilities.</p>'
for prediction in predictions:
    ident=prediction['track_id'];covered=prediction['covered'];truth=prediction['truth'];correct=prediction['candidate']==truth
    page+=f'<article><h2>Reference: {name(truth)} · track {ident}</h2><p>{"In model catalogue" if covered else "Outside model catalogue"} · Mean softmax top suggestion: <strong class="{"right" if correct else "wrong"}">{name(prediction["candidate"])} ({prediction["confidence"]:.3f})</strong> · Gated assignment: {name(prediction["assigned"])}</p>'
    other=cosine[ident]
    page+=f'<p>Mean cosine top suggestion: {name(other["candidate"])} ({other["confidence"]:.3f}); gated assignment: {name(other["assigned"])}.</p><div class="views">'
    for crop in sorted(crops[ident],key=lambda r:r['view']):
        data=base64.b64encode((root/crop['crop']).read_bytes()).decode()
        ranked=sorted(crop['softmax'],key=lambda k:-crop['softmax'][k])[:3]
        top=', '.join(f'{name(k)} {crop["softmax"][k]:.3f}' for k in ranked)
        page+=f'<div class="view"><img alt="Expert-labelled fish crop, view {crop["view"]+1}" src="data:image/jpeg;base64,{data}"><p>View {crop["view"]+1}: {top}</p></div>'
    page+='</div></article>'
page+='''<p>CoReFish: Cai et al. (2025), <a href="https://warplab.github.io/corefish/">Species-level Detection and Tracking of Caribbean Coral Reef Fish</a>. Reference imagery: CC BY-NC-SA 4.0. Fishial model: official v0.10.2 bundle. This page is a local research output.</p></main></body></html>'''
out=root/'local_review';(out/'benchmark.html').write_text(page)
(out/'benchmark_results.json').write_text((root/'benchmark_results.json').read_text())
gallery=out/'fish_ID_gallery.html';s=gallery.read_text();s=s.replace('<h1>Fish Gallery</h1>','<h1>Fish Gallery</h1><p><a href="benchmark.html">View the CoReFish benchmark and reference fish</a></p>');gallery.write_text(s)
print(out/'benchmark.html')
