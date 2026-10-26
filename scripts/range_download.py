"""Fallback for networks that stall on unbounded downloads (HTTP Range required)."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import time
import urllib.request


def download(url, path, workers=8):
    with urllib.request.urlopen(urllib.request.Request(url, headers={'Range': 'bytes=0-0'}), timeout=30) as r:
        if r.status != 206:
            raise ValueError('Server must support byte ranges')
        total = int(r.headers['Content-Range'].split('/')[-1])
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix('.part')
    with partial.open('wb') as f:
        f.truncate(total)
    def chunk(start):
        end = min(start+4*1024*1024, total)-1
        for attempt in range(4):
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers={'Range': f'bytes={start}-{end}'}), timeout=40) as r:
                    block = r.read()
                    if len(block) != end-start+1 or r.headers.get('Content-Range') != f'bytes {start}-{end}/{total}':
                        raise ValueError('Unexpected range response')
                with partial.open('r+b') as f:
                    f.seek(start)
                    f.write(block)
                return len(block)
            except (OSError, ValueError):
                if attempt == 3:
                    raise
                time.sleep(attempt+1)
    done = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for n, size in enumerate(pool.map(chunk, range(0, total, 4*1024*1024))):
            done += size
            if n % 20 == 0:
                print(f'{done:,}/{total:,} bytes', flush=True)
    partial.replace(path)
    print(str(path), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('url')
    parser.add_argument('path')
    args = parser.parse_args()
    download(args.url, args.path)
