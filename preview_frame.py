"""Extract a full-resolution source still and apply the same correction as inference."""
import argparse,json
from pathlib import Path
import cv2
from fish_settings import read_settings
from enhancement import correct_frame
p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--settings',required=True);p.add_argument('--time',type=float,default=0);p.add_argument('--output',required=True);a=p.parse_args()
s=read_settings(a.settings); cap=cv2.VideoCapture(a.source)
if not cap.isOpened():raise ValueError('Cannot open the selected video.')
fps=cap.get(cv2.CAP_PROP_FPS); total=int(cap.get(cv2.CAP_PROP_FRAME_COUNT)); n=max(0,min(total-1,round(a.time*fps)))
cap.set(cv2.CAP_PROP_POS_FRAMES,n); ok,frame=cap.read(); cap.release()
if not ok:raise ValueError('Cannot decode this still.')
out=Path(a.output); out.mkdir(parents=True,exist_ok=True)
for name,image in [('original',frame),('corrected',correct_frame(frame,s['color']))]:
    scale=min(1,1440/image.shape[1]); image=cv2.resize(image,(round(image.shape[1]*scale),round(image.shape[0]*scale)))
    if not cv2.imwrite(str(out/f'{name}.png'),image):raise RuntimeError('Could not save preview.')
(out/'preview.json').write_text(json.dumps(dict(frame=n,time_s=n/fps,duration_s=total/fps,source=a.source,settings=s)))
