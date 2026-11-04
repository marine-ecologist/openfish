"""Persistent human track labels and versioned, leakage-aware training exports."""
import csv
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from species import dataset_identity
from fish_phase import normalize_phase


def atomic_json(path, value):
    path = Path(path)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False)+'\n')
    temporary.replace(path)


def candidates(out, track):
    """Rank available original-color samples; no upscaling or video reprocessing."""
    from PIL import Image, ImageFilter, ImageStat
    out = Path(out); ident = int(track['track_id'])
    raw = track.get('raw_tracker_id') or ident
    paths = list((out/'similarity_samples'/str(raw)).glob('*.jpg'))
    paths += [out/'crops'/f'fish_{ident:04d}.jpg']
    images = {}; failures = []
    for path in paths:
        try:
            data = path.read_bytes(); fingerprint = hashlib.sha256(data).hexdigest()
            with Image.open(path) as image:
                width, height = image.size
                if min(width, height) < 16: continue
                edge = image.convert('L').filter(ImageFilter.FIND_EDGES)
                sharpness = ImageStat.Stat(edge).var[0]
            entry = dict(path=str(path.relative_to(out)), sha256=fingerprint, width=width, height=height,
                         quality=min(width*height, 250000)**.5 * (1+min(sharpness, 1000)/1000))
            if fingerprint not in images: images[fingerprint] = entry
        except (OSError, ValueError): failures.append(str(path))
    return sorted(images.values(), key=lambda r: (-r['quality'], r['path']))[:4]


class TrainingStore:
    def __init__(self, out, tracks):
        self.out = Path(out); self.tracks = {int(t['track_id']): t for t in tracks}
        self.fingerprint = dataset_identity(self.out)
        self.catalog = json.loads((Path(__file__).parent/'catalogs/caribbean_training.json').read_text())
        regional=json.loads((Path(__file__).parent/'catalogs/caribbean_reef_v5.json').read_text())
        self.catalog.update(regional)
        predictions = self.out/'species_predictions.json'
        if predictions.exists():
            model_catalog=json.loads(predictions.read_text()).get('catalog',{})
        else:model_catalog={}
        catalog_path=self.out/'training_catalog.json'
        pinned=json.loads(catalog_path.read_text()) if catalog_path.exists() else {}
        self.catalog.update({k:v for k,v in pinned.items() if k in self.catalog or 'fishial_species_id' not in v})
        self.path = self.out/'training_labels.json'
        self.data = dict(schema_version=1, dataset_sha256=self.fingerprint, labels={}, history=[])
        if self.path.exists():
            self.data = json.loads(self.path.read_text())
            if self.data['dataset_sha256'] != self.fingerprint:
                raise ValueError('Training labels belong to a changed track table or run. Restore the original run before editing.')
        for row in self.data['labels'].values():
            key=row.get('species_id')
            if key not in self.catalog:
                if key in pinned:self.catalog[key]=pinned[key]
                elif key in model_catalog:self.catalog[key]=model_catalog[key]
        for row in self.data['labels'].values():row.setdefault('phase',normalize_phase(row.get('species_id'),self.catalog))
        self.samples = {ident: candidates(self.out, track) for ident, track in self.tracks.items()}

    def label(self, ident): return self.data['labels'].get(str(ident), {})

    def save(self, ident, status, species_id, reviewer, note, approved, phase=None):
        if dataset_identity(self.out) != self.fingerprint: raise ValueError('Run changed; reopen it before saving.')
        if ident not in self.tracks: raise ValueError('Unknown track')
        if status not in ('species', 'unidentified', 'excluded'): raise ValueError('Choose a review outcome')
        if not reviewer.strip(): raise ValueError('Enter a reviewer name')
        if status == 'species' and species_id not in self.catalog: raise ValueError('Choose a species')
        available = {s['sha256']: s for s in self.samples[ident]}
        if set(approved)-set(available): raise ValueError('Unknown crop')
        row = dict(track_id=ident, status=status, phase=normalize_phase(species_id if status=='species' else None,self.catalog,phase), species_id=species_id if status=='species' else None,
                   reviewer=reviewer.strip(), note=note, approved=sorted(set(approved)),
                   reviewed_at=datetime.now(timezone.utc).isoformat())
        self.save_group([row])

    def save_group(self, rows):
        """Validate and commit an explicitly reviewed group in one label-file write."""
        if dataset_identity(self.out)!=self.fingerprint:raise ValueError('Run changed; reopen before saving')
        updated=json.loads(json.dumps(self.data))
        for source in rows:
            row=dict(source)
            ident=row['track_id'];status=row['status']
            if ident not in self.tracks or status not in ('species','unidentified','excluded'):raise ValueError('Invalid review')
            if not row['reviewer'].strip():raise ValueError('Enter a reviewer name')
            if status=='species' and row['species_id'] not in self.catalog:raise ValueError('Choose a species')
            if set(row['approved'])-{s['sha256'] for s in self.samples[ident]}:raise ValueError('Unknown crop')
            row['phase']=normalize_phase(row.get('species_id') if status=='species' else None,self.catalog,row.get('phase'))
            row['reviewed_at']=datetime.now(timezone.utc).isoformat()
            updated['labels'][str(ident)]=row;updated['history'].append(row)
        atomic_json(self.out/'training_catalog.json',self.catalog)
        atomic_json(self.path,updated);self.data=updated

    @property
    def complete(self): return bool(self.tracks) and all(self.label(i).get('status') in ('species','unidentified','excluded') for i in self.tracks)

    def export(self):
        if not self.complete: raise ValueError('Review every track before exporting')
        if dataset_identity(self.out) != self.fingerprint: raise ValueError('Run changed; reopen before exporting')
        run = json.loads((self.out/'run.json').read_text())
        source = str(Path(run['source']).resolve())
        group_id = hashlib.sha256(source.encode()).hexdigest()
        rows = []; track_rows = []
        for ident in sorted(self.tracks):
            label = self.label(ident); track_rows.append({**label, 'approved': ';'.join(label['approved'])})
            if label['status'] != 'species': continue
            by_hash = {s['sha256']: s for s in self.samples[ident]}
            for fingerprint in label['approved']:
                sample = by_hash.get(fingerprint)
                if sample is None: raise ValueError('Approved crop no longer available')
                path = self.out/sample['path']
                if hashlib.sha256(path.read_bytes()).hexdigest() != fingerprint: raise ValueError('Approved crop changed; review again')
                species_id = label['species_id']
                # Hash-based directory names prevent external catalogue IDs becoming paths.
                folder = hashlib.sha256(species_id.encode()).hexdigest()[:16]
                rows.append(dict(track_id=ident, species_id=species_id, phase=label['phase'], scientific_name=self.catalog[species_id]['scientific_name'],
                    image=f'images/{folder}/track_{ident}_{fingerprint[:16]}.jpg', source_crop=sample['path'],
                    sha256=fingerprint, width=sample['width'], height=sample['height'],
                    video_group=group_id, reviewer=label['reviewer']))
        manifest = dict(schema_version=1, dataset_sha256=self.fingerprint, source_video=source, video_group=group_id,
            grouping_policy='Keep this entire source video together when splitting training/evaluation. Group key is based on the recorded source path; deduplicate renamed copies across surveys.',
            crop_policy='Up to four available original-color images ranked by area and edge detail; exact duplicates removed; human approval required.',
            phase_policy='Manual visual appearance only, not sex or maturity confirmation. Not assessed and uncertain phases are not phase-training ground truth.', reviewed_tracks=len(track_rows), training_images=len(rows), samples=rows, tracks=track_rows,
            catalog={k:self.catalog[k] for k in sorted({r['species_id'] for r in rows})})
        version = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()[:16]
        destination = self.out/'training_exports'/version
        if destination.exists():
            # An existing snapshot must still have all its declared contents.
            for row in rows:
                if hashlib.sha256((destination/row['image']).read_bytes()).hexdigest()!=row['sha256']: raise ValueError('Existing export is damaged')
            return destination
        staging = destination.with_name(version+'.building')
        staging.mkdir(parents=True, exist_ok=True)
        for row in rows:
            target = staging/row['image']; target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(self.out/row['source_crop'], target)
        atomic_json(staging/'manifest.json', manifest)
        for name, values, columns in [('samples',rows,['track_id','species_id','phase','scientific_name','image','source_crop','sha256','width','height','video_group','reviewer']),
            ('tracks',track_rows,['track_id','status','species_id','phase','reviewer','note','approved','reviewed_at'])]:
            with (staging/f'{name}.csv').open('w',newline='') as stream:
                writer=csv.DictWriter(stream,fieldnames=columns);writer.writeheader();writer.writerows(values)
        (staging/'README.txt').write_text('Human-reviewed openFish training snapshot.\nOnly confirmed species with approved crops appear in samples.csv.\nUnidentified/excluded tracks remain in tracks.csv for audit, not supervised species training.\nNo model training or train/test split has been performed. Keep source videos/surveys together.\n')
        staging.rename(destination)
        return destination
