"""Fetch the author's immutable v1.0.0 archives without credentials."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import hashlib
import json
import urllib.request
import zipfile
import time

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://github.com/PengBo0/Home-fire-dataset/releases/download/v1.0.0/'
SIZES = {'train': 1060672433, 'val': 352482306, 'test': 407778390}


def fetch(split):
    target = ROOT / 'data' / 'archives' / f'{split}.zip'
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        partial = target.with_suffix('.part')
        # Bounded ranges avoid full-file transfer stalls on this network.
        with partial.open('wb') as out:
            for start in range(0, SIZES[split], 8 * 1024 * 1024):
                end = min(start + 8 * 1024 * 1024, SIZES[split]) - 1
                for attempt in range(4):
                    try:
                        req = urllib.request.Request(BASE + target.name,
                            headers={'Range': f'bytes={start}-{end}'})
                        with urllib.request.urlopen(req, timeout=40) as response:
                            chunk = response.read()
                            if response.headers.get('Content-Range') != f'bytes {start}-{end}/{SIZES[split]}' or len(chunk) != end-start+1:
                                raise ValueError('Server returned an unexpected byte range')
                        break
                    except (OSError, ValueError):
                        if attempt == 3:
                            raise
                        time.sleep(1 + attempt)
                out.write(chunk)
                if start % (80 * 1024 * 1024) == 0:
                    print(f'{split}: {end+1:,}/{SIZES[split]:,} bytes', flush=True)
        partial.replace(target)
    sha = hashlib.file_digest(target.open('rb'), 'sha256').hexdigest()
    destination = ROOT / 'data' / 'raw' / split
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target) as archive:
        for member in archive.infolist():
            path = (destination / member.filename).resolve()
            if not path.is_relative_to(destination.resolve()):
                raise ValueError(f'Unsafe archive path: {member.filename}')
        archive.extractall(destination)
    print(f'{split}: {target.stat().st_size:,} bytes, sha256={sha}', flush=True)
    return dict(split=split, url=BASE + target.name, bytes=target.stat().st_size, sha256=sha)


if __name__ == '__main__':
    with ThreadPoolExecutor(max_workers=3) as pool:
        records = list(pool.map(fetch, ['train', 'val', 'test']))
    (ROOT / 'evidence' / 'downloads.json').write_text(json.dumps(records, indent=2))
