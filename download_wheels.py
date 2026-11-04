import json, subprocess, concurrent.futures, pathlib, hashlib
dest=pathlib.Path('wheelhouse'); dest.mkdir(exist_ok=True)
packages=[('opencv-python','5.0.0.93','cp37-abi3-macosx_13_0_arm64'),('torch','2.15.0','cp315-cp315-macosx_14_0_arm64'),('polars-runtime-32','2.1.0','cp311-abi3-macosx_11_0_arm64'),('torchvision','0.29.2','py3-none-macosx_14_0_arm64')]
jobs=[]; entries=[]; chunk=8*1024*1024
for name,version,tag in packages:
    data=json.loads(subprocess.check_output(['curl','-sSfL',f'https://pypi.org/pypi/{name}/{version}/json']))
    info=next(x for x in data['urls'] if tag in x['filename'])
    entries.append(info)
    for i,start in enumerate(range(0,info['size'],chunk)):
        jobs.append((info,i,start,min(info['size']-1,start+chunk-1)))
def get(job):
    info,i,start,end=job; path=dest/(info['filename']+f'.{i}.part')
    subprocess.run(['curl','-sSfL','--retry','3','--range',f'{start}-{end}',info['url'],'-o',str(path)],check=True)
    assert path.stat().st_size==end-start+1
    print(info['filename'],i,'done',flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool: list(pool.map(get,jobs))
for info in entries:
    path=dest/info['filename']
    with path.open('wb') as f:
        for i in range((info['size']+chunk-1)//chunk): f.write((dest/(info['filename']+f'.{i}.part')).read_bytes())
    assert hashlib.sha256(path.read_bytes()).hexdigest()==info['digests']['sha256']
print('Wheels verified',flush=True)
