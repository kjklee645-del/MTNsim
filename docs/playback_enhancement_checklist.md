# Playback Enhancement Checklist

## Status Guide
- `[ ]` not started
- `[~]` in progress or partially implemented
- `[x]` implemented

## Playback Roadmap
- [x] Playback-heatmap synchronization
- [x] Zoom / pan / hover inspection
- [x] Minimap inset
- [x] Speed-colored vehicle glyphs
- [x] Vehicle tail trails
- [x] Heatmap control panel
- [x] Layer toggles for playback scene overlays
- [x] Receiver-linked playback cursor and frame marker
- [x] Vehicle selection and pinned vehicle detail panel
- [x] Event markers on timeline for enter/exit, speed-shift, and heading-shift moments
- [x] Camera follow mode for selected vehicle
- [ ] Playback bookmark / keyframe jump buttons
- [ ] Loop playback for selected time range
- [x] Background prefetch for future heatmap frames
- [x] Export playback as PNG sequence / GIF / video
- [ ] Side-by-side playback comparison between scenarios
- [x] Vehicle-specific contribution heatmap mode
- [ ] Playback performance benchmark panel

## Recommended Implementation Order
1. Heatmap control panel + layer toggles
2. Timeline event markers
3. Camera follow mode
4. Scenario comparison and comparison-oriented playback workflows
