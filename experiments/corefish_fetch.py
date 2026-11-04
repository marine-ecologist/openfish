"""Fetch selected members of the public CoReFish ZIP with verified HTTP ranges."""
import io
import json
import sys
import zipfile
from pathlib import Path
import requests

URL = 'https://drive.usercontent.google.com/download?id=1LENr6D8XW8ivusF2riS0v27Grwa1Uj2q&export=download&confirm=t'

class RemoteZip(io.RawIOBase):
    def __init__(self):
        self.session = requests.Session()
        response = self.session.get(URL, headers={'Range': 'bytes=-131072'}, timeout=60)
        response.raise_for_status()
        if response.status_code != 206:
            raise ValueError('Server did not honor range request')
        self.size = int(response.headers['Content-Range'].split('/')[-1])
        self.tail = response.content
        self.position = 0
        self.transferred = len(self.tail)
    def seekable(self): return True
    def tell(self): return self.position
    def seek(self, offset, whence=0):
        self.position = offset if whence == 0 else self.position + offset if whence == 1 else self.size + offset
        return self.position
    def read(self, size=-1):
        if size < 0: size = self.size - self.position
        size = min(size, self.size-self.position)
        if not size: return b''
        start = self.position
        if start >= self.size - len(self.tail):
            data = self.tail[start-(self.size-len(self.tail)):][:size]
        else:
            response = self.session.get(URL, headers={'Range': f'bytes={start}-{start+size-1}'}, timeout=90)
            response.raise_for_status()
            if response.status_code != 206 or not response.headers['Content-Range'].startswith(f'bytes {start}-'):
                raise ValueError('Invalid range response')
            data = response.content
            if len(data) != size: raise ValueError('Truncated range')
            self.transferred += len(data)
        self.position += len(data)
        return data

if __name__ == '__main__':
    out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
    remote = RemoteZip()
    with zipfile.ZipFile(remote) as archive:
        infos = archive.infolist()
        (out / 'zip_index.json').write_text(json.dumps([dict(name=i.filename, size=i.file_size, compressed=i.compress_size) for i in infos], indent=2))
        selected = sys.argv[2:]
        if not selected:
            selected = [i.filename for i in infos if i.filename.lower().endswith(('.json', '.md', '.yaml')) and i.file_size < 40_000_000]
        for name in selected:
            target = out / name
            if not target.resolve().is_relative_to(out.resolve()): raise ValueError('Unsafe path')
            if target.exists(): continue
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(name))
            print(name, target.stat().st_size, flush=True)
    print('Transferred bytes:', remote.transferred)
