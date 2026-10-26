"""Fetch Python 3.12 Windows wheels for the reproducible local environment."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import urllib.request
from range_download import download

PACKAGES = {'numpy': '1.26.4', 'opencv-python': '4.10.0.84', 'scipy': '1.14.1',
            'matplotlib': '3.9.2', 'pillow': '11.0.0', 'pandas': '2.2.3', 'polars': '1.26.0'}


def fetch(item):
    name, version = item
    with urllib.request.urlopen(f'https://pypi.org/pypi/{name}/{version}/json', timeout=30) as r:
        data = json.load(r)
    candidates = [f for f in data['urls'] if f['filename'].endswith('win_amd64.whl')
                  and ('cp312-' in f['filename'] or 'cp37-abi3-' in f['filename'] or 'cp39-abi3-' in f['filename'])]
    if len(candidates) != 1:
        raise ValueError(f'Ambiguous wheel selection: {name}: {[f["filename"] for f in candidates]}')
    info = candidates[0]
    target = Path('data/wheels') / info['filename']
    download(info['url'], target)
    import hashlib
    if hashlib.file_digest(target.open('rb'), 'sha256').hexdigest() != info['digests']['sha256']:
        raise ValueError(f'Wheel hash mismatch: {target}')


if __name__ == '__main__':
    with ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(fetch, PACKAGES.items()))
