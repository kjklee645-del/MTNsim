from pathlib import Path
updates = {
    Path(r'D:\Codex\MTNsim\docs\development_checklist.md'): (
        'built-in 3D snapshot/Markdown export, a first visual-polish pass for roads/barriers/buildings/vehicle glyphs plus basic labels/window hints/vegetation variation, barrier/terrain material patterning, a darker lighting pass, and a deeper playback-aware slice with selected-vehicle highlighting, trails, follow, and playback-synced 3D noise updates are now implemented; further 3D polish still remains',
        'built-in 3D snapshot/Markdown export plus hi-res PNG export, hover/tooltip inspection with halo highlighting, a first visual-polish pass for roads/barriers/buildings/vehicle glyphs plus basic labels/window hints/vegetation variation, barrier/terrain material patterning, a darker lighting pass, and a deeper playback-aware slice with selected-vehicle highlighting, trails, follow, and playback-synced 3D noise updates are now implemented; further 3D polish still remains'
    ),
    Path(r'D:\Codex\MTNsim\docs\current_status.md'): (
        '3D view and source-field visualization are now part of the main operator workflow; the GUI can now export the active 3D canvas as a PNG snapshot and export a Markdown 3D report, but deeper presentation polish still remains',
        '3D view and source-field visualization are now part of the main operator workflow; the GUI can now export the active 3D canvas as a PNG snapshot, export a hi-res 2x PNG snapshot, inspect rendered objects through hover tooltip/halo feedback, and export a Markdown 3D report, but deeper presentation polish still remains'
    ),
    Path(r'D:\Codex\MTNsim\docs\user_guide.md'): (
        '- export a 3D PNG snapshot',
        '- export a 3D PNG snapshot\n- export a hi-res 2x 3D PNG snapshot\n- inspect 3D receivers, vehicles, barriers, terrain edges, and buildings with hover halos and tooltips'
    ),
    Path(r'D:\Codex\MTNsim\docs\visualization_3d_plan.md'): (
        '- export the current 3D canvas as a PNG snapshot [done]',
        '- export the current 3D canvas as a PNG snapshot [done]\n- export a hi-res 2x PNG snapshot for presentation use [done]\n- provide hover tooltip/halo inspection for rendered 3D objects [done]'
    ),
}
for path, (old, new) in updates.items():
    text = path.read_text(encoding='utf-8')
    if old in text:
        text = text.replace(old, new, 1)
        path.write_text(text, encoding='utf-8')
