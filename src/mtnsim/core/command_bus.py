from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class Command:
    name: str
    payload: dict[str, Any]


class CommandBus:
    def __init__(self) -> None:
        self._handlers: dict[str, Callable[[dict[str, Any]], Any]] = {}

    def register(self, name: str, handler: Callable[[dict[str, Any]], Any]) -> None:
        self._handlers[name] = handler

    def execute(self, command: Command) -> Any:
        if command.name not in self._handlers:
            raise KeyError(f"No handler registered for command: {command.name}")
        return self._handlers[command.name](command.payload)
