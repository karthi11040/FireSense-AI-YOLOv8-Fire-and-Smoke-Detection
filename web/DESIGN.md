# White monitoring console

Purpose: make the source feed and virtual response understandable at a glance.
Primary action: start a live source. Secondary action: run the explicitly scripted demo.

References inspected: Fluent 2 layout's spacing, grid, proximity and responsive
examples (https://fluent2.microsoft.design/layout). Carbon dashboard/UI-shell and
Fluent toolbar reference URLs were unavailable; do not invent visual evidence.
Use Fluent's 4px spacing rhythm and command/content separation, adapted to this app.

Contract: white surfaces on a soft gray workspace; dark readable text; teal for
operational controls, orange/red for fire, blue for water/smoke. A compact side rail,
one source toolbar, large feed, adjacent response viewport, and a compact timeline.
Move secondary settings into disclosure. No oversized hero, repeated warning blocks,
decorative metric card grid, gradients, or tiny low-contrast copy. Preserve explicit
demo labels, incident latch, permission/error states and simulation-only markings.
Stack panels at narrow widths; verify 320/768/1024/1440px and keyboard navigation.

Real-time contract: process the newest available video frame after each completed
inference, with one request in flight and no fixed 350ms idle delay. Render independently
with requestAnimationFrame. Show measured processing rate/latency and stale-overlay
age; do not claim model inference matches the display refresh rate. Integrate the
toy intensity model using actual elapsed seconds, not a frame-count-dependent clock.

Dedicated simulator reference: the user supplied a white virtual-response card
with a large isometric room, fire on the left box, highlighted target region,
one active central sprinkler, closed neighboring heads, status/time and water controls.
Use this hierarchy on /?view=simulator, preserving the supporting detection feed
and input controls. Target lock is illustrative and does not map camera coordinates
to physical room geometry. Page navigation creates a fresh monitoring session.
