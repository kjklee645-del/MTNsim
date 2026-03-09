# MTNsim PRD Draft

Author: Codex
Date: 2026-03-09
Status: Draft v0.1

## 1. Product Summary

MTNsim is a traffic noise simulation platform that reproduces second-level road traffic noise fields by combining microscopic vehicle motion, 3D scene context, and measurement-based calibration.

The product is not positioned as a static average-noise mapping tool. It is positioned as a dynamic traffic-noise digital twin platform that can model vehicle-level events, terrain and roadside objects, and real-world sensor correction.

A core strategic requirement is AI-agent readiness. The product must be designed so that a future AI agent can safely control simulations through natural language without bypassing the simulation engine's deterministic interfaces.

## 2. Product Vision

Build a professional traffic-noise simulation tool that:
- models each vehicle as a moving sound source
- computes time-series noise at receivers and grid cells
- corrects the sound field using 3D terrain and roadside objects
- calibrates predictions with measured data
- exposes deterministic command interfaces so an AI agent can control scenarios using natural language

## 3. Target Users

- transport noise researchers
- public-sector planning and policy teams
- environmental impact assessment teams
- road design and traffic operation consultants
- smart-city or digital-twin operators

## 4. Problem Statement

Conventional road traffic noise tools are optimized for hourly average noise and macroscopic traffic input. They are weak at representing fast changes caused by:
- lane changes
- stop-and-go traffic
- speed-control policies
- mixed fleets including EVs
- geometric shielding and reflection at fine spatial resolution
- alignment with measured time-series sensor data

Users also need a simpler interaction model. Expert tools are often hard to control and require many manual parameter edits. In the target product, users should eventually be able to issue natural-language commands such as:
- "Run the scenario with 30 percent heavy vehicles and reduce speed to 80 km/h after 300 m."
- "Compare the current case with a 4 m barrier on the east side."
- "Explain why receiver R12 increased after 08:10."

## 5. Product Goals

### 5.1 Core Goals

- simulate microscopic, vehicle-level traffic noise over time
- support 2.5D and 3D scene-aware correction
- support receiver and grid-based outputs
- support calibration against measured sensor data
- support scenario comparison and reproducibility
- support future AI-agent control through stable APIs and command schemas

### 5.2 Non-Goals for the First Production Candidate

- full general-purpose urban acoustics for every source class
- unlimited free-form agent autonomy without safety checks
- real-time nationwide scale simulation
- full regulatory certification in the first release

## 6. Strategic Review Applied Before Scoping

### 6.1 Review Item 1: AI-Agent Extensibility

The product must be AI-agent extensible from the first architecture iteration.

This means:
- the engine must expose structured commands instead of relying on GUI-only flows
- scenario edits must be representable as typed actions
- model state must be queryable in machine-readable form
- all agent actions must be auditable and replayable
- dangerous actions must pass through permissions and validation gates
- explanation traces must be retained so the user can inspect what the agent changed and why

Required architectural implications:
- an `agent command layer` must exist above the simulation kernel
- an `intent-to-command schema` must translate natural language into deterministic engine actions
- simulation configs must be serializable to versioned manifests
- engine results must support summary retrieval optimized for LLM context windows
- the GUI must not be the only control surface

Conclusion:
AI-agent extensibility is not sufficiently covered by the original 2-year plan unless it is explicitly added as a first-class product requirement. It is now included in scope.

### 6.2 Review Item 2: Re-estimated Timeline If Codex Directly Develops

Assumption:
- development starts on 2026-03-09
- core implementation is accelerated by AI-driven coding throughput
- user provides domain decisions, sample data, and test feedback without long idle gaps
- the estimate excludes long external validation, procurement, or certification delays

Updated estimate:
- research-grade kernel and architecture refactor: 4 to 6 weeks
- internal MVP for scenario simulation and receiver/grid outputs: 10 to 14 weeks
- professional alpha with 3D correction, calibration, and basic UI: 5 to 7 months
- agent-ready beta with natural-language control over a bounded action set: 7 to 9 months
- production candidate with stronger validation, reporting, and operational hardening: 9 to 12 months

Revised milestone target if work starts on 2026-03-09:
- Architecture baseline: by 2026-04-15
- Internal MVP: by 2026-06-15
- Professional alpha: by 2026-09-30
- Agent-ready beta: by 2026-11-30
- Production candidate: between 2026-12-31 and 2027-03-09

Conclusion:
The earlier 2-year estimate is conservative for pure software implementation. If Codex is used as the primary implementation engine, the software side can likely be compressed to about 9 to 12 months. The main schedule risk moves from coding speed to validation quality, data quality, and product decisions.

## 7. Scope

### 7.1 In Scope for the First Production Candidate

- SUMO-based microscopic traffic integration
- vehicle-level moving sound source modeling
- receiver and grid noise time-series output
- scenario parameters for vehicle mix, speed, lane behavior, and route settings
- 2.5D terrain and selected 3D obstacle correction
- barrier, building, and terrain shielding effects
- measurement-based correction workflow
- comparison of at least two scenarios
- reproducible project file and run manifest
- batch execution API
- machine-readable result summaries
- bounded natural-language simulation control via AI agent

### 7.2 Out of Scope for the First Production Candidate

- unrestricted autonomous agent actions across the entire workstation
- full CAD authoring suite
- every international road-noise method in the first release
- multi-city live operations at very large scale

## 8. Key User Stories

### 8.1 Research User

- As a researcher, I want to change speed, lane-change behavior, and fleet mix so that I can analyze event-level noise changes.
- As a researcher, I want receiver-level time-series outputs so that I can compare them with measured data.

### 8.2 Planner or Consultant

- As a planner, I want to compare barrier and speed-policy scenarios so that I can justify a design option.
- As a consultant, I want exportable reports and maps so that I can deliver results to a client.

### 8.3 AI-Agent User

- As a user, I want to describe a simulation in natural language so that I do not need to manually edit every parameter.
- As a user, I want to inspect which commands the agent executed so that I can trust or reject the result.
- As a user, I want to lock certain actions behind approval so that the agent cannot silently change critical settings.

## 9. Functional Requirements

### 9.1 Simulation Core

- import traffic network and route inputs
- create and manage vehicle states over time
- compute per-vehicle emission terms
- propagate and aggregate noise to receiver points and grid cells
- support configurable time step
- store scenario parameters and run outputs

### 9.2 3D Scene and Correction

- import terrain, buildings, and barrier objects
- assign material and correction properties
- compute overlap, shielding, reflection or diffraction-related correction terms
- map scene-space corrections to noise-space cells or receivers

### 9.3 Calibration

- import measured time-series sensor data
- align time stamps and receiver mappings
- estimate correction factors and residual error
- output calibration reports and confidence indicators

### 9.4 Visualization and Reporting

- show noise maps and receiver charts
- compare scenarios side by side
- generate report-ready tables and summaries
- export machine-readable and human-readable outputs

### 9.5 Agent Platform Requirements

- expose simulation actions through a typed command API
- expose read-only state queries for scenario inspection
- validate agent actions before execution
- require approval for high-impact actions
- log prompts, parsed intents, commands, diffs, and results
- support replay of agent sessions against the same project state
- support bounded tool access instead of unrestricted code execution by default

## 10. Non-Functional Requirements

- reproducibility: same config and seed should reproduce the same run
- traceability: all scenario changes must be logged
- performance: must support batch execution on research-scale cases without manual tuning
- modularity: traffic, acoustics, scene, calibration, and agent modules must be separable
- inspectability: outputs must be explainable enough for engineering review
- security: agent actions must run through permission boundaries

## 11. Success Metrics

### 11.1 Product Metrics

- time required to create and run a new scenario
- time required to compare two scenarios
- number of manual edits eliminated by the agent interface
- percentage of agent commands accepted without manual correction

### 11.2 Engineering Metrics

- regression pass rate on benchmark cases
- runtime per scenario at target grid and vehicle scale
- memory usage stability
- calibration error reduction against baseline

### 11.3 Agent Metrics

- intent parsing accuracy on domain commands
- command execution success rate
- percentage of actions requiring rollback
- explanation usefulness score from user review

## 12. Constraints and Risks

### 12.1 Major Risks

- physical-model simplification may limit professional trust
- data quality may dominate calibration quality
- performance may degrade sharply with grid density and vehicle count
- agent freedom without bounded commands may harm reproducibility and trust

### 12.2 Mitigations

- keep a validated baseline mode and an advanced mode
- treat data ingestion and timestamp alignment as first-class features
- design for vectorization and GPU use early
- isolate the AI agent behind a command bus and permission model

## 13. Release Plan

### Phase A: Architecture Baseline
Target date: 2026-04-15

- modular refactor
- config manifest
- result storage standard
- benchmark harness
- initial command schema for agent control

### Phase B: Internal MVP
Target date: 2026-06-15

- vehicle-level simulation loop
- receiver and grid outputs
- scenario runner
- batch API
- initial result viewer

### Phase C: Professional Alpha
Target date: 2026-09-30

- 3D correction workflow
- calibration workflow
- report export
- scenario compare UI

### Phase D: Agent-Ready Beta
Target date: 2026-11-30

- natural-language scenario editing
- bounded command planner
- approval flow and action log
- explanation panel

### Phase E: Production Candidate
Target date: 2026-12-31 to 2027-03-09

- validation hardening
- runtime tuning
- data import stabilization
- user workflow polish

## 14. Open Decisions

- which road-noise methodology is the authoritative baseline for the first professional release
- which 3D effects are mandatory in the first validated model
- how much agent autonomy is acceptable in the first release
- whether the first UI target is desktop-first, web-first, or hybrid
- which external data formats are mandatory on day one

## 15. Immediate Next Steps

1. finalize the package architecture around engine boundaries and command interfaces
2. define the project manifest and scenario schema
3. define the bounded command set for the AI agent
4. split the current prototype into simulation kernel, scenario layer, and result layer
5. build benchmark and regression cases before major feature expansion
