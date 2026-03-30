from pathlib import Path
updates = {
    Path(r'D:\Codex\MTNsim\docs\user_guide.md'): [
        ("Project setup and Scenario Editor now support directivity presets: `custom`, `passenger`, `bus`, and `truck`. Non-custom presets auto-fill horizontal and vertical directivity values and keep the fields linked until switched back to `custom`.",
         "Project setup and Scenario Editor now support directivity presets from coarse legacy groups through finer vehicle classes: `custom`, `passenger`, `sedan`, `suv`, `bus`, `city_bus`, `coach_bus`, `truck`, `delivery_truck`, and `heavy_truck`. Non-custom presets auto-fill horizontal and vertical directivity values and keep the fields linked until switched back to `custom`."),
        ("In 3D View, calc-linked source fields now adopt preset-specific visual profiles and receiver-interaction styling. Passenger, bus, and truck presets use different default colors, relative size/height tendencies, highlight colors, link colors, and interaction reach, and receiver highlighting is now gain-gated by the actual directional-emission calculation. Hovering a highlighted receiver also shows its directional gain in dB.",
         "In 3D View, calc-linked source fields now adopt preset-specific visual profiles and receiver-interaction styling. Legacy and fine-grained presets such as `sedan`, `suv`, `city_bus`, `coach_bus`, `delivery_truck`, and `heavy_truck` each use distinct colors, size/height tendencies, highlight colors, link colors, and interaction reach, and receiver highlighting is now gain-gated by the actual directional-emission calculation. Hovering a highlighted receiver also shows its directional gain in dB.")
    ],
    Path(r'D:\Codex\MTNsim\docs\directional_emission_plan.md'): [
        ("Phase 2 now includes user-facing presets to make directional emission easier to adopt in project setup and scenario editing. Current presets are `custom`, `passenger`, `bus`, and `truck`.",
         "Phase 2 now includes user-facing presets to make directional emission easier to adopt in project setup and scenario editing. Current presets cover both legacy broad classes and finer vehicle groups: `custom`, `passenger`, `sedan`, `suv`, `bus`, `city_bus`, `coach_bus`, `truck`, `delivery_truck`, and `heavy_truck`."),
    ],
    Path(r'D:\Codex\MTNsim\docs\current_status.md'): [
        ("- Directional emission UX now includes directivity presets (`custom`, `passenger`, `bus`, `truck`) in both project setup and Scenario Editor.",
         "- Directional emission UX now includes coarse and fine-grained directivity presets (`custom`, `passenger`, `sedan`, `suv`, `bus`, `city_bus`, `coach_bus`, `truck`, `delivery_truck`, `heavy_truck`) in both project setup and Scenario Editor."),
    ],
    Path(r'D:\Codex\MTNsim\docs\development_checklist.md'): [
        ("- [x] Add directivity preset workflow (`custom`, `passenger`, `bus`, `truck`) to starter-project setup and Scenario Editor.",
         "- [x] Add directivity preset workflow (legacy broad classes plus finer classes such as `sedan`, `suv`, `city_bus`, `coach_bus`, `delivery_truck`, and `heavy_truck`) to starter-project setup and Scenario Editor."),
    ],
    Path(r'D:\Codex\MTNsim\docs\scenario_editor_field_reference.md'): [
        ("Directivity presets let you choose a predefined directional-emission profile instead of editing individual values manually.",
         "Directivity presets let you choose a predefined directional-emission profile instead of editing individual values manually. Presets now include both broad legacy classes and finer vehicle groups such as sedan, SUV/van, city bus, coach bus, delivery truck, and heavy truck.")
    ],
}
for path, replacements in updates.items():
    text = path.read_text(encoding='utf-8')
    changed = False
    for old, new in replacements:
        if old in text:
            text = text.replace(old, new, 1)
            changed = True
    if changed:
        path.write_text(text, encoding='utf-8')
