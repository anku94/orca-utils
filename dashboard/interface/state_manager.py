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
        self.schemas: Dict[str, Schema] = {}
        self.aggregators: Dict[str, Aggregator] = {}
        self.logs: List[LogEntry] = []
        self.queries: Dict[int, Query] = {}
        self.timestep: TimestepInfo = TimestepInfo()
        self.status: SystemStatus = SystemStatus()
        self.prev_ts_end: int | None = None
        self.all_ts_ends: list[tuple[int, float]] = []
        
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

    def clear(self) -> None:
        with self._lock:
            self.schemas.clear()
            self.aggregators.clear()
            self.logs.clear()
            self.queries.clear()
            self.timestep = TimestepInfo()
            self.status = SystemStatus()
            self._notify("all")
    
    def add_schema(self, schema: Schema) -> None:
        with self._lock:
            self.schemas[schema.name] = schema
            self._notify("schemas")
    
    def add_probe(self, probe: Probe) -> None:
        with self._lock:
            schema = self.schemas.get(probe.schema)
            if schema:
                schema.probes[probe.id] = probe
                self._notify("schemas")
    
    def set_probe_active(self, schema_name: str, probe_id: str, active: bool) -> None:
        with self._lock:
            schema = self.schemas.get(schema_name)
            if schema and probe_id in schema.probes:
                schema.probes[probe_id].active = active
                self._notify("schemas")
    
    def toggle_schema_expanded(self, schema_name: str) -> None:
        with self._lock:
            schema = self.schemas.get(schema_name)
            if schema:
                schema.expanded = not schema.expanded
                self._notify("schemas")
    
    def add_agg_reps(self, agg_id: str, rep_id: int, mpi_rbeg: int, mpi_rend: int) -> None:
        with self._lock:
            if agg_id not in self.aggregators:
                self.aggregators[agg_id] = Aggregator(id=agg_id, address="")

            self.aggregators[agg_id].reps.append((rep_id, mpi_rbeg, mpi_rend))
            rbegprev, rendprev = self.aggregators[agg_id].rank_range
            rbegnew = min(rbegprev, mpi_rbeg)
            rendnew = max(rendprev, mpi_rend)
            self.aggregators[agg_id].rank_range = (rbegnew, rendnew)

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

    def get_logs(self) -> list[str]:
        logs: list[str] = []
        with self._lock:
            for log in self.logs:
                logs.append(f"[{log.formatted_time}] {log.message}")
            self.logs = []
        return logs
    
    def add_query(self, query: Query) -> None:
        with self._lock:
            self.queries[query.id] = query
            self._notify("queries")
    
    def update_timestep(self, timestamp: float, from_ts: int, to_ts: int) -> None:
        with self._lock:
            self.timestep.update(timestamp, from_ts, to_ts)
            self._notify("timestep")
    
    def update_status(self, status_text: Optional[str] = None, aggregator_count: Optional[int] = None,
                      rank_count: Optional[int] = None, timestep: Optional[int] = None,
                      cpu_usage: Optional[float] = None, connection_status: Optional[str] = None) -> None:
        with self._lock:
            if status_text is not None:
                self.status.status_text = status_text
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
        # Determine which listener types to notify
        listener_types = list(self._listeners.keys()) if state_type == "all" else [state_type]
        
        # Notify all applicable listeners
        for type_name in listener_types:
            if type_name in self._listeners:
                for callback in list(self._listeners[type_name]):
                    try:
                        callback()
                    except Exception as e:
                        print(f"Error in listener callback: {e}")