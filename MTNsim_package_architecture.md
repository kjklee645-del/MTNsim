# MTNsim Package Architecture Design

Author: Codex
Date: 2026-03-09
Status: Draft v0.1

## 1. Design Principles

The package structure must support four properties from the start:
- deterministic simulation execution
- modular acoustics and scene modeling
- reproducible scenario management
- safe AI-agent extensibility

The AI agent must not manipulate the simulation by directly patching internal objects. It should use a stable command layer that sits above the domain engine.

## 2. Top-Level Architecture

Recommended workspace structure:

```text
MTNsim/
  docs/
  configs/
  data/
  examples/
  outputs/
  src/
    mtnsim/
      app/
      agent/
      api/
      core/
      traffic/
      acoustics/
      scene/
      calibration/
      visualization/
      io/
      schemas/
      services/
      utils/
  tests/
    unit/
    integration/
    regression/
    benchmarks/
```

## 3. Package Responsibilities

### 3.1 `mtnsim.app`

Entry points and orchestration.

Responsibilities:
- CLI entry points
- desktop or service bootstrap
- environment setup
- dependency wiring

Example modules:
- `main.py`
- `runner.py`
- `bootstrap.py`

### 3.2 `mtnsim.agent`

AI-agent integration layer.

Responsibilities:
- natural-language intent parsing integration
- command planning over bounded domain actions
- approval and permission policies
- agent session state and memory
- audit log and replay
- explanation generation from executed commands and results

Recommended modules:
- `planner.py`
- `policies.py`
- `commands.py`
- `session.py`
- `audit.py`
- `explanations.py`
- `tool_registry.py`

Important rule:
The agent package can call public APIs and services, but must not directly mutate deep engine internals.

### 3.3 `mtnsim.api`

Stable public interfaces.

Responsibilities:
- typed facade for project, scenario, run, result, and agent actions
- command execution interfaces
- state query interfaces
- serialization-friendly DTOs

Recommended modules:
- `project_api.py`
- `scenario_api.py`
- `simulation_api.py`
- `result_api.py`
- `agent_api.py`

### 3.4 `mtnsim.core`

Core execution primitives shared across domains.

Responsibilities:
- simulation clock
- event bus
- command bus
- domain errors
- job lifecycle
- run context
- deterministic seed handling

Recommended modules:
- `clock.py`
- `events.py`
- `command_bus.py`
- `context.py`
- `errors.py`
- `jobs.py`

### 3.5 `mtnsim.traffic`

Traffic simulation abstraction layer.

Responsibilities:
- SUMO adapter
- vehicle state model
- route and lane behavior abstraction
- trajectory replay from measured or external data

Recommended modules:
- `adapters/sumo_adapter.py`
- `models.py`
- `state_store.py`
- `scenario_controls.py`
- `trajectory_replay.py`

### 3.6 `mtnsim.acoustics`

Acoustic computation domain.

Subpackages:
- `emission/`
- `propagation/`
- `field/`
- `gpu/`

Responsibilities:
- per-vehicle emission terms
- propagation and correction logic
- receiver and grid aggregation
- GPU-accelerated kernels

Recommended modules:
- `emission/base.py`
- `emission/road_vehicle.py`
- `propagation/distance.py`
- `propagation/shielding.py`
- `propagation/reflection.py`
- `propagation/diffraction.py`
- `field/grid_engine.py`
- `field/receiver_engine.py`
- `gpu/tensors.py`
- `gpu/kernels.py`

### 3.7 `mtnsim.scene`

Spatial scene domain.

Responsibilities:
- terrain model
- buildings, barriers, and roadside objects
- material properties
- grid generation
- overlap and spatial query services

Recommended modules:
- `terrain.py`
- `objects.py`
- `materials.py`
- `grid.py`
- `spatial_index.py`
- `overlap.py`

### 3.8 `mtnsim.calibration`

Measured-data correction domain.

Responsibilities:
- sensor data import
- timestamp alignment
- receiver mapping
- correction factor estimation
- residual analysis

Recommended modules:
- `sensors.py`
- `alignment.py`
- `estimation.py`
- `metrics.py`
- `reports.py`

### 3.9 `mtnsim.visualization`

Presentation layer.

Responsibilities:
- receiver plots
- grid map rendering
- scenario comparison views
- report chart generation

Recommended modules:
- `charts.py`
- `maps.py`
- `compare.py`
- `export.py`

### 3.10 `mtnsim.io`

Input and output adapters.

Responsibilities:
- project manifest read/write
- importers for network, GIS, measurement data
- output writers for CSV, Parquet, SQLite, JSON

Recommended modules:
- `project_store.py`
- `network_import.py`
- `scene_import.py`
- `measurement_import.py`
- `result_store.py`

### 3.11 `mtnsim.schemas`

Typed schemas and validation contracts.

Responsibilities:
- project schema
- scenario schema
- run schema
- result summary schema
- agent command schema

Recommended modules:
- `project.py`
- `scenario.py`
- `run.py`
- `results.py`
- `agent_commands.py`

### 3.12 `mtnsim.services`

High-level use-case services.

Responsibilities:
- create project
- run scenario
- compare scenarios
- calibrate scenario
- summarize results for UI or agent

Recommended modules:
- `project_service.py`
- `run_service.py`
- `compare_service.py`
- `calibration_service.py`
- `summary_service.py`

### 3.13 `mtnsim.utils`

Small shared helpers only.

Rule:
Do not let `utils` become a dumping ground. If logic is domain-specific, keep it inside the owning package.

## 4. Data and Control Flow

### 4.1 Human or API Flow

1. user creates or loads a project
2. scenario config is validated against schema
3. services build a run context
4. traffic engine produces vehicle states
5. scene engine provides spatial queries and correction context
6. acoustics engine computes receiver and grid values
7. calibration engine optionally adjusts outputs
8. results are stored and summarized
9. visualization layer renders charts and maps

### 4.2 AI-Agent Flow

1. user issues a natural-language instruction
2. `agent.planner` parses the intent into bounded domain commands
3. `agent.policies` checks permission and risk level
4. approved commands are sent to `core.command_bus`
5. `api` and `services` execute the commands
6. run results and diffs are logged in `agent.audit`
7. `agent.explanations` produces a human-readable summary

This separation is essential. The agent is a planner and controller, not the simulation kernel itself.

## 5. Agent-Ready Design Requirements

To support future natural-language control safely, the architecture must include the following from the first iteration.

### 5.1 Command Schema

All write operations should be expressed as typed commands, such as:
- `CreateScenario`
- `UpdateFleetMix`
- `SetSpeedPolicy`
- `AddBarrierObject`
- `RunSimulation`
- `CompareScenario`
- `ExportReport`

### 5.2 Query Schema

The agent needs read-only machine-friendly queries, such as:
- `GetScenarioSummary`
- `ListReceivers`
- `GetReceiverTimeseries`
- `GetRunStatus`
- `GetTopNoiseContributors`

### 5.3 Permission Boundaries

Commands should be classified by risk:
- low risk: read queries, chart generation
- medium risk: scenario parameter edits
- high risk: deleting runs, overwriting baseline configs, external exports

### 5.4 Auditability

Every agent action should persist:
- source instruction
- parsed intent
- generated commands
- approval result
- resulting config diff
- run outputs referenced in the explanation

### 5.5 Replayability

Agent sessions should be replayable against the same project snapshot to support trust and debugging.

## 6. Suggested Core Domain Models

Suggested first models:
- `Project`
- `Scenario`
- `RunRequest`
- `RunResult`
- `VehicleState`
- `Receiver`
- `NoiseGrid`
- `SceneObject`
- `Material`
- `CalibrationDataset`
- `AgentCommand`
- `AgentActionLog`

## 7. File and Storage Strategy

Recommended storage:
- project metadata: JSON or TOML manifest
- structured results: Parquet or SQLite
- time-series outputs: Parquet preferred, CSV optional for export
- chart and map exports: PNG, PDF
- audit logs: JSONL

Recommended project layout:

```text
project-root/
  project.toml
  scenarios/
  scene/
  measurements/
  runs/
    <run-id>/
      request.json
      summary.json
      outputs.parquet
      audit.jsonl
```

## 8. Testing Strategy by Package

- `unit`: formulas, validators, command parsing, scene overlap logic
- `integration`: traffic-to-acoustics-to-results pipeline
- `regression`: benchmark scenarios with expected outputs
- `benchmarks`: runtime and memory tests on representative cases

AI-agent-specific tests:
- intent to command mapping tests
- policy enforcement tests
- audit completeness tests
- replay determinism tests

## 9. Migration Path From Current Prototype

### Step 1
Move the current single-script logic into these initial modules:
- `traffic/adapters/sumo_adapter.py`
- `acoustics/emission/road_vehicle.py`
- `acoustics/field/grid_engine.py`
- `scene/grid.py`
- `io/result_store.py`

### Step 2
Introduce a project manifest and scenario config file.

### Step 3
Replace direct script-level globals with typed state containers.

### Step 4
Add command and query APIs before adding the AI layer.

### Step 5
Add the AI package only after the command layer is stable.

## 10. Timeline Re-estimate With Codex as Primary Implementer

Assumption:
- implementation starts on 2026-03-09
- the main bottleneck is not coding speed but decisions, data, and validation

Estimated build timeline:
- package skeleton plus refactor baseline: 2 to 3 weeks
- scenario API plus simulation core split: 3 to 5 weeks
- first benchmarked internal MVP: 8 to 12 weeks
- 3D correction and calibration alpha: 5 to 6 months
- bounded AI-agent integration beta: 7 to 9 months
- production-candidate package maturity: 9 to 12 months

## 11. Immediate Implementation Order

1. `schemas`
2. `core`
3. `traffic`
4. `scene`
5. `acoustics`
6. `io`
7. `services`
8. `api`
9. `visualization`
10. `agent`

The agent package appears late in implementation order, but the command and query interfaces it depends on must be designed first.

## 12. Final Recommendation

Do not build the AI agent as a layer that directly operates the GUI or raw code internals. Build MTNsim as an engine with explicit commands, explicit queries, and explicit audit logs. Then the AI agent becomes an interchangeable control layer on top of a trustworthy simulation platform.
