"""Build the confidence/refinement evidence report from saved experiment outputs."""
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline import ROOT, save_json


def load(relative):
    return json.loads((ROOT / relative).read_text())


def pct(value):
    return f'{value*100:.2f}%'


if __name__ == '__main__':
    baseline = load('evidence/val_metrics.json')['n']
    baseline['imgsz'] = 416
    baseline['thresholds'] = load('evidence/optimization_baseline_thresholds.json')
    candidates = load('evidence/optimization_val_yolov8n_best.json')
    baseline = next((r for r in candidates if r['imgsz'] == 416), baseline)
    refined = load('evidence/optimization_val_yolov8n_refined.json')[0]
    selected = 'refined' if (refined['map50_95'] > baseline['map50_95'] and
        refined['thresholds']['0.5']['overall']['precision'] >= .9) else 'original'
    selection = dict(selected=selected, imgsz=416, default_confidence=.5,
        strict_confidence=.9, criterion='Validation mAP50-95 improvement and precision at 0.50 >= 90%; never select using test',
        weights=f'models/yolov8n_{"refined" if selected == "refined" else "best"}.pt')
    selection['sha256'] = hashlib.sha256((ROOT / selection['weights']).read_bytes()).hexdigest()
    selection['model'] = 'YOLOv8 nano (refined)' if selected == 'refined' else 'YOLOv8 nano'
    test_path = ROOT / 'evidence/optimization_test_yolov8n_refined.json'
    selection['testMap50'] = (json.loads(test_path.read_text())[0]['map50']*100 if test_path.exists() else None) if selected == 'refined' else 82.02
    save_json(ROOT / 'evidence/optimization_selection.json', selection)
    rows = [('Original', baseline)] + [('Larger input', r) for r in candidates if r['imgsz'] != 416] + [('Four-epoch refinement', refined)]
    text = '# Detector optimization and confidence audit\n\n'
    text += ('A confidence score is a per-box model output, not proof of correctness. '
        'Scores have not been rescaled, rounded up to a floor or fabricated. '
        'The 90%+ control only filters boxes. Higher thresholds can hide real hazards.\n\n')
    text += ('## Validation comparison\n\nAll configurations use the same 1,297 validation images. '
        'Selection uses validation only. NMS IoU is 0.70; fixed-threshold matching '
        'requires the correct class and a one-to-one IoU >= 0.50.\n\n')
    text += '| Configuration | Input | mAP50 | mAP50–95 | Precision at 0.50 | Recall at 0.50 |\n|---|---:|---:|---:|---:|---:|\n'
    for name, row in rows:
        metric = row['thresholds']['0.5']['overall']
        text += f'| {name} | {row["imgsz"]} | {pct(row["map50"])} | {pct(row["map50_95"])} | {pct(metric["precision"])} | {pct(metric["recall"])} |\n'
    text += f'\nSelected checkpoint: **{selection["weights"]}** at 416 pixels. '
    text += selection['criterion'] + '. SHA256: `' + selection['sha256'] + '`.\n\n'
    text += ('## Training configuration\n\nWarm start from the original 20-epoch nano checkpoint; '
        '4 additional epochs on all 3,873 training images, 416 pixels, batch 16, '
        'AdamW lr0=0.00015, lrf=0.1, weight decay=0.0005, warmup 1 epoch, seed 42, '
        'deterministic execution, FP32 on GTX 1650. Freeze backbone layers 0–9; '
        'train neck/head. Mosaic/mixup disabled; scale=0.2, translate=0.05, '
        'fliplr=0.5, HSV h/s/v=0.015/0.4/0.3. Other settings are recorded in the '
        'run args.yaml. Select the best epoch by native validation fitness. '
        'An initial batch-4 attempt was stopped during its first epoch for throughput; '
        'it did not supply a checkpoint. Original weights are preserved.\n\n')
    text += '## Score thresholds on the existing test set\n\n'
    text += ('The test set has 1,295 images and 1,581 labeled objects. It was already '
        'evaluated in the original project. This follow-up is a reused benchmark, '
        'not a new independent generalization study. No test results select the checkpoint.\n\n')
    original_test_path = ROOT / 'evidence/optimization_test_yolov8n_best.json'
    original_test = json.loads(original_test_path.read_text())[0] if original_test_path.exists() else load('evidence/test_metrics.json')['n']
    original_thresholds = original_test.get('thresholds', load('evidence/optimization_original_test_thresholds.json'))
    tests = [('Original', original_thresholds)]
    path = ROOT / 'evidence/optimization_test_yolov8n_refined.json'
    if path.exists():
        refined_test = json.loads(path.read_text())[0]
        tests.append(('Refined', refined_test['thresholds']))
        text += (f'Refined test mAP50: **{pct(refined_test["map50"])}**; '
                 f'mAP50–95: **{pct(refined_test["map50_95"])}**. '
                 f'Original test values were {pct(original_test["map50"])} and {pct(original_test["map50_95"])}.\n\n')
    text += '| Checkpoint | Min score | Precision | Recall | TP | FP | Missed objects |\n|---|---:|---:|---:|---:|---:|---:|\n'
    for name, thresholds in tests:
        for threshold in ['0.25', '0.5', '0.9']:
            m = thresholds[threshold]['overall']
            text += f'| {name} | {threshold} | {pct(m["precision"])} | {pct(m["recall"])} | {m["tp"]} | {m["fp"]} | {m["fn"]} |\n'
    text += '\nPer-class results at the recommended 0.50 threshold:\n\n| Checkpoint | Class | Precision | Recall |\n|---|---|---:|---:|\n'
    for name, thresholds in tests:
        for cls, metric in thresholds['0.5']['per_class'].items():
            text += f'| {name} | {cls} | {pct(metric["precision"])} | {pct(metric["recall"])} |\n'
    if len(tests) == 2:
        before, after = tests[0][1]['0.5']['overall'], tests[1][1]['0.5']['overall']
        text += (f'\nAt 0.50, precision changes from {pct(before["precision"])} to '
                 f'{pct(after["precision"])}, while recall changes from {pct(before["recall"])} '
                 f'to {pct(after["recall"])}. Refinement improves recall/localization with '
                 'a small precision tradeoff; it does not uniformly improve every class or image.\n')
    if path.exists():
        import shutil
        figures = ROOT / 'reports/optimization_figures'
        figures.mkdir(exist_ok=True)
        for name in ['BoxPR_curve.png', 'confusion_matrix.png']:
            shutil.copy2(Path(refined_test['run']) / name, figures / name)
        text += '\n![Refined test precision–recall curve](optimization_figures/BoxPR_curve.png)\n\n![Refined test confusion matrix from native validator](optimization_figures/confusion_matrix.png)\n\nThe native confusion matrix uses validator settings; fixed-threshold counts in the tables are computed separately.\n'
    text += ('\n100% observed precision at 0.90 is based on very few retained detections, '
        'with most objects missed. It does not mean perfect safety or accuracy. '
        'Use 0.50 as the default for fewer false detections; use 0.25 when recall matters '
        'more. The 90%+ filter is available explicitly, with a missed-detection warning.\n\n')
    text += ('## Reproduction and evidence\n\n'
        '```powershell\n.venv/Scripts/python.exe scripts/optimize_detector.py\n'
        '.venv/Scripts/python.exe scripts/optimize_detector.py --finetune\n'
        '.venv/Scripts/python.exe scripts/report_optimization.py\n```\n\n'
        'Only after the validation selection is locked, evaluate the refined checkpoint '
        'with `scripts/optimize_detector.py --weights models/yolov8n_refined.pt --sizes 416 --split test`. '
        'Rebuild this report afterward. Runs are uniquely named on repeats. '
        'Native curves, confusion matrices and prediction JSON are under runs/optimization; '
        'summary JSON and logs are under evidence/optimization_*. '
        'Original benchmark and data licensing remain in FINAL_REPORT.md.\n\n'
        'No probability calibration, deployment-specific camera validation or independent '
        'incident-video safety testing was performed. Smoke and small/obscured objects '
        'remain challenging. Further improvement needs deployment-like labeled examples '
        'and hard negatives, not a higher displayed score.\n\n'
        'The included sample image still receives a raw fire score around 77% after refinement; '
        'at 0.90 it has no retained box. This is expected filtering, not evidence that the scene is safe.\n\n'
        'Metric definitions: [Ultralytics metrics](https://docs.ultralytics.com/guides/yolo-performance-metrics/). '
        'Threshold behavior: [Ultralytics predict settings](https://docs.ultralytics.com/modes/predict/).\n')
    (ROOT / 'reports/OPTIMIZATION_REPORT.md').write_text(text, encoding='utf-8')
    print(json.dumps(selection, indent=2))
