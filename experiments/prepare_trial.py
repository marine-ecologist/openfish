"""Select a deterministic bounded CoReFish pilot, without using model outputs."""
import collections
import json
import random
from pathlib import Path

# Explicit crosswalk from CoReFish category codes/common names, not image similarity.
# Broader/generic labels are deliberately absent. Azurina names retain current genus.
CROSSWALK = {
'absa': 'Abudefduf saxatilis', 'acch': 'Acanthurus chirurgus', 'acco': 'Acanthurus coeruleus',
'acpo': 'Acanthostracion polygonium', 'acqu': 'Acanthostracion quadricornis', 'actr': 'Acanthurus tractus',
'alsc': 'Aluterus scriptus', 'anvi': 'Anisotremus virginicus',
'azcy': 'Azurina cyanea', 'azmu': 'Azurina multilineata', 'bach': 'Brachygenys chrysargyrea',
'boru': 'Bodianus rufus', 'cama': 'Cantherhines macrocerus', 'capu': 'Cantherhines pullus',
'carb': 'Caranx bartholomaei', 'carl': 'Caranx latus', 'caro': 'Canthigaster rostrata', 'caru': 'Caranx ruber',
'cecr': 'Cephalopholis cruentata', 'cefu': 'Cephalopholis fulva',
'chca': 'Chaetodon capistratus', 'choc': 'Chaetodon ocellatus', 'chst': 'Chaetodon striatus',
'clpa': 'Clepticus parrae', 'daam': 'Hypanus americanus', 'dioh': 'Diodon hystrix',
'epad': 'Epinephelus adscensionis', 'epgu': 'Epinephelus guttatus', 'epst': 'Epinephelus striatus',
'eqpu': 'Eques punctatus', 'gici': 'Ginglymostoma cirratum', 'gral': 'Gramma loreto',
'hafl': 'Haemulon flavolineatum', 'haga': 'Halichoeres garnoti', 'hara': 'Halichoeres radiatus',
'hasc': 'Haemulon sciurus', 'hoca': 'Holacanthus ciliaris', 'hotr': 'Holacanthus tricolor',
'hyni': 'Hypoplectrus nigricans', 'hypu': 'Hypoplectrus puella', 'labi': 'Lactophrys bicaudalis',
'lama': 'Lachnolaimus maximus', 'latr': 'Lactophrys triqueter',
'luap': 'Lutjanus apodus', 'lugr': 'Lutjanus griseus', 'micr': 'Microspathodon chrysurus',
'muma': 'Mulloidichthys martinicus', 'myja': 'Myripristis jacobus', 'occh': 'Ocyurus chrysurus',
'opau': 'Opistognathus aurifrons', 'papa': 'Pomacanthus paru', 'poar': 'Pomacanthus arcuatus',
'psma': 'Pseudupeneus maculatus', 'rere': 'Remora remora', 'scis': 'Scarus iseri',
'scpl': 'Scorpaena plumieri', 'scta': 'Scarus taeniopterus', 'scve': 'Scarus vetula',
'sote': 'Sphoeroides testudineus', 'spau': 'Sparisoma aurofrenatum', 'spba': 'Sphyraena barracuda',
'spvi': 'Sparisoma viride', 'stad': 'Stegastes adustus', 'stdi': 'Stegastes diencaeus',
'stle': 'Stegastes leucostictus', 'stpa': 'Stegastes partitus', 'stpl': 'Stegastes planifrons',
'stxa': 'Stegastes xanthurus', 'thbi': 'Thalassoma bifasciatum', 'spru': 'Sparisoma rubripinne'
}
ALIASES = {'Acanthostracion polygonium': ['Acanthostracion polygonius'], 'Eques punctatus': ['Equetus punctatus'], 'Azurina cyanea': ['Chromis cyanea'], 'Azurina multilineata': ['Chromis multilineata'],
           'Brachygenys chrysargyrea': ['Haemulon chrysargyreum'], 'Hypanus americanus': ['Dasyatis americana']}

def prepare(root):
    root = Path(root)
    data = json.loads((root/'corefish/corefish_dataset/coco_species.json').read_text())
    labels = json.loads((root/'fishial_labels.json').read_text())
    name_to_id = {v['label']: int(k) for k,v in labels.items()}
    annotations = {a['id']: a for a in data['annotations']}
    images = {i['id']: i for i in data['images']}
    categories = {c['id']: c for c in data['categories']}
    available_images = {i['name'] for i in json.loads((root/'corefish/zip_index.json').read_text())}
    by_category = collections.defaultdict(list)
    for track in data['object_tracks']:
        rows = [annotations[i] for i in track['annotation_id_list']]
        cats = {a['category_id'] for a in rows}
        if len(cats) != 1: continue
        cat = next(iter(cats))
        code = categories[cat]['name'].split('_')[0]
        if code not in CROSSWALK: continue
        valid = [a for a in rows if min(a['bbox'][2:]) >= 16 and 'corefish_dataset/images/images/'+images[a['image_id']]['file_name'] in available_images]
        if len(valid) >= 3:
            by_category[cat].append((track['id'], valid))
    crosswalk = []
    for c in data['categories']:
        name = CROSSWALK.get(c['name'].split('_')[0])
        options = [name] + ALIASES.get(name, [])
        matched = next((n for n in options if n in name_to_id), None)
        crosswalk.append(dict(category_id=c['id'], category=c['name'], scientific_name=name,
                              model_class=name_to_id.get(matched), model_name=matched,
                              eligible_tracks=len(by_category[c['id']]),
                              interpretation='explicit_species_crosswalk' if name else 'broader_or_ambiguous_excluded'))
    samples = []
    randomizer = random.Random(20261104)
    for entry in crosswalk:
        available = sorted(by_category[entry['category_id']])
        randomizer.shuffle(available)
        for ident, rows in available[:2]:
            rows = sorted(rows, key=lambda a: a['image_id'])
            chosen = [rows[0], rows[(len(rows)-1)//2], rows[-1]]
            for view, annotation in enumerate(chosen):
                samples.append(dict(track_id=ident, view=view, annotation_id=annotation['id'],
                    category_id=entry['category_id'], truth=entry['scientific_name'],
                    model_class=entry['model_class'], bbox=annotation['bbox'],
                    image='corefish_dataset/images/images/'+images[annotation['image_id']]['file_name']))
    (root/'crosswalk.json').write_text(json.dumps(crosswalk,indent=2))
    (root/'sample_manifest.json').write_text(json.dumps(dict(seed=20261104, tracks_per_species=2, views_per_track=3,
        min_crop_side=16, samples=samples),indent=2))
    print('Selected',len(samples),'crops,',len({s['track_id'] for s in samples}),'tracks,',len({s['truth'] for s in samples}),'species')
    print('Covered species',len({s['truth'] for s in samples if s['model_class'] is not None}))

if __name__ == '__main__':
    import sys
    prepare(sys.argv[1])
