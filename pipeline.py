"""FireSense AI: audited data, reproducible YOLOv8 training and inference."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent


def save_json(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, indent=2), encoding='utf-8')


def parse_label(text):
    rows = []
    for line in text.splitlines():
        values = [float(v) for v in line.split()]
        if len(values) != 5 or not all(math.isfinite(v) for v in values):
            raise ValueError(f'Invalid YOLO row: {line}')
        cls, x, y, w, h = values
        if cls not in (0, 1) or not (0 < w <= 1 and 0 < h <= 1):
            raise ValueError(f'Invalid class or size: {line}')
        if min(x-w/2, y-h/2) < -1e-5 or max(x+w/2, y+h/2) > 1+1e-5:
            raise ValueError(f'Box outside image: {line}')
        rows.append([int(cls), x, y, w, h])
    return rows


def unique_records(records):
    seen, kept, removed = set(), [], []
    for r in sorted(records, key=lambda r: {'test': 0, 'val': 1, 'train': 2}[r['split']]):
        if r['hash'] in seen:
            removed.append(r)
        else:
            seen.add(r['hash'])
            kept.append(r)
    return kept, removed


def prepare():
    from PIL import Image, ImageOps
    import yaml
    records, rejected = [], []
    for split in ['train', 'val', 'test']:
        base = ROOT / 'data/raw' / split
        labels = {p.stem: p for p in base.rglob('*.txt') if p.name != 'classes.txt'}
        images = sorted(p for p in base.rglob('*') if p.suffix.lower() in {'.jpg', '.jpeg', '.png'})
        if not images:
            raise FileNotFoundError(f'No images under {base}; run scripts/download_data.py first')
        for p in images:
            try:
                label = labels[p.stem]
                rows = parse_label(label.read_text(encoding='utf-8-sig'))
                with Image.open(p) as im:
                    if im.getexif().get(274, 1) != 1:
                        raise ValueError('EXIF rotation requires explicit annotation conversion')
                    im = ImageOps.exif_transpose(im).convert('RGB')
                    digest = hashlib.sha256(str(im.size).encode() + im.tobytes()).hexdigest()
                records.append(dict(split=split, image=str(p.relative_to(ROOT)),
                                    label=str(label.relative_to(ROOT)), hash=digest, boxes=rows))
            except (KeyError, ValueError, OSError) as e:
                rejected.append(dict(split=split, image=str(p.relative_to(ROOT)), reason=str(e)))
    kept, removed = unique_records(records)
    counts = {}
    for split in ['train', 'val', 'test']:
        selected = [r for r in kept if r['split'] == split]
        folder = ROOT / 'data/prepared' / split
        (folder / 'images').mkdir(parents=True, exist_ok=True)
        (folder / 'labels').mkdir(parents=True, exist_ok=True)
        # Refuse stale files: manifests and dataset directories must describe the same experiment.
        expected = {Path(r['image']).stem for r in selected}
        existing = {p.stem for p in (folder / 'images').glob('*')}
        if existing - expected:
            raise ValueError(f'Stale data in {folder}; use a fresh data/prepared directory')
        for r in selected:
            src = ROOT / r['image']
            target = folder / 'images' / (src.stem + '.jpg')
            if not target.exists():
                with Image.open(src) as im:
                    im = im.convert('RGB')
                    im.thumbnail((640, 640))
                    im.save(target, quality=95)
            shutil.copyfile(ROOT / r['label'], folder / 'labels' / (src.stem + '.txt'))
            r['prepared'] = str(target.relative_to(ROOT))
        c = Counter(int(box[0]) for r in selected for box in r['boxes'])
        counts[split] = dict(images=len(selected), fire_boxes=c[0], smoke_boxes=c[1],
                             negatives=sum(not r['boxes'] for r in selected))
    config = dict(path=str((ROOT / 'data/prepared').resolve()), train='train/images',
                  val='val/images', test='test/images', names={0: 'fire', 1: 'smoke'})
    (ROOT / 'data/dataset.yaml').write_text(yaml.safe_dump(config), encoding='utf-8')
    save_json(ROOT / 'evidence/manifest.json', kept)
    audit = dict(counts=counts, raw_images=len(records)+len(rejected),
                 rejected=rejected, exact_duplicates_removed=removed,
                 policy='Preserve test, then val, then train; exact decoded RGB SHA256 deduplication; resize max side 640 JPEG quality 95',
                 scene_independence='Not established: original video IDs are not mapped to frames')
    save_json(ROOT / 'evidence/data_audit.json', audit)
    print(json.dumps(counts, indent=2), 'Rejected:', len(rejected), 'Duplicates:', len(removed))


def train(args):
    from ultralytics import YOLO
    import torch
    torch.set_num_threads(4)
    model = YOLO(f'yolov8{args.size}.pt')
    model.train(data=str(ROOT / 'data/dataset.yaml'), epochs=args.epochs,
                imgsz=416, batch=8, device=args.device, workers=0, cache=False,
                seed=42, deterministic=True, optimizer='AdamW', lr0=.001,
                lrf=.01, weight_decay=.0005, patience=8, warmup_epochs=2,
                hsv_h=.015, hsv_s=.7, hsv_v=.4, degrees=0., translate=.1,
                scale=.5, fliplr=.5, flipud=0., mosaic=1., mixup=0.,
                close_mosaic=3, amp=False, plots=True,
                project=str(ROOT / 'runs/train'), name=f'yolov8{args.size}',
                exist_ok=False)
    best = Path(model.trainer.best)
    shutil.copy2(best, ROOT / 'models' / f'yolov8{args.size}_best.pt')
    save_json(ROOT / 'evidence' / f'train_{args.size}.json',
              dict(run=str(best.parent.parent.relative_to(ROOT)), best_sha256=hashlib.file_digest(best.open('rb'), 'sha256').hexdigest(),
                   epochs_completed=model.trainer.epoch+1, args=model.trainer.args.__dict__))


def predict(args):
    from ultralytics import YOLO
    source = int(args.source) if args.source.isdecimal() else args.source
    # Streaming results must be consumed for videos and webcams.
    for _ in YOLO(args.weights).predict(source=source, stream=True, save=True, save_txt=True,
            save_conf=True, conf=args.conf, imgsz=416, device=args.device,
            project=str(ROOT / 'runs/predict'), name='inference', exist_ok=False):
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('prepare')
    p = sub.add_parser('train')
    p.add_argument('--size', choices=['n', 's'], default='n')
    p.add_argument('--epochs', type=int, default=20)
    p.add_argument('--device', default='0')
    p = sub.add_parser('predict')
    p.add_argument('--weights', default=str(ROOT / 'models/yolov8n_best.pt'))
    p.add_argument('--source', required=True)
    p.add_argument('--conf', type=float, default=.25)
    p.add_argument('--device', default='0')
    args = parser.parse_args()
    if args.command == 'prepare':
        prepare()
    elif args.command == 'train':
        train(args)
    else:
        predict(args)


if __name__ == '__main__':
    main()
