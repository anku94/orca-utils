# state.py
from typing import Dict, List, Optional, Callable, Set
from datetime import datetime
import threading
import queue
from interface.models import (
    Schema, 
    Probe, 
    Aggregator, 
    LogEntry, 
    Query, 
    TimestepInfo, 
    SystemStatus, 
    LogLevel)


class StateManager:
    def __init__(self):
        self.schemas: Dict[int, Schema] = {}
        self.aggregators: Dict[str, Aggregator] = {}
        self.logs: List[LogEntry] = []
        self.queries: Dict[int, Query] = {}
        self.timestep: TimestepInfo = TimestepInfo()
        self.status: SystemStatus = SystemStatus()
        
        self._listeners: Dict[str, Set[Callable]] = {
            "schemas": set(),
            "aggregators": set(),
            "logs": set(),
            "queries": set(),
            "timestep": set(),
            "status": set(),
        }
        self._lock = threading.RLock()
        
        # Queue for UI updates
        self._ui_update_queue = queue.Queue()
    
    def queue_ui_update(self, update_func: Callable[[], None]) -> None:
        """Queue a UI update function to be executed in the UI thread"""
        self._ui_update_queue.put(update_func)
    
    def process_ui_updates(self) -> None:
        """Process any queued UI updates - call this from the UI thread"""
        try:
            while True:
                update_func = self._ui_update_queue.get_nowait()
                try:
                    update_func()
                except Exception as e:
                    print(f"Error in UI update: {e}")
        except queue.Empty:
            pass
    
    def add_schema(self, schema: Schema) -> None:
        with self._lock:
            self.schemas[schema.id] = schema
            self._notify("schemas")
    
    def add_probe(self, probe: Probe) -> None:
        with self._lock:
            if probe.schema_id in self.schemas:
                self.schemas[probe.schema_id].probes[probe.id] = probe
                self._notify("schemas")
    
    def set_probe_active(self, probe_id: int, schema_id: int, active: bool) -> None:
        with self._lock:
            if schema_id in self.schemas and probe_id in self.schemas[schema_id].probes:
                self.schemas[schema_id].probes[probe_id].active = active
                self._notify("schemas")
    
    def toggle_schema_expanded(self, schema_id: int) -> None:
        with self._lock:
            if schema_id in self.schemas:
                self.schemas[schema_id].expanded = not self.schemas[schema_id].expanded
                self._notify("schemas")
    
    def add_aggregator(self, aggregator: Aggregator) -> None:
        with self._lock:
            self.aggregators[aggregator.id] = aggregator
            self._notify("aggregators")
    
    def update_aggregator(self, agg_id: str, rank_count: Optional[int] = None,
                          data_rate: Optional[float] = None, status: Optional[bool] = None) -> None:
        with self._lock:
            if agg_id in self.aggregators:
                if rank_count is not None:
                    self.aggregators[agg_id].rank_count = rank_count
                if data_rate is not None:
                    self.aggregators[agg_id].data_rate = data_rate
                if status is not None:
                    self.aggregators[agg_id].status = status
                self._notify("aggregators")
    
    def add_log(self, entry: LogEntry) -> None:
        with self._lock:
            self.logs.append(entry)
            if len(self.logs) > 100:  # Keep last 100 logs
                self.logs = self.logs[-100:]
            self._notify("logs")

    def log(self, level: LogLevel, message: str) -> None:
        with self._lock:
            self.logs.append(LogEntry(datetime.now(), message, level))
            self._notify("logs")
    
    def add_query(self, query: Query) -> None:
        with self._lock:
            self.queries[query.id] = query
            self._notify("queries")
    
    def update_timestep(self, current: Optional[int] = None, rate: Optional[float] = None,
                        step_time_ms: Optional[int] = None, progress: Optional[float] = None) -> None:
        with self._lock:
            if current is not None:
                self.timestep.current = current
            if rate is not None:
                self.timestep.rate = rate
            if step_time_ms is not None:
                self.timestep.step_time_ms = step_time_ms
            if progress is not None:
                self.timestep.progress = progress
            self._notify("timestep")
    
    def update_status(self, running: Optional[bool] = None, aggregator_count: Optional[int] = None,
                      rank_count: Optional[int] = None, timestep: Optional[int] = None,
                      cpu_usage: Optional[float] = None, connection_status: Optional[str] = None) -> None:
        with self._lock:
            if running is not None:
                self.status.running = running
            if aggregator_count is not None:
                self.status.aggregator_count = aggregator_count
            if rank_count is not None:
                self.status.rank_count = rank_count
            if timestep is not None:
                self.status.timestep = timestep
            if cpu_usage is not None:
                self.status.cpu_usage = cpu_usage
            if connection_status is not None:
                self.status.connection_status = connection_status
            self._notify("status")
    
    def listen(self, state_type: str, callback: Callable) -> None:
        with self._lock:
            if state_type in self._listeners:
                self._listeners[state_type].add(callback)
    
    def remove_listener(self, state_type: str, callback: Callable) -> None:
        with self._lock:
            if state_type in self._listeners:
                self._listeners[state_type].discard(callback)
    
    def _notify(self, state_type: str) -> None:
        if state_type in self._listeners:
            for callback in list(self._listeners[state_type]):
                try:
                    callback()
                except Exception as e:
                    print(f"Error in listener callback: {e}")