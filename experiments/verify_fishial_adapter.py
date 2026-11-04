"""Compare the adapter against inference.py shipped with the downloaded model."""
import importlib.util
import json
import os
os.environ["NO_ALBUMENTATIONS_UPDATE"] = "1"
import sys
from pathlib import Path
import cv2
import numpy as np
import torch
from PIL import Image

root=Path(sys.argv[1]).resolve()
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fishial_species import FishialClassifier
# Optional, isolated verification-only dependency directory.
if (root/'verification_deps').exists():sys.path.insert(0,str(root/'verification_deps'))
spec=importlib.util.spec_from_file_location('fishial_vendor_inference',root/'fishial-model/inference.py')
vendor=importlib.util.module_from_spec(spec);sys.modules[spec.name]=vendor;spec.loader.exec_module(vendor)
model=FishialClassifier(root/'fishial-model')
engine=vendor.FishInferenceEngine.from_bundle(str(root/'fishial-model/model.pt'),input_size=(154,434),device='cpu',config=vendor.InferenceConfig(max_unique_classes=3))
rows=json.loads((root/'crop_scores.json').read_text())
selected=[rows[0],rows[1],rows[-1],*sorted(rows,key=lambda r:r['bbox'][2]*r['bbox'][3],reverse=True)[:3]]
checks=[]
for row in selected:
    path=root/row['crop'];rgb=np.array(Image.open(path).convert('RGB'))
    output=engine.predict(rgb,method='arcface_logits')
    predicted=model.score(path)
    ranked=sorted(predicted['softmax'],key=lambda k:-predicted['softmax'][k])[:3]
    names=[r.name.lower().replace(' ','_') for r in output.top_k]
    delta=max(abs(predicted['softmax'][k]-r.accuracy) for k,r in zip(ranked,output.top_k))
    if names!=ranked or delta>1e-5:raise AssertionError((names,ranked,delta))
    # Also ensure the original benchmark stored the same scores.
    stored_delta=max(abs(row['softmax'][k]-predicted['softmax'][k]) for k in model.labels)
    if stored_delta>1e-5:raise AssertionError(('Stored score mismatch',stored_delta))
    checks.append(dict(crop=row['crop'],top3_match=True,max_softmax_difference=delta,stored_score_difference=stored_delta))
result=dict(status='passed',source='inference.py from official v0.10.2 ZIP',checks=checks,opencv=cv2.__version__,
    note='Vendor box-only inference, same CPU model and native ArcFace softmax; no segmentation or TTA.')
(root/'adapter_verification.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
