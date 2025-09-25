from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Sequence


@dataclass(frozen=True)
class CommandMeta:
    name: str
    description: str
    domains: Sequence[str]


DEFAULT_DOMAINS = ("MPI",)

COMMAND_METADATA: Dict[str, CommandMeta] = {
    "PAUSE": CommandMeta("PAUSE", "Pause all MPI ranks", DEFAULT_DOMAINS),
    "RESUME": CommandMeta("RESUME", "Resume all MPI ranks", DEFAULT_DOMAINS),
    "APPCFG": CommandMeta("APPCFG", "Update application configuration key", DEFAULT_DOMAINS),
    "APPCMD": CommandMeta("APPCMD", "Issue application command", DEFAULT_DOMAINS),
    "UPDATEFLOW": CommandMeta("UPDATEFLOW", "Install new flow plan", ("CTL", "AGG", "MPI")),
}

SUGGEST_COMMANDS = [
    COMMAND_METADATA["PAUSE"],
    COMMAND_METADATA["RESUME"],
    COMMAND_METADATA["APPCFG"],
    COMMAND_METADATA["APPCMD"],
    COMMAND_METADATA["UPDATEFLOW"],
]
