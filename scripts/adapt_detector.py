"""Add training-only close-up/portrait/lighting augmentation, then refine a candidate."""
import argparse
import json
import random
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline import ROOT, parse_label, save_json


def candidate_path(models, run_name):
    path = models/'yolov8n_domain.pt'
    if path.exists():
        path = models/f'{run_name}_candidate.pt'
    if path.exists():
        raise FileExistsError(f'Refusing to overwrite checkpoint: {path}')
    return path


def crop_labels(labels, bounds, dimensions):
    left, top, right, bottom = bounds
    w, h = dimensions
    result = []
    for cls, x, y, bw, bh in labels:
        x1, y1, x2, y2 = (x-bw/2)*w, (y-bh/2)*h, (x+bw/2)*w, (y+bh/2)*h
        a, b, c, d = max(x1,left), max(y1,top), min(x2,right), min(y2,bottom)
        if c <= a or d <= b or (c-a)*(d-b) < .15*(x2-x1)*(y2-y1):
            continue
        result.append([cls, ((a+c)/2-left)/(right-left), ((b+d)/2-top)/(bottom-top),
                       (c-a)/(right-left), (d-b)/(bottom-top)])
    return result


def prepare():
    import cv2
    import numpy as np
    import yaml
    rng = random.Random(42)
    base = ROOT / 'data/domain_augmented'
    (base/'images').mkdir(parents=True, exist_ok=True)
    (base/'labels').mkdir(exist_ok=True)
    images = sorted((ROOT/'data/prepared/train/images').glob('*.jpg'))
    candidates = []
    for path in images:
        labels = parse_label((ROOT/'data/prepared/train/labels'/f'{path.stem}.txt').read_text())
        fire = [b for b in labels if b[0] == 0]
        if fire:
            candidates.append((path, labels, max(fire, key=lambda b:b[3]*b[4])))
    rng.shuffle(candidates)
    generated = []
    provenance = []
    for i, (path, labels, fire) in enumerate(candidates[:600]):
        im = cv2.imread(str(path)); h, w = im.shape[:2]
        _, x, y, bw, bh = fire
        context = rng.uniform(.1,.3)
        bounds = (max(0,int((x-bw*(.5+context))*w)), max(0,int((y-bh*(.5+context))*h)),
                  min(w,int((x+bw*(.5+context))*w)+1), min(h,int((y+bh*(.5+context))*h)+1))
        left, top, right, bottom = bounds
        converted = crop_labels(labels, bounds, (w,h))
        if not any(b[0] == 0 for b in converted):
            continue
        crop = cv2.resize(im[top:bottom,left:right], (360,640))
        if i % 2 == 0:
            gains = np.array([rng.uniform(.45,.75),rng.uniform(.65,.95),rng.uniform(1.1,1.5)])
            crop = np.clip(crop.astype(np.float32)*gains,0,255).astype(np.uint8)
        target = base/'images'/f'portrait_{path.stem}.jpg'
        assert cv2.imwrite(str(target),crop)
        text = '\n'.join(' '.join(map(str, b)) for b in converted)+'\n'
        parse_label(text)
        (base/'labels'/f'{target.stem}.txt').write_text(text)
        generated.append(target)
        provenance.append(dict(source=str(path.relative_to(ROOT)),generated=str(target.relative_to(ROOT)),
                               bounds=bounds,red_light=i%2==0))
    train = base/'train.txt'
    train.write_text('\n'.join(str(p.resolve()) for p in images+generated)+'\n')
    config = dict(path=str((ROOT/'data/prepared').resolve()),train=str(train.resolve()),
                  val='val/images',test='test/images',names={0:'fire',1:'smoke'})
    (base/'dataset.yaml').write_text(yaml.safe_dump(config))
    save_json(ROOT/'evidence/user_video/augmentation_manifest.json',dict(
        original_training_images=len(images),generated=len(generated),seed=42,
        source_policy='Original training split only; user video and validation/test excluded',images=provenance))
    return base/'dataset.yaml'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--train',action='store_true')
    args = parser.parse_args()
    data = ROOT/'data/domain_augmented/dataset.yaml'
    # shortcut: reuse prepared variants; rerun without --train after changing source data.
    if not args.train or not data.exists():
        data = prepare()
    print(f'Training data: {data}',flush=True)
    if args.train:
        import shutil
        import torch
        from ultralytics import YOLO
        torch.set_num_threads(4)
        model = YOLO(str(ROOT/'models/yolov8n_refined.pt'))
        model.train(data=str(data),epochs=3,imgsz=416,batch=16,device='0',workers=0,
            cache=False,seed=42,deterministic=True,optimizer='AdamW',lr0=.0002,lrf=.1,
            weight_decay=.0005,freeze=4,warmup_epochs=1,patience=3,mosaic=0.,mixup=0.,
            scale=.15,translate=.05,fliplr=.5,hsv_h=.005,hsv_s=.2,hsv_v=.2,
            amp=False,plots=True,project=str(ROOT/'runs/optimization'),name='domain_adaptation',exist_ok=False)
        candidate = candidate_path(ROOT/'models',Path(model.trainer.save_dir).name)
        shutil.copy2(model.trainer.best,candidate)
        print(f'Candidate weights: {candidate}',flush=True)
        save_json(ROOT/'evidence/user_video/adaptation_training.json',dict(
            run=str(model.trainer.save_dir),candidate_weights=str(candidate),
            epochs_completed=model.trainer.epoch+1,args=vars(model.trainer.args)))
