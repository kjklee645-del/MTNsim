from pathlib import Path
updates = {
    Path(r'D:\Codex\MTNsim\docs\current_status.md'): (
        'calc-linked 3D source-field overlays now differentiate passenger/bus/truck presets by default visual profile and receiver-interaction style (shape-linked mode plus preset-specific colors, scale tendencies, highlight colors, link colors, and interaction reach).',
        'calc-linked 3D source-field overlays now differentiate passenger/bus/truck presets by default visual profile and receiver-interaction style (shape-linked mode plus preset-specific colors, scale tendencies, highlight colors, link colors, interaction reach, and gain-gated receiver highlighting based on the actual directional-emission calculation).'
    ),
    Path(r'D:\Codex\MTNsim\docs\development_checklist.md'): (
        '- [x] Differentiate calc-linked 3D source-field visuals and receiver-interaction styling by directivity preset (passenger/bus/truck).',
        '- [x] Differentiate calc-linked 3D source-field visuals and receiver-interaction styling by directivity preset (passenger/bus/truck), including gain-gated receiver highlighting tied to the actual directional-emission model.'
    ),
    Path(r'D:\Codex\MTNsim\docs\user_guide.md'): (
        'In 3D View, calc-linked source fields now adopt preset-specific visual profiles and receiver-interaction styling. Passenger, bus, and truck presets use different default colors, relative size/height tendencies, highlight colors, link colors, and interaction reach so the active source-field is easier to interpret.',
        'In 3D View, calc-linked source fields now adopt preset-specific visual profiles and receiver-interaction styling. Passenger, bus, and truck presets use different default colors, relative size/height tendencies, highlight colors, link colors, and interaction reach, and receiver highlighting is now gain-gated by the actual directional-emission calculation. Hovering a highlighted receiver also shows its directional gain in dB.'
    ),
    Path(r'D:\Codex\MTNsim\docs\directional_emission_plan.md'): (
        '- calc-linked 3D source-field overlays that reuse the same vertical spread settings for overlay height and receiver highlighting, and now differentiate receiver-interaction style by directivity preset',
        '- calc-linked 3D source-field overlays that reuse the same vertical spread settings for overlay height and receiver highlighting, differentiate receiver-interaction style by directivity preset, and now gate receiver highlighting through the actual directional-gain calculation'
    ),
}
for path, (old, new) in updates.items():
    text = path.read_text(encoding='utf-8')
    if old in text:
        text = text.replace(old, new, 1)
        path.write_text(text, encoding='utf-8')
