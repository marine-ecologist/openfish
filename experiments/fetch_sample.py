"""Download only selected public ZIP members; validate decompression and CRC."""
import concurrent.futures
import json
import struct
import sys
import zipfile
import zlib
import time
from pathlib import Path
import requests
from corefish_fetch import RemoteZip, URL

root = Path(sys.argv[1]); out = root/'corefish'
manifest = json.loads((root/'sample_manifest.json').read_text())
names = sorted({s['image'] for s in manifest['samples']})
remote = RemoteZip()
with zipfile.ZipFile(remote) as archive:
    infos = {name: archive.getinfo(name) for name in names}

def fetch(name):
    target = out/name
    if target.exists(): return 0
    info = infos[name]
    start = info.header_offset
    for attempt in range(4):
        try:
            response = requests.get(URL, headers={'Range': f'bytes={start}-{start+info.compress_size+4095}'}, timeout=(15, 40))
            response.raise_for_status()
            break
        except requests.RequestException:
            if attempt == 3: raise
            time.sleep(attempt + 1)
    response.raise_for_status()
    if response.status_code != 206 or not response.headers['Content-Range'].startswith(f'bytes {start}-'):
        raise ValueError('Invalid HTTP byte range')
    data = response.content
    if data[:4] != b'PK\x03\x04': raise ValueError('Invalid local ZIP header')
    name_len, extra_len = struct.unpack_from('<HH',data,26)
    offset = 30+name_len+extra_len
    compressed = data[offset:offset+info.compress_size]
    if info.compress_type != zipfile.ZIP_DEFLATED: raise ValueError('Unexpected compression')
    raw = zlib.decompress(compressed,-15)
    if len(raw)!=info.file_size or zlib.crc32(raw)!=info.CRC: raise ValueError('CRC/size mismatch')
    target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(raw)
    return len(data)

transferred = remote.transferred
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    for n, size in enumerate(pool.map(fetch,names),1):
        transferred += size
        if n%10==0 or n==len(names): print(f'{n}/{len(names)} images; {transferred/1e6:.1f} MB transferred',flush=True)
(root/'download_summary.json').write_text(json.dumps(dict(images=len(names),transferred_bytes=transferred),indent=2))
