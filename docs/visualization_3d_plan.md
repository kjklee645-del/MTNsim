# 3D Scene and Noise Visualization Plan

Date: 2026-03-18
Purpose: define the scope and first implementation order for the mainline 3D visualization track before starting code changes.

## 1. Why This Is the Next Mainline Step

MTNsim now has a usable 2D operator workflow:
- project creation/import
- scenario editing
- scene-object authoring
- free rectangular grid-region authoring
- run / result / compare / playback

The next major gap is visual comprehension.
The current 2D scene and heatmap are useful, but they are no longer sufficient for:
- terrain-aware interpretation
- barrier/building height understanding
- receiver-height understanding
- future volumetric and directional source-field display

That makes a true 3D scene/noise layer the next major mainline expansion.

## 2. Scope Boundary

This plan is for `3D scene/noise visualization`, not yet for full 3D physics.

Included in scope:
- 3D rendering of roads, receivers, barriers, buildings, terrain edges, ground surfaces, and vegetation zones
- 3D rendering of a run-level noise field derived from existing grid outputs
- camera controls and layer toggles suitable for operator use
- a scene/view architecture that later volumetric/directive source-field modes can reuse

Not included in this first scope:
- true 3D propagation reimplementation
- full CFD-like volumetric acoustics
- CAD/GIS-grade modeling tools
- final directional source physics
- full regulatory reporting around 3D outputs

## 3. Recommended Rendering Stack

Recommended baseline:
- stay inside `PySide6`
- use a dedicated 3D view layer under `src/mtnsim/gui/views/`
- target a `Qt3D`-style scene graph first so the GUI remains consistent with the existing desktop shell

Why this choice:
- matches the existing PySide6 app shell
- keeps event handling and GUI integration simple
- gives a reusable scene graph for later vehicle/source-field rendering

Architectural rule:
- do not couple the 3D renderer directly to run services
- build a scene adapter layer that converts MTNsim scene/runtime/result data into renderable 3D primitives

## 4. 3D MVP Definition

The first 3D milestone should be a `static 3D scene + static 3D noise view`.

### 4.1 Must Show

- road corridor as 3D ribbons or slabs
- receivers as vertical markers with labels
- noise barriers as extruded walls
- buildings as extruded prisms from footprint + height
- terrain edges as raised line/wall markers
- ground surfaces and vegetation zones as colored flat polygons
- one selected run's grid noise as a 3D surface or raised field over the grid region

### 4.2 Must Support

- orbit / pan / zoom camera
- reset view
- layer on/off toggles
- color legend for noise field
- choose between:
  - `2D Heatmap`
  - `3D Noise Surface`
- selecting a result/run from the existing result workflow

### 4.3 Nice to Have but Not Required in First 3D Step

- animated vehicles in 3D
- 3D playback heatmap updates per frame
- slice views
- terrain mesh instead of flat terrain-edge proxies
- volumetric source-field bubbles/wedges

## 5. Data Model for the 3D Layer

Introduce a renderer-facing adapter layer, for example:
- `gui/models/scene_3d.py`
- `gui/controllers/scene3d_controller.py`
- `gui/views/scene_3d_view.py`

The adapter should consume:
- current scenario
- current scene snapshot
- selected run result summary
- selected grid snapshot or dynamic heatmap frame

And produce render primitives like:
- `RoadMesh`
- `ReceiverMarker`
- `BarrierMesh`
- `BuildingMesh`
- `GroundPolygon`
- `VegetationPolygon`
- `NoiseSurfaceMesh`

Important constraint:
- the adapter should remain separate from simulation logic so later 3D rendering changes do not force engine changes.

## 6. First Implementation Order

### Phase 3D-0: Architecture Freeze

Build first:
- 3D visualization plan document
- renderer adapter contract
- new GUI navigation target for `3D View`
- minimal placeholder screen

Goal:
- freeze the architecture before graphics work spreads through unrelated files

### Phase 3D-1: Static 3D Scene Shell

Build next:
- 3D canvas/view widget
- camera controls
- static road geometry
- receiver markers
- barrier/building/terrain/ground/vegetation geometry
- layer toggles

Goal:
- users can inspect the authored scene in 3D even before noise rendering is added

### Phase 3D-2: Static 3D Noise Surface

Build next: [started]
- load selected run's final grid snapshot [done]
- convert grid cells into a 3D surface or height field [done]
- add legend and dB scaling controls [done]
- let users switch between color-only and height-plus-color rendering [done]
- support operator camera controls for orbit / pan / zoom / reset [done]

Goal:
- users can understand the noise field spatially in 3D

### Phase 3D-3: Result Integration Polish

Build next:
- open 3D view directly from Result Viewer [done]
- bind the selected run to the 3D view [done]
- show run metadata and current view mode [done]
- keep layer states and camera resets manageable [started]

Goal:
- make the 3D view part of the normal operator workflow rather than a demo-only screen

### Phase 3D-4: Playback-Aware 3D Expansion

Later:
- animate vehicles in 3D
- sync playback slider with 3D scene
- optional dynamic heatmap updates per frame

Goal:
- unify playback and 3D visualization after the static 3D scene is stable

## 7. Relationship to Future Directional Source-Field Work

This 3D plan is the prerequisite for later source-field visualization work.

Later directional/source-field modes should plug into the same 3D scene as optional overlays:
- spherical source field
- wedge-like/directive field
- other user-selectable source-region shapes

That later work should reuse:
- camera controls
- object selection
- legend/overlay controls
- scene adapter layer

## 8. Main Risks

### Risk 1: Rendering Stack Complexity
If the first 3D widget is too heavy, the GUI can become unstable or hard to maintain.
Mitigation:
- start with a static 3D scene shell before dynamic playback
- keep a strict adapter layer

### Risk 2: Mixing Visualization with Physics
If 3D view logic starts mutating engine structures, later maintenance becomes expensive.
Mitigation:
- renderer consumes scenario/result data only
- no simulation logic should live inside 3D widgets

### Risk 3: Scope Creep
Trying to deliver 3D playback, volumetric fields, and true 3D acoustics in one pass will stall progress.
Mitigation:
- first milestone is static 3D scene plus static 3D noise field only

## 9. Immediate Next Coding Task

The next coding task after the current slice is:
1. keep layer states and camera resets manageable across 3D result switches
2. prepare the scene adapter for later playback-aware 3D updates
3. then move toward playback-aware 3D behavior
4. after that, start volumetric/directive source-field overlays

That is the correct next slice because the static 3D scene, static 3D noise surface, operator legend/range controls, and orbit/pan/zoom camera now exist and should be folded into the normal result workflow before dynamic 3D playback is attempted.
