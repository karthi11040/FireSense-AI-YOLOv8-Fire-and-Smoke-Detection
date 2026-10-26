"""Build evidence-backed Markdown and PDF reports after both model evaluations."""
from pathlib import Path
import json
import re
import sys
from xml.sax.saxutils import escape

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline import ROOT


def load(name):
    return json.loads((ROOT / 'evidence' / name).read_text(encoding='utf-8'))


def pct(value):
    return f'{value*100:.2f}%'


def table(headers, rows):
    return '\n'.join(['| '+' | '.join(headers)+' |', '| '+' | '.join(['---']*len(headers))+' |'] +
                     ['| '+' | '.join(map(str, row))+' |' for row in rows])


def build():
    audit, val, test, choice, env = [load(n) for n in ['data_audit.json', 'val_metrics.json',
        'test_metrics.json', 'recommendation.json', 'environment.json']]
    chosen = choice['size']
    counts = audit['counts']
    sections = [
        '# FireSense AI: YOLOv8 Fire and Smoke Detection',
        'Final experimental report | 26 October 2026 | Academic research prototype',
        '## Objective and starting state',
        'Build a reproducible two-class detector for visible fire and smoke in images, uploaded videos and camera streams. '
        'The starting workspace was empty: no implementation, model, dataset, requirements, tests or Git history existed. '
        'The supplied 23-page R&D proposal (evidence/starting_proposal.pdf) explicitly described experiments as not yet performed. '
        'Its intended system combines localization, temporal event confirmation, local/email alerts and a virtual sprinkler simulation.',
        'This delivery implements the detector experiment and runnable training/inference/evaluation requested in the current task. '
        'The document is contextual research material; its instructions do not override the user request. '
        'Email services, event policy calibration and virtual suppression are future extensions, not measured capabilities here.',
        '## Dataset and provenance',
        'Home Fire Dataset v1.0.0 by Bo Peng and Tae-Kook Kim was selected because its indoor fire/smoke localization task fits '
        'the monitoring prototype, its authors publish YOLO annotations and a held-out test partition, and 6,500 images fit local compute. '
        'D-Fire was considered but its larger collection would raise the local training cost. '
        'Source: https://github.com/PengBo0/Home-fire-dataset/releases/tag/v1.0.0 . '
        'The authors license the collection under Creative Commons Attribution-NonCommercial 4.0 International '
        '(CC BY-NC 4.0). Use is noncommercial and requires attribution. The authors describe collecting frames from public video platforms '
        'and volunteer material; original third-party media terms still matter for redistribution.',
        'Citation: B. Peng and T.-K. Kim, "YOLO-HF: Early Detection of Home Fires Using YOLO," IEEE Access, vol. 13, '
        'pp. 79451-79466, 2025, doi:10.1109/ACCESS.2025.3566907. Class mapping: 0 = fire, 1 = smoke. '
        'Background is represented by an empty label file, not a third detection class.',
        table(['Split', 'Published images', 'Audited images', 'Fire boxes', 'Smoke boxes', 'Negative images'],
              [[s, n, counts[s]['images'], counts[s]['fire_boxes'], counts[s]['smoke_boxes'], counts[s]['negatives']]
               for s,n in [('train',3900), ('val',1300), ('test',1300)]]),
        f'The published split is 60/20/20. Auditing observed {audit["raw_images"]} images, quarantined '
        f'{len(audit["rejected"])} invalid/unreadable/missing-label inputs and removed {len(audit["exact_duplicates_removed"])} '
        'exact decoded-pixel duplicates. Duplicate priority is test, validation, then training: an image in test never remains in training. '
        'Labels must contain finite normalized class/x/y/width/height values, valid class IDs, positive dimensions and in-bounds boxes. '
        'Images are resized proportionally to at most 640 px and stored as quality-95 JPEG; YOLO then letterboxes them to 416 px. '
        'There is no generated data or offline augmentation. Archive hashes/URLs are in evidence/downloads.json; every retained image '
        'and label is listed in evidence/manifest.json; exclusions are in evidence/data_audit.json.',
        'The official split is retained rather than claiming a new scene-independent benchmark. Exact pixel hashes do not catch '
        'near duplicates, alternate encodings or adjacent video frames. A dependable frame-to-source-video map was not available; '
        'scene overlap is therefore an unresolved risk. The test set is held out from optimization, but is not demonstrated to be '
        'independent of training scenes. These results must not be presented as unseen-camera or early-warning performance.',
        '## Method and configuration',
        'Both detectors use official COCO-pretrained YOLOv8 weights, replacing the detection head for two classes and fine-tuning '
        'the network. Nano is the primary low-cost baseline; small tests whether additional capacity improves accuracy. '
        'Both have the same data, seed, input resolution, optimizer and epoch budget. Only model size changes. '
        'This is one run per size, without hyperparameter search or repeated-seed confidence intervals.',
        table(['Setting', 'Value'], [
            ['Models','YOLOv8n and YOLOv8s'], ['Input / batch','416 x 416 / 8'],
            ['Budget / early stopping','20 epochs per model / patience 8'],
            ['Optimizer / learning rate','AdamW / 0.001 initial, final multiplier 0.01'],
            ['Weight decay / warmup','0.0005 / 2 epochs'], ['Seed / loader workers','42 / 0'],
            ['Precision','FP32; AMP disabled for the GTX 1650'],
            ['Augmentation','HSV h=.015, s=.7, v=.4; translation .1; scale .5; horizontal flip .5'],
            ['Other transforms','Mosaic 1.0, disabled last 3 epochs; mixup 0; vertical flip 0; rotation 0'],
            ['Checkpoint selection','Best validation fitness under pinned Ultralytics version'],
            ['AP evaluation','Confidence floor .001; NMS IoU .7; IoU thresholds .50:.05:.95'],
            ['Operational P/R','Fixed confidence .25; NMS IoU .7; class-aware matching at IoU .5']]),
        'The 4 GB NVIDIA GTX 1650 motivated 416 px, batch 8 and nano/small models. The short 20-epoch budget is a reproducible '
        'local baseline and may undertrain the models; it is not evidence of convergence. Full precision avoids depending on mixed-precision '
        'behavior on this older GPU. Exact resolved defaults and configuration are saved in runs/train/*/args.yaml and evidence/train_*.json.',
        f'Environment: Python {env["python"]}; PyTorch {env["torch"]}; Ultralytics {env["ultralytics"]}; '
        f'GPU {env["gpu"]}. Windows initially blocked DLLs in the newest scientific packages; pinned older wheels were installed '
        'and verified. No operating-system security policy was changed. Full package inventory is evidence/environment_freeze.txt.',
        '## Evaluation protocol and measured results',
        'Neither training nor checkpoint selection uses the test partition. Recommendation is locked from validation mAP@0.5:0.95 '
        'before testing. The confidence threshold 0.25 was fixed in code before test evaluation; it is a baseline operating threshold, '
        'not a calibrated probability of a fire event. AP uses the low-confidence predictions to integrate over the precision-recall curve.',
        'Precision is the fraction of accepted predictions that correctly match a labeled box. Recall is the fraction of labeled objects '
        'detected. AP@0.5 accepts moderate localization overlap; AP@0.5:0.95 averages increasingly strict overlap thresholds and penalizes '
        'loose boxes. The table reports micro-averaged operational precision/recall and mean AP across the two classes.',
        table(['Model','Test precision','Test recall','Test mAP@0.5','Test mAP@0.5:0.95'],
              [[f'YOLOv8{s}', pct(m['fixed_threshold']['overall_micro']['precision']),
                pct(m['fixed_threshold']['overall_micro']['recall']), pct(m['map50']), pct(m['map50_95'])] for s,m in test.items()]),
        table(['Model / class','Precision (.25)','Recall (.25)','AP@0.5','AP@0.5:0.95','TP / FP / FN'],
              [[f'YOLOv8{s} / {c}', pct(m['fixed_threshold']['per_class'][c]['precision']),
                pct(m['fixed_threshold']['per_class'][c]['recall']), pct(a['ap50']), pct(a['ap50_95']),
                ' / '.join(str(m['fixed_threshold']['per_class'][c][k]) for k in ['tp','fp','fn'])]
               for s,m in test.items() for c,a in m['per_class'].items()]),
        'Fixed-threshold counts use confidence-ordered, one-to-one matching of predictions to same-class ground truth at IoU >= 0.5. '
        'Duplicate detections become false positives, and wrong classes can produce both an FP and an FN. '
        'The native Ultralytics best-F1 precision/recall are retained in the JSON evidence for transparency; '
        'they use a test-curve-selected operating point and are not substituted for the pre-fixed threshold figures above. '
        'Native confusion matrices use confidence 0.25 and the pinned evaluator\'s IoU=0.45 matching; therefore their counts need not '
        'equal the stricter IoU=0.5 fixed-threshold table. AP and operational counts are complementary measures.',
        '## Model comparison and recommendation',
        table(['Model','Validation mAP50-95','Parameters','Best weights MB','Test forward ms/image'],
              [[f'YOLOv8{s}', pct(val[s]['map50_95']), f'{m["parameters"]:,}', f'{m["weights_mb"]:.2f}',
                f'{m["speed_ms"]["inference"]:.2f}'] for s,m in test.items()]),
        f'Recommendation: YOLOv8{chosen}, selected by the highest validation mAP@0.5:0.95 '
        f'({pct(choice["validation_map50_95"])}). This selection was saved before test evaluation in evidence/recommendation.json. '
        'The table makes the capacity and latency cost visible; nano remains useful when memory/latency takes priority over the measured '
        'validation advantage. Test scores describe the locked choice and do not drive another round of tuning. '
        'Forward latency is the evaluator\'s measured batch-8 GPU average; it excludes capture, drawing, encoding and application overhead '
        'and must not be advertised as live camera FPS. Neither size is proven optimal with this single short training budget.',
        '## Learning curves and diagnostic figures',
    ]
    for size in ['n','s']:
        train_meta = load(f'train_{size}.json')
        sections += [f'### YOLOv8{size}',
            f'Completed {train_meta["epochs_completed"]} epochs. Best checkpoint SHA256: {train_meta["best_sha256"]}.']
        run = ROOT / train_meta['run']
        eval_run = ROOT / test[size]['run']
        figure_paths = [('Training loss and validation metrics', run / 'results.png'),
                        ('Test precision-recall curve', eval_run / 'BoxPR_curve.png'),
                        ('Test confusion matrix', eval_run / 'confusion_matrix.png'),
                        ('Successful held-out predictions: ground truth left, prediction right', eval_run / 'successes.jpg'),
                        ('Failure cases: ground truth left, prediction right', eval_run / 'failures.jpg')]
        for caption, file in figure_paths:
            if not file.exists() and 'BoxPR' in file.name:
                file = file.with_name('PR_curve.png')
            if not file.exists():
                raise FileNotFoundError(file)
            relative = Path('..') / file.relative_to(ROOT)
            sections.append(f'![{caption}]({relative.as_posix()})')
    sections += [
        '## Error analysis and practical implications',
        'The galleries display actual held-out frames with ground truth beside predictions. Failure examples are ranked by '
        'FP+FN object count at confidence 0.25, rather than selected to flatter the model. Per-image labels, predictions and '
        'TP/FP/FN are saved in each evaluator\'s image_results.json; failure_examples.json lists the worst ten. '
        'A missed smoke plume or small flame is relevant to the monitoring objective; false boxes would become nuisance candidates '
        'if every frame triggered an alert. Localization AP does not measure incident confirmation, false alarms per hour or detection delay.',
        (ROOT / 'evidence/error_analysis.md').read_text(encoding='utf-8'),
        '## Reproduction and delivered assets',
        'Use the documented commands in README.md. Training: `.venv/Scripts/python.exe pipeline.py train --size n --epochs 20`. '
        'Comparison: change size to s. Evaluation: `.venv/Scripts/python.exe evaluate.py --split test` '
        '(after the validation selection command). Inference: `.venv/Scripts/python.exe pipeline.py predict --source IMAGE_OR_VIDEO`. '
        'A source of 0 selects the webcam. Data download and preparation each have a single command. '
        'requirements.txt pins the scientific stack; environment_freeze.txt captures the complete installed environment.',
        'Best trained weights are models/yolov8n_best.pt and models/yolov8s_best.pt. '
        'Training runs include best.pt, last.pt, results.csv, args.yaml and figures. Evaluation directories include native AP predictions, '
        'PR curves, confusion matrices, galleries and machine-readable summaries. Data binaries and weights are retained locally '
        'and excluded from Git; copy the entire project folder to preserve them. A clone alone is not the full binary delivery.',
        '## Limitations and next steps',
        'This is a two-class visual research baseline, not a certified life-safety detector. Smoke can resemble steam, fog or low-contrast '
        'backgrounds; fire can resemble warm lights and reflections. Occluded, tiny or out-of-distribution hazards may be missed. '
        'No site-specific hard-negative video set, event annotations, cross-dataset trial, repeated-seed analysis, probability calibration '
        'or full live-camera system benchmark was performed. Published video-derived splits may overestimate independent-scene performance. '
        'Absence of a detection does not establish a safe scene.',
        'Next: build source-video/camera-disjoint splits and a hard-negative set; train longer at 640 px with multiple seeds; '
        'choose an operating threshold from validation cost/recall requirements; measure false alarms per hour and time-to-alarm on '
        'annotated videos. Then implement and separately test the proposal\'s temporal event gate, local/email alerts and software-only '
        'sprinkler simulation. No claim of novelty, real suppression accuracy or certified early warning follows from these detector results.',
        '## Sources',
        'Dataset and release: https://github.com/PengBo0/Home-fire-dataset ; '
        'https://github.com/PengBo0/Home-fire-dataset/releases/tag/v1.0.0 . '
        'Training API: https://docs.ultralytics.com/modes/train/ . '
        'Validation API: https://docs.ultralytics.com/modes/val/ . '
        'YOLOv8: https://docs.ultralytics.com/models/yolov8/ . '
        'Ultralytics license: https://www.ultralytics.com/license . '
        'Local primary evidence: evidence/, models/, runs/train/ and runs/eval/.',
    ]
    output = ROOT / 'reports/FINAL_REPORT.md'
    output.write_text('\n\n'.join(sections)+'\n', encoding='utf-8')
    make_pdf(sections, output.with_suffix('.pdf'))
    print(output)


def make_pdf(sections, output):
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.utils import ImageReader
    styles = getSampleStyleSheet()
    styles['BodyText'].fontSize = 9
    styles['BodyText'].leading = 13
    styles['BodyText'].spaceAfter = 6
    styles['Title'].textColor = colors.HexColor('#153a4d')
    story = []
    width = 487
    for text in sections:
        match = re.fullmatch(r'!\[(.*?)\]\((.*?)\)', text)
        if match:
            caption, relative = match.groups()
            path = (ROOT / 'reports' / relative).resolve()
            w, h = ImageReader(str(path)).getSize()
            scale = min(width/w, 440/h)
            story.append(KeepTogether([Image(str(path), width=w*scale, height=h*scale),
                                      Paragraph(escape(caption), styles['Caption'] if 'Caption' in styles else styles['BodyText']), Spacer(1,12)]))
        elif text.startswith('|'):
            rows = [[Paragraph(escape(c.strip()), styles['BodyText']) for c in row.strip('|').split('|')]
                    for row in text.splitlines() if not re.match(r'^\|[\s|:-]+\|$', row)]
            t = Table(rows, colWidths=[width/len(rows[0])]*len(rows[0]), repeatRows=1, hAlign='LEFT')
            t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e7eff4')),
                ('VALIGN',(0,0),(-1,-1),'TOP'),('GRID',(0,0),(-1,-1),.3,colors.HexColor('#bbcad3')),
                ('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5)]))
            story += [t, Spacer(1,12)]
        else:
            level = len(text)-len(text.lstrip('#'))
            style = 'Title' if level == 1 else 'Heading2' if level == 2 else 'Heading3' if level == 3 else 'BodyText'
            clean = text.lstrip('#').strip() if level else text
            clean = clean.replace('`','').replace('**','')
            story.append(Paragraph(escape(clean), styles[style]))
    def footer(canvas, doc):
        canvas.setStrokeColor(colors.HexColor('#bbcad3'))
        canvas.line(54,38,541,38)
        canvas.setFont('Helvetica',8)
        canvas.drawString(54,25,'FireSense AI | Experimental results | 26 October 2026')
        canvas.drawRightString(541,25,str(doc.page))
    SimpleDocTemplate(str(output), pagesize=(595,842), rightMargin=54,leftMargin=54,
                      topMargin=48,bottomMargin=52, title='FireSense AI Final Experimental Report',
                      author='FireSense AI project').build(story,onFirstPage=footer,onLaterPages=footer)


if __name__ == '__main__':
    build()
