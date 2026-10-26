# Current detector check

- Local dashboard was unreachable (connection refused); restarted the existing dashboard in the background.
- Runtime status confirms refined YOLOv8 nano on GPU; the checkpoint SHA256 matches the validation-selected artifact.
- Tested the actual browser inference API at confidence 0.50 on test_10.jpg (fire) and test_1.jpg (smoke). Each detected the annotated class with IoU >= 0.50 and no extra detections in those two samples.
- Reviewed cached held-out failures against annotations: duplicate fire boxes on test_213.jpg; missed small flames on test_374.jpg; fragmented/extra smoke boxes on test_517.jpg; missed faint smoke on test_1004.jpg. These examples confirm remaining detection limitations, not an all-input correctness guarantee.
- Comparison gallery: current_model_failures.jpg. Machine-readable runtime checks: current_model_check.json.
- The user's uploaded video has not been available to inspect. Its local path or attached file is required to reproduce the specific reported error.
- No weights, confidence scores or filtering thresholds were changed during this check.
