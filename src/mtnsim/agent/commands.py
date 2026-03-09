from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class AgentCommand:
    name: str
    arguments: dict
    risk_level: str = "medium"
