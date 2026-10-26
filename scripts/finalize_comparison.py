"""Preserve the completed comparison checkpoint after the user's speed request."""
from pathlib import Path
import csv
import hashlib
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline import ROOT, save_json


if __name__ == '__main__':
    import torch
    from ultralytics.utils.torch_utils import strip_optimizer
    from ultralytics.utils.plotting import plot_results
    run = ROOT / 'runs/train/yolov8s'
    checkpoint = torch.load(run / 'weights/best.pt', map_location='cpu', weights_only=False)
    last = torch.load(run / 'weights/last.pt', map_location='cpu', weights_only=False)
    rows = list(csv.DictReader((run / 'results.csv').open()))
    completed = int(rows[-1]['epoch'])
    assert last['epoch'] + 1 == completed, 'Checkpoint and completed-epoch CSV disagree'
    assert checkpoint['ema'] is not None and len(checkpoint['ema'].names) == 2
    target = ROOT / 'models/yolov8s_best.pt'
    strip_optimizer(run / 'weights/best.pt', s=str(target))
    plot_results(file=str(run / 'results.csv'))
    save_json(ROOT / 'evidence/train_s.json', dict(
        run=str(run.relative_to(ROOT)), epochs_completed=completed,
        best_epoch=int(checkpoint['epoch']) + 1,
        best_sha256=hashlib.file_digest(target.open('rb'), 'sha256').hexdigest(),
        args=last['train_args'],
        termination='User requested faster completion; retained latest completed checkpoint; partial next epoch discarded'))
    print(f'Finalized small comparison: {completed} completed epochs; best epoch {checkpoint["epoch"]+1}', flush=True)
