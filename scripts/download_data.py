"""Fetch the author's immutable v1.0.0 archives without credentials."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import hashlib
import json
import zipfile
from range_download import download

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://github.com/PengBo0/Home-fire-dataset/releases/download/v1.0.0/'
SIZES = {'train': 1060672433, 'val': 352482306, 'test': 407778390}


def fetch(split):
    target = ROOT / 'data' / 'archives' / f'{split}.zip'
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        download(BASE + target.name, target, workers=16)
    if target.stat().st_size != SIZES[split]:
        raise ValueError(f'Unexpected archive size: {target}')
    sha = hashlib.file_digest(target.open('rb'), 'sha256').hexdigest()
    destination = ROOT / 'data' / 'raw' / split
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target) as archive:
        if archive.testzip() is not None:
            raise ValueError(f'ZIP CRC check failed: {target}')
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
