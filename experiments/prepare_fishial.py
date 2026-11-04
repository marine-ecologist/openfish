"""Prepare an already downloaded official v0.10.2 ZIP for the openFish adapter."""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path
import torch

SOURCE='https://storage.googleapis.com/fishial-ml-resources/classification_model_v0.10.2.zip'

def prepare(archive, folder):
    archive=Path(archive);folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(archive) as bundle:
        for name in ('model.pt','info.json','inference.py','requirements.txt'):
            (folder/name).write_bytes(bundle.read(name))
    model=torch.jit.load(str(folder/'model.pt'),map_location='cpu').eval()
    mapping=json.loads(bytes(model.class_mapping_json_bytes.tolist()))
    ordered=[mapping[str(i)] for i in range(len(mapping))]
    labels=[x['label'].lower().replace(' ','_') for x in ordered]
    if len(set(labels))!=len(labels):raise ValueError('Duplicate embedded labels')
    info=json.loads((folder/'info.json').read_text())
    if len(labels)!=info['num_of_class']:raise ValueError('Class count mismatch')
    manifest=dict(backend='fishial_torchscript',model_id='fishial-v0.10.2',
        revision=hashlib.sha256((folder/'model.pt').read_bytes()).hexdigest(),labels=labels,
        catalog={k:dict(scientific_name=v['label'],fishial_species_id=v['species_id']) for k,v in zip(labels,ordered)},
        input_size=info['image_size'],score_method='softmax_arcface_logits',source=SOURCE)
    (folder/'species_manifest.json').write_text(json.dumps(manifest,indent=2))
    return mapping

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--archive',required=True);parser.add_argument('--out',required=True);parser.add_argument('--labels-output');args=parser.parse_args()
    mapping=prepare(args.archive,args.out)
    if args.labels_output:Path(args.labels_output).write_text(json.dumps(mapping,indent=2))
    print('Prepared',len(mapping),'embedded class labels')
