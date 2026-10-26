# FireSense AI

YOLOv8 fire/smoke object detection research pipeline. See `reports/FINAL_REPORT.md`
for the measured results and limitations once the experiment completes.

## Frontend and live virtual simulation

The trained weights are already present in this workspace. Start the dashboard:

```powershell
cd "D:\fire ai"
.venv/Scripts/python.exe dashboard.py
```

Open **http://localhost:8765** in Chrome or Edge. No additional packages or training
are needed. The page opens while the detector loads; wait for **Detector ready**
before starting real inference. **Run simulation demo** works immediately.

- **Live camera:** click Start camera and grant browser permission. Stop releases
  the camera. If the embedded preview cannot access it, open the URL in Chrome/Edge.
- **Video file:** choose a browser-supported video (e.g. H.264 MP4 or WebM), then
  Play & detect. The browser decodes the video; only sampled JPEG frames go to
  the local model. Overlays represent the latest analyzed frame, not object tracking.
- **Image:** choose a JPEG, PNG or WebP, then Analyze image; Try sample image uses
  the included Home Fire test image. A still image cannot confirm a temporal event.
- **Virtual response:** 3 fire-positive samples in the last 5 analyzed frames latch
  one incident. Automatic mode opens virtual water. Smoke alone does not open it.
  Toggle virtual water manually, or Reset session to clear the incident.
- **Demo:** detections and confidence values are scripted and clearly labeled.
  Actual camera/video/image modes use the trained YOLOv8 nano checkpoint.
- **Export log:** downloads the current browser session's event JSON with incident
  IDs, timestamps and source. Frames are processed in memory and are not written
  to disk by the dashboard. Exporting events is a user action.

The simulation is an illustrative animation, not a fire-severity estimator or a
physical suppression model. Intensity is 0–100 arbitrary units: visible-fire
samples add 4 AU/s and virtual water removes 16 AU/s, clamped to the range.
Its clock pauses when monitoring stops. Confirmed incidents remain latched until
reset; an ended/disconnected source is reported as stopped/error, never as safe.
The 3-of-5 policy is a prototype and has not been calibrated on event-labeled video.
No physical sprinkler, email provider or alarm hardware is connected.

Use `--device cpu` if CUDA is unavailable, or `--port 8766` if 8765 is occupied.
The server binds only to 127.0.0.1 and serves an explicit asset allowlist. It is a
local desktop prototype, not a public hosting server. Press Ctrl+C in its terminal
to shut it down. The benchmark report describes the detector experiment before
this UI extension; adding the simulation does not change its measured model results.

Dashboard checks: Python tests include image validation and localhost-origin
restrictions. `node --test web/simulation.test.mjs` checks the event gate and toy
dynamics. Optional Playwright browser QA is in `scripts/test_dashboard.cjs`;
set `PLAYWRIGHT_MODULE` to an installed Playwright module if needed.

## Setup (Windows PowerShell, Python 3.12)

```powershell
py -3.12 -m venv .venv
.venv/Scripts/python.exe -m pip install torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cu121
.venv/Scripts/python.exe -m pip install -r requirements.txt
```

If Python 3.12 is not registered with `py`, use its executable path. The supplied local
`.venv` uses the Codex bundled Python 3.12 runtime. CUDA requires a compatible NVIDIA
GPU/driver. Pass `--device cpu` to training, evaluation or prediction for CPU execution.
Never load untrusted `.pt` files: PyTorch checkpoints may contain executable pickle data.

## Commands

Run from the project root. Data and existing weights are already present after the
delivered experiment; the download/prepare commands are for reproduction.

```powershell
# Download the authors' full v1.0.0 release, verify ZIP paths, extract, then audit.
.venv/Scripts/python.exe scripts/download_data.py
.venv/Scripts/python.exe pipeline.py prepare

# Each model trains with one command. Uses a fresh run directory on repeats.
.venv/Scripts/python.exe pipeline.py train --size n --epochs 20
.venv/Scripts/python.exe pipeline.py train --size s --epochs 20

# Resume after an interruption; preserves the checkpoint's original epoch budget.
.venv/Scripts/python.exe pipeline.py train --size s --resume runs/train/yolov8s/weights/last.pt

# Select recommendation using validation only, then evaluate both on held-out test.
.venv/Scripts/python.exe evaluate.py --split val
.venv/Scripts/python.exe evaluate.py --split test

# Image, image folder, video file, or webcam index (0).
.venv/Scripts/python.exe pipeline.py predict --source data/prepared/test/images
.venv/Scripts/python.exe pipeline.py predict --source path/to/video.mp4
.venv/Scripts/python.exe pipeline.py predict --source 0

# Tests and regenerated report (requires completed experiment evidence).
.venv/Scripts/python.exe -m unittest discover -s tests
.venv/Scripts/python.exe scripts/build_report.py
```

Inference defaults to nano weights. To use the validation-recommended model, pass
`--weights models/yolov8s_best.pt` if the report recommends small. Annotated media
and normalized YOLO detection text (including confidence) go to `runs/predict/`.
Video uses streaming inference; webcam processing ends with Ctrl+C. No camera is
assumed to be attached.

## Outputs and reproducibility

- `models/yolov8{n,s}_best.pt`: fine-tuned checkpoints, not the original COCO weights.
- `runs/train/`: best/last weights, epoch CSV, settings YAML and learning curves.
- `runs/eval/`: test/validation PR curves, confusion matrices, metrics and galleries.
- `evidence/`: starting proposal, sources, downloads/hashes, complete split manifest,
  rejected annotations, exact duplicate removals, environment and execution logs.
- `data/dataset.yaml`: absolute local dataset root, regenerated by `prepare` after moving.
- `reports/`: Markdown/PDF final report and figure references.

Training uses 416 px images, batch 4, AdamW, seed 42, explicit augmentations and
full precision on the 4 GB GTX 1650. Both sizes share data, resolution and optimizer. Best weights
are selected by validation fitness. Test AP uses confidence 0.001; operational P/R
uses confidence 0.25, NMS IoU 0.7 and class-aware one-to-one matching at IoU 0.5.
The native Ultralytics best-F1 P/R is retained separately and is not the fixed-threshold
operating result. The native confusion matrix uses its own configured matching rule.

The delivered nano run began with batch 8 and resumed at batch 4 after epoch 8
because Windows/CUDA resource interruptions occurred. Small uses batch 4 throughout.
Gradient accumulation targets nominal batch 64. This is a practical comparison,
not a strictly isolated architecture ablation. Original and recovery logs are kept.

At the user's request for faster completion, the delivered small comparison was
stopped after 8 completed epochs of its planned 20. Nano completed 20. Both used
the original 20-epoch learning-rate schedule. The comparison measures these actual
checkpoints, not architecture superiority under equal training. `train_s.json`
records the cutoff, and `scripts/finalize_comparison.py` preserves/plots the checkpoint.
Evaluation reuses native JSON predictions for fixed-threshold counts and galleries;
JSON uses one-based class IDs and native rounding (3-decimal coordinates, 5-decimal scores).

`data/` and weight binaries are kept locally but excluded from Git. Copy the entire
folder when transferring trained assets. A Git clone alone requires fetching data
and retraining or separately obtaining the delivered `models/` directory.

## Attribution and scope

Home Fire Dataset by Bo Peng and Tae-Kook Kim, **CC BY-NC 4.0**, noncommercial
academic use with attribution. Source: https://github.com/PengBo0/Home-fire-dataset
v1.0.0. Cite: B. Peng and T.-K. Kim, "YOLO-HF: Early Detection of Home Fires Using
YOLO," IEEE Access 13 (2025), 79451-79466, doi:10.1109/ACCESS.2025.3566907.
The original collection includes third-party videos; preserve attribution and check
original terms before redistributing media. Ultralytics is AGPL-3.0 / enterprise licensed:
https://www.ultralytics.com/license.

This is an image detector research baseline with a local frontend and an illustrative
virtual sprinkler. The supplied proposal's email alerts and event calibration remain
future work. The results do
not establish certified fire detection, real suppression, time-to-alarm or camera
generalization. Exact duplicates are audited; correlated frames from the same source
video may still cross official splits because a reliable frame-to-video map is absent.
