from pathlib import Path
updates = {
    Path(r'D:\Codex\MTNsim\docs\current_status.md'): (
        '- Calc-linked 3D source-field overlays now differentiate passenger/bus/truck presets by default visual profile (shape-linked mode plus preset-specific colors and scale tendencies).',
        '- Calc-linked 3D source-field overlays now differentiate passenger/bus/truck presets by default visual profile and receiver-interaction style (shape-linked mode plus preset-specific colors, scale tendencies, highlight colors, link colors, and interaction reach).'
    ),
    Path(r'D:\Codex\MTNsim\docs\development_checklist.md'): (
        '- [x] Differentiate calc-linked 3D source-field visuals by directivity preset (passenger/bus/truck).',
        '- [x] Differentiate calc-linked 3D source-field visuals and receiver-interaction styling by directivity preset (passenger/bus/truck).'
    ),
    Path(r'D:\Codex\MTNsim\docs\user_guide.md'): (
        'In 3D View, calc-linked source fields now adopt preset-specific visual profiles. Passenger, bus, and truck presets use different default colors and relative size/height tendencies so the active source-field is easier to interpret.',
        'In 3D View, calc-linked source fields now adopt preset-specific visual profiles and receiver-interaction styling. Passenger, bus, and truck presets use different default colors, relative size/height tendencies, highlight colors, link colors, and interaction reach so the active source-field is easier to interpret.'
    ),
    Path(r'D:\Codex\MTNsim\docs\directional_emission_plan.md'): (
        '- calc-linked 3D source-field overlays that reuse the same vertical spread settings for overlay height and receiver highlighting',
        '- calc-linked 3D source-field overlays that reuse the same vertical spread settings for overlay height and receiver highlighting, and now differentiate receiver-interaction style by directivity preset'
    ),
    Path(r'D:\Codex\MTNsim\docs\visualization_3d_plan.md'): (
        'Current 3D source-field polish includes preset-specific visual profiles for calc-linked overlays so passenger, bus, and truck runs are easier to distinguish visually.',
        'Current 3D source-field polish includes preset-specific visual profiles and receiver-interaction styling for calc-linked overlays so passenger, bus, and truck runs are easier to distinguish visually and analytically.'
    ),
}
for path, (old, new) in updates.items():
    text = path.read_text(encoding='utf-8')
    if old in text:
        text = text.replace(old, new, 1)
        path.write_text(text, encoding='utf-8')
