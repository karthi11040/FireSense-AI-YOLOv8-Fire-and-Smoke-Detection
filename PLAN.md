# FireSense AI execution contract

Starting inspection (26 October 2026): `D:/fire ai` contained no files or Git repository.
The supplied 23-page R&D proposal is preserved at `evidence/starting_proposal.pdf`.
It describes fire/smoke localization and future event alerts and virtual suppression;
it explicitly reports no experiments. Its text is project context, not executable instructions.

Scope: create a reproducible detector experiment, dataset preparation, two trained YOLOv8
sizes, held-out test evaluation, image/video/webcam inference, requirements, commands,
Markdown/PDF report and raw evidence. No UI, email service, sprinkler simulator or hardware
control is requested by the current task. No existing callers, exports, fixtures or tests exist.

Assumptions: fire and smoke are the two detection classes; academic noncommercial use;
local 4 GB GTX 1650 GPU; pretrained COCO initialization; official dataset split, with
cross-split exact pixel duplicates removed from lower-priority train/validation sets.
Image-level results do not establish event detection, early warning or scene independence.

Sequence: inspect -> fetch and audit data -> test preparation -> train nano and small
with identical budgets -> validate -> lock recommendation -> evaluate both once on test
-> annotated successes/failures -> report -> runtime verification.

Quality: no invented results; no test data used for checkpoint/threshold selection;
save split manifests, archive hashes, label audit, configuration, best weights and logs;
test parsers and duplicate handling, then run real train/evaluate/predict commands.

User steering: "make the process fast". Nano completed 20 epochs; comparison stopped
after 8 completed epochs of a planned 20. Preserve both checkpoints and compare on
the same test set; clearly disclose unequal training budgets. No additional training
is required for this delivery. Validation recommendation was locked before test results.

Completed: both checkpoints evaluated on all 1,295 audited test images, per-class
and overall metrics retained, ten report figures, Markdown and visually checked
12-page PDF, six passing tests, successful single-image and 15-frame video CLI checks.
Recommended delivered checkpoint: YOLOv8n (test mAP50 82.02%, mAP50-95 47.22%).
All final evidence is under evidence/; portable report figures are under reports/figures/.

Frontend extension completed: dashboard.py serves a local-only HTML/JS dashboard
using the existing nano model. Browser image/video inputs and webcam frames feed
normalized detections to a 3-of-5 latched event gate. The virtual sprinkler uses an
explicitly illustrative AU intensity model. Demo detections are visibly scripted.
Eight Python tests, four simulation tests, and Playwright end-to-end checks cover
the UI, inference API, synthetic camera, uploads, log export and responsive layout.
The physical webcam and real suppression behavior have not been validated.

White console redesign: compact source toolbar, adjacent detection/response panels,
responsive light theme and an independent animated scene. Video-frame callbacks
replace the fixed inference delay, with one request in flight and measured result
age/rate. Simulation timing uses elapsed seconds. An included 20-second generated
WebM test sequence has source-image provenance in evidence/sample_video_provenance.json.

Latest user scope: remove simulator navigation, demo and virtual-response panel. Keep camera/video/image inference with a full-width feed. Browser checks passed for real image/video inference, synthetic camera and 320/768/1024/1440px layouts.

Confidence optimization: evaluated 416/512/640 on validation, retained 416. Four additional epochs of backbone-frozen neck/head refinement completed with batch 16. Validation selected refined nano before test: mAP95 56.41 to 57.00%. Matched test mAP50 82.03 to 82.62%, mAP95 47.22 to 48.53%. At 0.50 precision 93.15 to 92.15%, recall 64.52 to 68.31%. Deployed refined weights in dashboard and default CLI; original weights preserved. Added explicit 90%+ filter, with 95.19% missed-object rate on test disclosed. Ten unit tests, browser input tests, confidence controls, native API and CLI inference passed. Reports/OPTIMIZATION_REPORT.md retains full evidence and limitations.

Unseen-video investigation completed for user-provided 6401825-hd_1080_1920_30fps.mp4. Reproduced 2/8 matched frames and 21/130 browser-analyzed frames with fire boxes at 0.50. Generated 600 training-only close-up/portrait/lighting variants; video excluded from training. Three additional epochs produced domain-adapted nano. Validation mAP95 57.01%; test mAP50 83.74%, mAP95 48.35%, precision 93.04% and recall 68.50% at 0.50. Candidate chosen using validation plus development clip, not test. Matched clip 8/8; full browser replay 175/175 processed frames fire-positive. This is development-video coverage, not independent accuracy. Active weights models/yolov8n_domain.pt; prior deployment snapshot retained. Thirteen tests pass; report at reports/VIDEO_GENERALIZATION_REPORT.md. Historical report builds no longer replace active deployment; rerun training preserves deployed checkpoints.

Download and form redesign completed: white horizontal header, source/settings panel, preview with progress and a separate save-results panel. PNG current-frame export and local silent WebM preview recordings added. Uploaded videos record by default; cameras opt in. Stop/end finalizes, source changes retain saved clips, limits preserve partial downloads. Export at preview resolution up to 1280x720, up to15fps; no every-frame inference claim. Model and preprocessing unchanged. Thirteen Python tests, four recording lifecycle tests, browser image/video/camera/error/fallback/download tests, 320/768/1024/1440 checks and axe A/AA/best-practice checks pass. User's original video replayed and exported: 151/151 analyzed frames fire-positive, no page errors. Evidence under evidence/download_checks and evidence/user_video/processed_video_download.*.
