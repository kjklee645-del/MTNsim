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
- [ ] Receiver-linked playback cursor and frame marker
- [ ] Vehicle selection and pinned vehicle detail panel
- [ ] Event markers on timeline for lane-change / speed-shift moments
- [ ] Camera follow mode for selected vehicle
- [ ] Playback bookmark / keyframe jump buttons
- [ ] Loop playback for selected time range
- [ ] Background prefetch for future heatmap frames
- [ ] Export playback as PNG sequence / GIF / video
- [ ] Side-by-side playback comparison between scenarios
- [ ] Vehicle-specific contribution heatmap mode
- [ ] Playback performance benchmark panel

## Recommended Implementation Order
1. Heatmap control panel + layer toggles
2. Receiver-linked playback cursor
3. Playback performance improvement and frame prefetch
4. Vehicle selection and detail panel
5. Timeline event markers
6. Camera follow mode
7. Export and comparison workflows
