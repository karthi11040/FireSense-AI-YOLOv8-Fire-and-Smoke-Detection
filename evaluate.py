"""Evaluate both trained models; retain metrics, predictions and error examples."""
import argparse
from pathlib import Path
import json
from collections import defaultdict
from pipeline import ROOT, save_json, parse_label


def iou(a, b):
    intersection = max(0, min(a[2], b[2])-max(a[0], b[0])) * max(0, min(a[3], b[3])-max(a[1], b[1]))
    union = (a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - intersection
    return intersection / union if union else 0.


def match_predictions(gt, pred):
    """Confidence-ordered, class-aware one-to-one matching at IoU >= 0.5."""
    tp, fp, fn = [0, 0], [0, 0], [0, 0]
    used = set()
    for p in sorted(pred, key=lambda p: p[1], reverse=True):
        candidates = [(iou(p[2:], g[1:]), j) for j, g in enumerate(gt)
                      if j not in used and int(g[0]) == int(p[0])]
        overlap, index = max(candidates, default=(0., -1))
        cls = int(p[0])
        if overlap >= .5:
            tp[cls] += 1
            used.add(index)
        else:
            fp[cls] += 1
    for j, g in enumerate(gt):
        if j not in used:
            fn[int(g[0])] += 1
    return tp, fp, fn


def rates(tp, fp, fn):
    return dict(precision=tp/(tp+fp) if tp+fp else 0.,
                recall=tp/(tp+fn) if tp+fn else 0., tp=tp, fp=fp, fn=fn)


def fixed_predictions(records):
    by_image = defaultdict(list)
    for row in records:
        if row['score'] < .25:
            continue
        if row['category_id'] not in (1, 2):
            raise ValueError('Expected one-based custom-dataset categories 1=fire, 2=smoke')
        x, y, w, h = row['bbox']
        by_image[str(row['image_id'])].append([row['category_id']-1, row['score'], x, y, x+w, y+h])
    return by_image


def gallery(records, path, title):
    from PIL import Image, ImageDraw, ImageFont
    font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 15) if Path('C:/Windows/Fonts/arial.ttf').exists() else ImageFont.load_default()
    canvas = Image.new('RGB', (960, 290*len(records)+40), 'white')
    draw = ImageDraw.Draw(canvas)
    draw.text((12, 10), title+' | green=fire, blue=smoke', fill='black', font=font)
    for k, row in enumerate(records):
        for col, field in enumerate(['gt', 'pred']):
            with Image.open(row['image']) as source:
                w, h = source.size
                im = source.copy()
                im.thumbnail((470, 240))
            overlay = ImageDraw.Draw(im)
            for box in row[field]:
                cls = int(box[0])
                coords = box[1:] if field == 'gt' else box[2:]
                xy = [coords[0]*im.width/w, coords[1]*im.height/h, coords[2]*im.width/w, coords[3]*im.height/h]
                color = '#00d044' if cls == 0 else '#009dff'
                overlay.rectangle(xy, outline=color, width=3)
                label = ['fire', 'smoke'][cls] + (f' {box[1]:.2f}' if field == 'pred' else '')
                overlay.text((xy[0], max(0, xy[1]-17)), label, fill=color, font=font, stroke_width=1, stroke_fill='black')
            x, y = 10+col*480, 40+k*290
            text = ('Ground truth' if col == 0 else f'Prediction TP={sum(row["tp"])} FP={sum(row["fp"])} FN={sum(row["fn"])}')
            draw.text((x, y), text, fill='black', font=font)
            canvas.paste(im, (x, y+23))
            draw.text((x, y+270), Path(row['image']).name[:58], fill='black', font=font)
    canvas.save(path)


def evaluate(split, device):
    from ultralytics import YOLO
    import torch
    torch.set_num_threads(4)
    summaries = {}
    for size in ['n', 's']:
        model = YOLO(str(ROOT / f'models/yolov8{size}_best.pt'))
        dest = ROOT / f'runs/eval/{split}_yolov8{size}'
        metrics = model.val(data=str(ROOT / 'data/dataset.yaml'), split=split,
             imgsz=416, batch=8, device=device, workers=0, conf=.001, iou=.7,
             plots=True, save_json=True, project=str(dest.parent), name=dest.name,
             exist_ok=False, half=False)
        dest = Path(metrics.save_dir)
        summary = dict(map50=float(metrics.box.map50), map50_95=float(metrics.box.map),
                       run=str(dest.relative_to(ROOT)),
                       speed_ms=metrics.speed, parameters=sum(p.numel() for p in model.model.parameters()),
                       weights_mb=(ROOT / f'models/yolov8{size}_best.pt').stat().st_size/1e6,
                       native_best_f1_precision=float(metrics.box.mp), native_best_f1_recall=float(metrics.box.mr),
                       per_class={})
        for j, cls in enumerate(metrics.box.ap_class_index):
            summary['per_class'][model.names[int(cls)]] = dict(
                ap50=float(metrics.box.ap50[j]), ap50_95=float(metrics.box.ap[j]))
        if split == 'test':
            from PIL import Image
            totals = [[0, 0], [0, 0], [0, 0]]
            records = []
            predictions = fixed_predictions(json.loads((dest / 'predictions.json').read_text()))
            for p in sorted((ROOT / 'data/prepared/test/images').glob('*.jpg')):
                with Image.open(p) as image:
                    w, h = image.size
                labels = parse_label((ROOT / 'data/prepared/test/labels' / (p.stem+'.txt')).read_text())
                gt = [[c, (x-bw/2)*w, (y-bh/2)*h, (x+bw/2)*w, (y+bh/2)*h] for c,x,y,bw,bh in labels]
                pred = predictions.get(p.stem, [])
                tp, fp, fn = match_predictions(gt, pred)
                for accumulator, counts in zip(totals, [tp, fp, fn]):
                    for i in range(2):
                        accumulator[i] += counts[i]
                records.append(dict(image=str(p), gt=gt, pred=pred, tp=tp, fp=fp, fn=fn))
            summary['fixed_threshold'] = dict(confidence=.25, match_iou=.5, nms_iou=.7,
                 overall_micro=rates(*(sum(a) for a in totals)),
                 per_class={model.names[c]: rates(*(a[c] for a in totals)) for c in range(2)})
            failures = sorted((r for r in records if sum(r['fp'])+sum(r['fn'])>0),
                              key=lambda r: sum(r['fp'])+sum(r['fn']), reverse=True)
            successes = [r for r in records if sum(r['fp'])+sum(r['fn']) == 0 and sum(r['tp'])>0]
            save_json(dest / 'image_results.json', records)
            save_json(dest / 'failure_examples.json', failures[:10])
            if failures:
                gallery(failures[:3], dest / 'failures.jpg', f'YOLOv8{size}: highest object-error counts, confidence 0.25')
            if successes:
                # Evenly sample successful cases instead of repeatedly displaying the same adjacent frames.
                chosen = [successes[i] for i in sorted(set([0, len(successes)//2, len(successes)-1]))]
                gallery(chosen, dest / 'successes.jpg', f'YOLOv8{size}: successful test detections, confidence 0.25')
        summaries[size] = summary
        save_json(dest / 'metrics.json', summary)
    save_json(ROOT / f'evidence/{split}_metrics.json', summaries)
    if split == 'val':
        winner = max(summaries, key=lambda s: summaries[s]['map50_95'])
        save_json(ROOT / 'evidence/recommendation.json',
                  dict(size=winner, criterion='Highest validation mAP50-95; fixed before test evaluation',
                       threshold=.25, validation_map50_95=summaries[winner]['map50_95']))
    print(json.dumps(summaries, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--split', choices=['val', 'test'], default='test')
    parser.add_argument('--device', default='0')
    args = parser.parse_args()
    if args.split == 'test' and not (ROOT / 'evidence/recommendation.json').exists():
        raise SystemExit('Run --split val first to lock the recommendation before testing')
    evaluate(args.split, args.device)
