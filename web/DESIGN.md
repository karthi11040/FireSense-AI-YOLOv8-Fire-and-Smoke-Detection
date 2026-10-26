# Detection workspace and downloads
References inspected: accepted white dashboard screenshots; Fluent 2 Layout, Button
and Input usage at fluent2.microsoft.design. Use 4px spacing, one primary action,
persistent labels/helper text and responsive grouping. Field documentation timed out.
Recording follows MDN captureStream and MediaRecorder documentation.

Job: choose a source, inspect detections, save annotated output. Replace the sidebar
with a compact header. Put a 320px input panel beside the preview and downloads.
Stack at tablet widths; verify 320/768/1024/1440px. White surfaces, gray workspace,
teal actions, 14px body copy, 44px targets, visible keyboard focus. No simulator or
empty-feed promotion. File details and supported formats stay near the upload.
Benchmark and activity are secondary. Never insert filenames as HTML.

PNG saves the displayed annotated frame. WebM records the preview at 15fps without
audio during uploaded-video playback or explicitly selected camera recording.
Stop/end finalizes it. Explain disabled/finalizing/ready/partial states. Playback is
real time; not every frame is inferred. Export at preview resolution up to 1280x720.
Keep the previous recording when changing sources; replace it only when a new one
starts. Limit recording to approximately 100MB or 10 minutes; preserve the partial
clip and continue detection. Unsupported recording leaves PNG and detection usable.
No new framework or external upload. Verify downloaded files decode with boxes.
