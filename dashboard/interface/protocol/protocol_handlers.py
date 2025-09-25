from typing import Dict, List, Callable, ClassVar, Type, Any
from datetime import datetime
from ..models import Schema, Probe, LogLevel, LogEntry
from ..state_manager import StateManager

# Type for handler functions
HandlerFunc = Callable[["ProtocolHandlers", List[str], StateManager], None]

# Dictionary to store registered handlers
_HANDLERS: Dict[str, HandlerFunc] = {}

def handler(message_type: str):
    """Decorator to register a method as a message handler"""
    def decorator(func: HandlerFunc) -> HandlerFunc:
        _HANDLERS[message_type] = func
        return func
    return decorator


class ProtocolHandlers:
    """Container for all protocol message handlers"""
    
    @staticmethod
    def get_handler(message_type: str) -> HandlerFunc:
        """Get the handler for a specific message type"""
        return _HANDLERS.get(message_type)
    
    @staticmethod
    def get_all_handlers() -> Dict[str, HandlerFunc]:
        """Get all registered handlers"""
        return _HANDLERS
    
    def __init__(self, protocol_handler: Any = None):
        """Initialize with an optional reference to the protocol handler"""
        self.protocol_handler = protocol_handler

    @handler("CLEAR")
    def handle_clear(self, parts: List[str], state_manager: StateManager) -> None:
        """Handle CLEAR message
        
        Format: CLEAR
        """
        state_manager.clear()
    
    @handler("CONFIG")
    def handle_config(self, parts: List[str], state_manager: StateManager) -> None:
        """Handle CONFIG message
        
        Format: CONFIG|num_aggs|num_ranks
        """
        num_aggs, num_ranks = int(parts[1]), int(parts[2])
        state_manager.logs = []
        state_manager.update_status(aggregator_count=num_aggs,
                                   rank_count=num_ranks)
    
    @handler("STATUS")
    def handle_status(self, parts: List[str], state_manager: StateManager) -> None:
        """Handle STATUS message
        
        Format: STATUS|status_text
        """
        status_text = parts[1]
        state_manager.update_status(status_text=status_text)

    @handler("REPS_ADD")
    def handle_reps_add(self, parts: List[str], state_manager: StateManager) -> None:
        """Handle REPS_ADD message
        
        Format: REPS_ADD|agg_id|rep_id|mpi_rbeg|mpi_rend
        """
        parts_int = [int(part) for part in parts[1:5]]
        agg_id, rep_id, mpi_rbeg, mpi_rend = parts_int
        log_msg = f"AGG{agg_id}: REP {rep_id} with range [{mpi_rbeg}, {mpi_rend})"
        state_manager.add_log(LogEntry(timestamp=datetime.now(),
                                      message=log_msg,
                                      level=LogLevel.INFO))
        state_manager.add_agg_reps(agg_id, rep_id, mpi_rbeg, mpi_rend)

    @handler("SCHEMA_ADD")
    def handle_schema_add(self, parts: List[str], state_manager: StateManager) -> None:
        """Handle SCHEMA_ADD message (SCHEMA_ADD|schema_name)."""
        schema_name = parts[1]
        state_manager.add_schema(Schema(name=schema_name))
    
    @handler("PROBE_ADD")
    def handle_probe_add(self, parts: List[str], state_manager: StateManager) -> None:
        """Handle PROBE_ADD message
        
        Format: PROBE_ADD|schema_name|probe_id|probe_name|active
        """
        schema_name, probe_id, probe_name = parts[1], parts[2], parts[3]
        active = parts[4].lower() == "true" if len(parts) > 4 else True

        state_manager.add_probe(
            Probe(id=probe_id,
                 schema=schema_name,
                 name=probe_name,
                 active=active))
    
    @handler("TSADV")
    def handle_timestep_advance(self, parts: List[str], state_manager: StateManager) -> None:
        """Handle TSADV message
        
        Format: TSADV|timestamp|from_timestep|to_timestep
        """
        timestamp, from_ts, to_ts = int(parts[1]), int(parts[2]), int(parts[3])

        state_manager.update_timestep(timestamp, from_ts, to_ts)
        state_manager.update_status(timestep=to_ts)

        # Add log entry
        state_manager.add_log(
            LogEntry(timestamp=datetime.now(),
                    message=f"Timestep advanced: {from_ts}→{to_ts}",
                    level=LogLevel.INFO))
    
    @handler("LOG")
    def handle_log(self, parts: List[str], state_manager: StateManager) -> None:
        """Handle LOG message
        
        Format: LOG|timestamp|severity|message
        """
        severity = LogLevel.INFO
        if parts[2].upper() == "WARN":
            severity = LogLevel.WARNING
        elif parts[2].upper() == "ERROR":
            severity = LogLevel.ERROR
        elif parts[2].upper() == "DEBUG":
            severity = LogLevel.DEBUG

        state_manager.add_log(
            LogEntry(
                timestamp=datetime.now(),  # We use client time, not server time
                message=parts[3],
                level=severity)) 