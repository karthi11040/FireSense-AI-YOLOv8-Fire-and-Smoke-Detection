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
