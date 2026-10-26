"""Validate inference resolution and confidence; never tune on the test split."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline import ROOT, parse_label, save_json
from evaluate import fixed_predictions, match_predictions, rates


def threshold_metrics(predictions_path, split):
    from PIL import Image
    records = json.loads(Path(predictions_path).read_text())
    ground_truth = {}
    for path in sorted((ROOT / f'data/prepared/{split}/images').glob('*.jpg')):
        with Image.open(path) as image:
            w, h = image.size
        labels = parse_label((ROOT / f'data/prepared/{split}/labels/{path.stem}.txt').read_text())
        ground_truth[path.stem] = [[c, (x-bw/2)*w, (y-bh/2)*h, (x+bw/2)*w, (y+bh/2)*h]
                                  for c, x, y, bw, bh in labels]
    output = {}
    for threshold in [.25, .5, .75, .9]:
        predictions = fixed_predictions(records, threshold)
        totals = [[0, 0], [0, 0], [0, 0]]
        for key, gt in ground_truth.items():
            for total, counts in zip(totals, match_predictions(gt, predictions.get(key, []))):
                for cls in range(2):
                    total[cls] += counts[cls]
        output[str(threshold)] = dict(overall=rates(*(sum(a) for a in totals)),
            per_class={name: rates(*(a[c] for a in totals)) for c, name in enumerate(['fire', 'smoke'])})
    return output


def run(weights, size, split, name):
    import torch
    from ultralytics import YOLO
    torch.set_num_threads(2)
    metrics = YOLO(str(weights)).val(data=str(ROOT / 'data/dataset.yaml'), split=split,
        imgsz=size, batch=4, device='0', workers=0, conf=.001, iou=.7,
        plots=True, save_json=True, half=False,
        project=str(ROOT / 'runs/optimization'), name=name, exist_ok=False)
    result = dict(weights=str(weights), imgsz=size, split=split, run=str(metrics.save_dir),
        map50=float(metrics.box.map50), map50_95=float(metrics.box.map), speed_ms=metrics.speed,
        per_class={['fire', 'smoke'][int(c)]: dict(ap50=float(metrics.box.ap50[j]),
            ap50_95=float(metrics.box.ap[j])) for j, c in enumerate(metrics.box.ap_class_index)})
    result['thresholds'] = threshold_metrics(Path(metrics.save_dir) / 'predictions.json', split)
    save_json(Path(metrics.save_dir) / 'optimization_metrics.json', result)
    print(json.dumps(result), flush=True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--weights', default=str(ROOT / 'models/yolov8n_best.pt'))
    parser.add_argument('--sizes', type=int, nargs='+', default=[512, 640])
    parser.add_argument('--split', choices=['val', 'test'], default='val')
    parser.add_argument('--finetune', action='store_true', help='Four-epoch head/neck refinement; preserve original weights')
    args = parser.parse_args()
    if args.finetune:
        import shutil
        import torch
        from ultralytics import YOLO
        torch.set_num_threads(4)
        model = YOLO(args.weights)
        model.train(data=str(ROOT / 'data/dataset.yaml'), epochs=4, imgsz=416,
            batch=16, device='0', workers=0, cache=False, seed=42, deterministic=True,
            optimizer='AdamW', lr0=.00015, lrf=.1, weight_decay=.0005,
            freeze=10, warmup_epochs=1, patience=4, mosaic=0., mixup=0.,
            scale=.2, translate=.05, fliplr=.5, hsv_h=.015, hsv_s=.4, hsv_v=.3,
            amp=False, plots=True, project=str(ROOT / 'runs/optimization'),
            name='nano_refinement', exist_ok=False)
        args.weights = str(ROOT / 'models/yolov8n_refined.pt')
        shutil.copy2(model.trainer.best, args.weights)
        save_json(ROOT / 'evidence/train_refinement.json', dict(
            run=str(model.trainer.save_dir), epochs_completed=model.trainer.epoch+1,
            args=vars(model.trainer.args)))
        args.sizes = [416]
    results = [run(args.weights, size, args.split, f'{args.split}_{Path(args.weights).stem}_{size}')
               for size in args.sizes]
    output = ROOT / f'evidence/optimization_{args.split}_{Path(args.weights).stem}.json'
    prior = json.loads(output.read_text()) if output.exists() else []
    results = [r for r in prior if r['imgsz'] not in args.sizes] + results
    save_json(output, results)
