"""Reproduce the bounded Fishial/CoReFish pilot and prepare local review gallery."""
import argparse
import collections
import csv
import hashlib
import json
import platform
import random
import shutil
import sys
from pathlib import Path
import numpy as np
from PIL import Image

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fishial_species import FishialClassifier
from species import build_species, save
from fish_gallery import write_gallery


def classify(scores, threshold=.8, margin=.2):
    ranked = sorted(scores, key=lambda k: (-scores[k],k))
    best = ranked[0]
    confidence = scores[best]
    accepted = confidence >= threshold and confidence-scores[ranked[1]] >= margin
    return dict(candidate=best, assigned=best if accepted else 'unidentified', confidence=confidence,
                top3=ranked[:3], scores=scores)


def metrics(rows):
    covered = [r for r in rows if r['covered']]
    absent = [r for r in rows if not r['covered']]
    accepted = [r for r in rows if r['assigned']!='unidentified']
    safe = lambda a,b: a/b if b else None
    return dict(n=len(rows), covered_n=len(covered), absent_n=len(absent),
        top1_covered=safe(sum(r['candidate']==r['truth'] for r in covered),len(covered)),
        top3_covered=safe(sum(r['truth'] in r['top3'] for r in covered),len(covered)),
        accepted_n=len(accepted), acceptance_rate=safe(len(accepted),len(rows)),
        accepted_precision=safe(sum(r['assigned']==r['truth'] for r in accepted),len(accepted)),
        confidently_wrong=sum(r['assigned']!=r['truth'] for r in accepted),
        unidentified_rate=safe(sum(r['assigned']=='unidentified' for r in rows),len(rows)),
        absent_rejection_rate=safe(sum(r['assigned']=='unidentified' for r in absent),len(absent)),
        absent_false_acceptances=sum(r['assigned']!='unidentified' for r in absent))


def write_table(path, rows, fields):
    with Path(path).open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(rows)


def local_review(root, model, source):
    source=Path(source);out=root/'local_review';(out/'crops').mkdir(parents=True,exist_ok=True)
    with (source/'tracks.csv').open() as stream:
        tracks=list(csv.DictReader(stream))
    eligible=[t for t in tracks if int(t['detections'])>=15 and (source/'crops'/f"fish_{int(t['track_id']):04d}.jpg").exists()]
    eligible.sort(key=lambda t:(float(t['first_s']),int(t['track_id'])))
    indices=np.linspace(0,len(eligible)-1,min(36,len(eligible)),dtype=int)
    selected=[eligible[i] for i in indices]
    if not selected: raise ValueError('No usable local tracks')
    write_table(out/'tracks.csv',selected,list(tracks[0]))
    run=json.loads((source/'run.json').read_text())
    run['species_trial_source_run']=str(source.resolve())
    run['species_trial_note']='36 or fewer chronological evenly spaced tracks with >=15 detections; not expert labelled.'
    save(out/'run.json',run)
    for t in selected:
        ident=int(t['track_id']);shutil.copyfile(source/'crops'/f'fish_{ident:04d}.jpg',out/'crops'/f'fish_{ident:04d}.jpg')
        raw=t.get('raw_tracker_id') or ident
        paths=sorted((source/'similarity_samples'/str(raw)).glob('*.jpg'))[:4]
        for path in paths:
            dest=out/'similarity_samples'/str(raw)/path.name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,dest)
    predictions=build_species(out,selected,model)
    similarity_path=source/'similarity.json'
    similarity=json.loads(similarity_path.read_text()) if similarity_path.exists() else dict(status='unavailable',groups=[],message='Grouping unavailable')
    ids={int(t['track_id']) for t in selected}
    similarity['groups']=[[i for i in group if i in ids] for group in similarity['groups']]
    similarity['groups']=[g for g in similarity['groups'] if g]
    similarity['message']='Existing appearance groups retained for browsing only. Model suggestions await your verification.'
    write_gallery(out,selected,run,species_result=predictions,similarity_result=similarity)
    fields=['track_id','species_id','reviewer','reviewed_at','note']
    write_table(out/'validation_labels.csv',[dict(track_id=t['track_id'],species_id='',reviewer='',reviewed_at='',note='') for t in selected],fields)
    save(out/'validation_status.json',dict(status='awaiting_user_review',reviewed_tracks=0,selected_tracks=len(selected),accuracy=None))
    print('Local gallery:',out/'fish_ID_gallery.html',flush=True)


def benchmark(root, model):
    manifest=json.loads((root/'sample_manifest.json').read_text());rows=[]
    (root/'benchmark_crops').mkdir(exist_ok=True)
    for n,sample in enumerate(manifest['samples'],1):
        crop=root/'benchmark_crops'/f"track_{sample['track_id']}_view_{sample['view']}.jpg"
        with Image.open(root/'corefish'/sample['image']) as image:
            x,y,w,h=sample['bbox']
            if not (x>=0 and y>=0 and x+w<=image.width and y+h<=image.height): raise ValueError('Out of bounds annotation')
            image.crop((int(x),int(y),int(x+w),int(y+h))).save(crop,quality=95)
        scores=model.score(crop)
        rows.append(dict(**sample,crop=str(crop.relative_to(root)),sha256=hashlib.sha256(crop.read_bytes()).hexdigest(),**scores))
        if n%20==0: print('Scored',n,'/',len(manifest['samples']),flush=True)
    save(root/'crop_scores.json',rows)
    modes={}
    for method,threshold,margin in [('softmax',.8,.2),('cosine',.7,.05)]:
        crop_rows=[];first_rows=[];track_rows=[]
        grouped=collections.defaultdict(list)
        for r in rows:grouped[r['track_id']].append(r)
        for ident,views in sorted(grouped.items()):
            views.sort(key=lambda v:v['view'])
            info=dict(track_id=ident,truth=model.labels[views[0]['model_class']] if views[0]['model_class'] is not None else views[0]['truth'].lower().replace(' ','_'),dataset_species=views[0]['truth'],covered=views[0]['model_class'] is not None)
            for v in views:
                crop_rows.append(dict(**info,**classify(v[method],threshold,margin)))
            first_rows.append(dict(**info,**classify(views[0][method],threshold,margin)))
            mean={k:sum(v[method][k] for v in views)/len(views) for k in model.labels}
            track_rows.append(dict(**info,**classify(mean,threshold,margin)))
        modes[method]=dict(threshold=threshold,margin=margin,crop=metrics(crop_rows),single_view_track=metrics(first_rows),multi_view_track=metrics(track_rows))
        save(root/f'{method}_track_predictions.json',track_rows)
        per_species=[]
        for truth in sorted({r['truth'] for r in track_rows}):
            actual=[r for r in track_rows if r['truth']==truth];predicted=[r for r in track_rows if r['candidate']==truth]
            tp=sum(r['candidate']==truth for r in actual)
            per_species.append(dict(species=truth,covered=actual[0]['covered'],support=len(actual),top1_correct=tp,
                recall=tp/len(actual),precision=tp/len(predicted) if predicted else '',accepted=sum(r['assigned']!='unidentified' for r in actual)))
        write_table(root/f'{method}_per_species.csv',per_species,list(per_species[0]))
        for kind,key in [('top1','candidate'),('gated','assigned')]:
            confusion=collections.Counter((r['truth'],r[key]) for r in track_rows)
            write_table(root/f'{method}_{kind}_confusion.csv',[dict(truth=a,predicted=b,count=n) for (a,b),n in sorted(confusion.items())],['truth','predicted','count'])
    import torch,cv2
    provenance=dict(model=model.manifest,python=platform.python_version(),torch=torch.__version__,opencv=cv2.__version__,
        annotation_sha256=hashlib.sha256((root/'corefish/corefish_dataset/coco_species.json').read_bytes()).hexdigest(),
        sample_manifest_sha256=hashlib.sha256((root/'sample_manifest.json').read_bytes()).hexdigest(),
        note='Exploratory external-dataset pilot; training overlap unknown. No fine tuning or threshold fitting. Broad labels excluded; no species inference from appearance groups.')
    save(root/'benchmark_results.json',dict(provenance=provenance,methods=modes))
    print(json.dumps(modes,indent=2),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',required=True);parser.add_argument('--local-source');parser.add_argument('--benchmark',action='store_true');args=parser.parse_args()
    root=Path(args.root);model=FishialClassifier(root/'fishial-model')
    if args.local_source:local_review(root,model,args.local_source)
    if args.benchmark:benchmark(root,model)
