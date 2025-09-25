# models.py
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict
from datetime import datetime
from textual import log as tlog


class LogLevel(Enum):
    INFO = auto()
    WARNING = auto()
    ERROR = auto()
    DEBUG = auto()


@dataclass
class Probe:
    id: str
    schema: str
    name: str
    active: bool = True


@dataclass
class Schema:
    name: str
    probes: Dict[str, Probe] = field(default_factory=dict)
    expanded: bool = True


@dataclass
class Aggregator:
    id: str
    address: str
    rank_range: tuple[int, int] = (1e9, -1)
    reps: list[tuple[int, int, int, int]] = field(default_factory=list)


@dataclass
class LogEntry:
    timestamp: datetime
    message: str
    level: LogLevel = LogLevel.INFO
    
    @property
    def formatted_time(self) -> str:
        return self.timestamp.strftime("[%H:%M:%S]")


@dataclass
class Query:
    id: int
    name: str
    text: str
    active: bool = True


@dataclass
class TimestepInfo:
    current: int = 0
    rate: float = 0.0
    step_time_ms: int = 0
    progress: float = 0.0

class TimestepInfo:
    cur_ts: int = 0
    all_ts_ends: list[tuple[int, float]] = []

    def update(self, timestamp: float, from_ts: int, to_ts: int) -> None:
        self.cur_ts = to_ts
        self.all_ts_ends.append((from_ts, timestamp))

@dataclass
class SystemStatus:
    status_text: str = "Unclear"
    aggregator_count: int = 0
    rank_count: int = 0
    timestep: int = 0
    cpu_usage: float = 0.0
    connection_status: str = "Disconnected"