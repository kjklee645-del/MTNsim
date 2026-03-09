# Manifest and Scenario Schema Notes

This document fixes the configuration order before large-scale refactoring.

## Why the manifest comes first

The manifest and scenario schema define the stable input language for:
- CLI
- GUI
- batch runner
- API
- AI agent

Without this layer, code refactoring tends to hard-code assumptions and must be redone later.

## Manifest responsibilities

The project manifest stores:
- project identity
- shared input paths
- simulation defaults
- agent policy defaults
- output policy

## Scenario responsibilities

A scenario stores run-specific inputs:
- traffic composition and timing
- speed and lane controls
- noise coefficients
- grid settings
- receiver locations

## AI-agent implications

Because the AI agent is a first-class future requirement, all user-visible changes should eventually map to scenario edits or bounded commands derived from the manifest.
