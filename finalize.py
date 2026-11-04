"""Validate completed tracking tables, encode the review video, and build a portable ID gallery."""
import argparse,csv,json,subprocess,shutil
import cv2,numpy as np
from pathlib import Path
from enhancement import correct_frame
p=argparse.ArgumentParser(); p.add_argument('--output',default='outputs/full'); a=p.parse_args()
out=Path(a.output)
run=json.loads((out/'run.json').read_text())
assert run['processed_frames']==run['total_frames'] and run['total_frames']>0,run
total=run['total_frames']; width=run['width']; height=run['height']; fps=run['source_fps']
ow=run.get('output_width',1920); oh=run.get('output_height',1080)
color_settings=run.get('settings',{}).get('color',{'enabled':False})
dw,dh=(width,height) if color_settings['enabled'] else (ow,oh)
for name in ('detections','tracks'):
    raw=out/f'{name}_raw.csv'
    if not raw.exists(): shutil.copyfile(out/f'{name}.csv',raw)
rows=list(csv.DictReader((out/'detections_raw.csv').open()))
tracks=list(csv.DictReader((out/'tracks_raw.csv').open()))
assert len(rows)==run['detection_rows']
ids={int(t['track_id']) for t in tracks}
assert len(ids)==run['track_count']
assert {int(r['track_id']) for r in rows if r['track_id']}==ids
mapping={old:new for new,old in enumerate(sorted(ids),1)}
crops=out/'crops'; crops.mkdir(exist_ok=True)
for old,new in mapping.items(): shutil.copyfile(out/f'fish_{old:04d}.jpg',crops/f'fish_{new:04d}.jpg')
for table,name in ((rows,'detections'),(tracks,'tracks')):
    for r in table:
        old=r['track_id']; r['raw_tracker_id']=old
        r['track_id']=mapping[int(old)] if old else ''
    with (out/f'{name}_raw.csv').open() as f: columns=next(csv.reader(f))+['raw_tracker_id']
    with (out/f'{name}.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=columns); w.writeheader(); w.writerows(table)
for r in rows:
    x1,y1,x2,y2=(float(r[k]) for k in ['x1','y1','x2','y2'])
    assert 0<=x1<x2<=width and 0<=y1<y2<=height,r
    assert 0<=int(r['frame'])<total
by_frame={}
for r in rows: by_frame.setdefault(int(r['frame']),[]).append(r)
source_capture=cv2.VideoCapture(run['source']) if color_settings['enabled'] else None
decoder=None if source_capture is not None else subprocess.Popen(['ffmpeg','-hide_banner','-loglevel','error','-i',run['source'],'-vf',f'scale={dw}:{dh}','-pix_fmt','bgr24','-fps_mode','passthrough','-f','rawvideo','pipe:1'],stdout=subprocess.PIPE)
encoder=subprocess.Popen(['ffmpeg','-y','-hide_banner','-loglevel','error','-f','rawvideo','-pix_fmt','bgr24','-s',f'{ow}x{oh}','-r',str(fps),'-i','pipe:0','-i',run['source'],'-map','0:v:0','-map','1:a:0?','-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p','-c:a','aac','-movflags','+faststart',str(out/'fishcount_tracked.mp4')],stdin=subprocess.PIPE)
for n in range(total):
    if source_capture is not None:
        ok,frame=source_capture.read();assert ok,('Cannot decode source frame',n)
    else:
        raw=decoder.stdout.read(dw*dh*3)
        assert len(raw)==dw*dh*3,(n,len(raw))
        frame=np.frombuffer(raw,np.uint8).reshape(dh,dw,3).copy()
    frame=correct_frame(frame,color_settings)
    if (dw,dh)!=(ow,oh):frame=cv2.resize(frame,(ow,oh))
    for r in by_frame.get(n,[]):
        ident=int(r['track_id']) if r['track_id'] else None
        color=(0,200,255) if ident is None else ((ident*53)%200+55,(ident*97)%200+55,(ident*139)%200+55)
        x1,y1,x2,y2=[int(float(r[k])*s) for k,s in zip(['x1','y1','x2','y2'],(ow/width,oh/height,ow/width,oh/height))]
        cv2.rectangle(frame,(x1,y1),(x2,y2),color,2)
        label=(f'Fish {ident:04d}' if ident is not None else 'Fish pending')+f' | {float(r["confidence"]):.2f}'
        (tw,th),_=cv2.getTextSize(label,cv2.FONT_HERSHEY_SIMPLEX,.6,2)
        lx=max(3,min(x1,ow-5-tw)); ly=max(th+8,y1-8)
        cv2.rectangle(frame,(lx-3,ly-th-5),(lx+tw+3,ly+4),(0,0,0),-1)
        cv2.putText(frame,label,(lx,ly),cv2.FONT_HERSHEY_SIMPLEX,.6,(255,255,255),2)
    cv2.rectangle(frame,(10,10),(600,48),(0,0,0),-1)
    cv2.putText(frame,f'{n/run["source_fps"]:.1f}s | Provisional fish track IDs',(20,36),cv2.FONT_HERSHEY_SIMPLEX,.7,(255,255,255),2)
    encoder.stdin.write(frame.tobytes())
    if n in (0,300,900,1800,3000,4500): cv2.imwrite(str(out/f'review_{n:05d}.jpg'),frame)
    if n%600==0: print('Encoded',n,'frames',flush=True)
if source_capture is not None:
    ok,_=source_capture.read();assert not ok,'Source contains more frames than the detector processed';source_capture.release()
else:
    assert not decoder.stdout.read(1),'Decoded source contains more frames than the detector processed'
    decoder.stdout.close();assert decoder.wait()==0
encoder.stdin.close()
assert encoder.wait()==0
probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=nb_frames,width,height,duration','-of','json',str(out/'fishcount_tracked.mp4')]))['streams'][0]
assert int(probe['nb_frames'])==total,probe
from fish_gallery import write_gallery
write_gallery(out, tracks, run)
brief=sum(int(t['detections'])<15 for t in tracks)
log_paths=[out/'processing.log',out.parent/f'{out.name}.log']
warning_count=sum(p.read_text(errors='replace').count('NMS time limit') for p in log_paths if p.exists())
(out/'summary.json').write_text(json.dumps(dict(**run,brief_tracks_under_15_detections=brief,nms_time_limit_warnings=warning_count,video_verified=probe),indent=2))
(out/'REVIEW_NOTES.md').write_text(f'''# Automated fish tracking review

{total:,} source frames processed. {len(tracks):,} provisional track segments; {brief:,} have fewer than 15 detected frames. This is not a count of unique individual fish. IDs can split or switch when fish turn, cross, become obscured, or re-enter. Species are unassigned. Small fish may be missed.

The detector reported {warning_count} NMS time-limit warning(s). Affected batches may have incomplete detections. Model scores are not measured accuracy on this footage.

The final video was checked against the source frame count. Bounding boxes were checked against the source image dimensions, and IDs were checked across both CSV tables. Final consecutive IDs map back to BoT-SORT through the raw_tracker_id column.
''')
print(json.dumps(dict(tracks=len(tracks),detection_rows=len(rows),brief_tracks=brief,video=probe),indent=2))
