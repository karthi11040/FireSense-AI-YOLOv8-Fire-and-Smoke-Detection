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
