from typing import Dict, List, Callable, Optional
from datetime import datetime
from ..models import Schema, Probe, Aggregator, LogEntry, Query, LogLevel, TimestepInfo, SystemStatus
from ..state_manager import StateManager
from .transport import TCPTransport, MessageReceived, StatusChanged
from .file_replay import FileReplayTransport

# Type for message handler functions
MessageHandler = Callable[[List[str], StateManager], None]


class ProtocolHandler:
    """Handles the application protocol logic, parsing and dispatching messages"""

    def __init__(self, state_manager: StateManager, use_replay: bool = False):
        self.state_manager = state_manager

        # Create the appropriate transport layer
        if use_replay:
            self._transport = FileReplayTransport()
            self._replay_mode = True
        else:
            self._transport = TCPTransport()
            self._replay_mode = False

        # App reference
        self.app = None

        # Dictionary of message handlers
        self._message_handlers: Dict[str, MessageHandler] = {}

        # Register default message handlers
        self._register_default_handlers()

        # Flag to track if we've been initialized
        self._initialized = False

    def initialize(self):
        """Initialize the protocol handler after the app is fully mounted"""
        self._initialized = True
        self._transport.initialize()

    def set_app(self, app):
        """Set the app reference after initialization"""
        self.app = app
        self._transport.set_app(app)

    def _register_default_handlers(self) -> None:
        """Register all the default message handlers"""
        self.register_handler("CONFIG", self._handle_config)
        self.register_handler("STATUS", self._handle_status)
        self.register_handler("SCHEMA_ADD", self._handle_schema_add)
        self.register_handler("PROBE_ADD", self._handle_probe_add)
        self.register_handler("TSADV", self._handle_timestep_advance)
        self.register_handler("LOG", self._handle_log)
        self.register_handler("DATA", self._handle_data)
        self.register_handler("QUERY_ADD", self._handle_query_add)
        self.register_handler("PROBE_STATE", self._handle_probe_state)
        self.register_handler("HEARTBEAT", self._handle_heartbeat)

    def register_handler(self, message_type: str,
                         handler: MessageHandler) -> None:
        """Register a new message handler for a specific message type"""
        self._message_handlers[message_type] = handler

    def unregister_handler(self, message_type: str) -> None:
        """Unregister a message handler"""
        if message_type in self._message_handlers:
            del self._message_handlers[message_type]

    # Transport delegation methods

    def connect(self, host_or_file: str, port: Optional[int] = None) -> bool:
        """Connect to the server or load a replay file"""
        if not self._initialized:
            return False
            
        if self._replay_mode:
            return self._transport.connect(host_or_file)
        else:
            return self._transport.connect(host_or_file, port, auto_reconnect=True)

    def disconnect(self) -> None:
        """Disconnect from the server"""
        self._transport.disconnect()

    def is_connected(self) -> bool:
        """Return the current connection status"""
        return self._transport.is_connected()

    def send_command(self, command: str) -> None:
        """Send a command to the server"""
        self._transport.send(f"COMMAND|{command}")

    # Add these new methods for replay control
    
    def is_replay_mode(self) -> bool:
        """Return whether we're in replay mode"""
        return self._replay_mode
        
    def step_replay(self) -> bool:
        """Step to the next message in replay mode"""
        if not self._replay_mode:
            return False
            
        return self._transport.step_message()

    # Message handling

    def handle_message_received(self, event: MessageReceived) -> None:
        """Handle message received event"""
        self._process_message(event.message)

    def handle_status_changed(self, event: StatusChanged) -> None:
        """Handle status changed event"""
        self._update_connection_status(event.status)

    def _update_connection_status(self, status: str) -> None:
        """Update the connection status in the UI"""
        # Queue the update to be processed in the UI thread
        self.state_manager.queue_ui_update(lambda: self._do_update_connection_status(status))

    def _do_update_connection_status(self, status: str) -> None:
        """Actually update the connection status (called from UI thread)"""
        # Log the connection status
        self.state_manager.add_log(
            LogEntry(timestamp=datetime.now(),
                     message=f"Connection: {status}",
                     level=LogLevel.INFO))

        # Update the status bar with connection information
        self.state_manager.update_status(connection_status=status)

    def _process_message(self, message: str) -> None:
        """Process a received message"""
        parts = message.split('|')
        if not parts:
            return

        msg_type = parts[0]

        try:
            # Look up the handler for this message type
            handler = self._message_handlers.get(msg_type)
            if handler:
                # Queue the handler to be executed in the UI thread
                self.state_manager.queue_ui_update(lambda: handler(parts, self.state_manager))
            else:
                print(f"Unknown message type: {msg_type}")
        except Exception as e:
            print(f"Error processing message '{message}': {e}")

    # Message handlers

    def _handle_config(self, parts: List[str],
                       state_manager: StateManager) -> None:
        # CONFIG|num_aggs|num_ranks
        num_aggs, num_ranks = int(parts[1]), int(parts[2])
        state_manager.logs = []
        state_manager.update_status(aggregator_count=num_aggs,
                                    rank_count=num_ranks)


    def _handle_status(self, parts: List[str],
                       state_manager: StateManager) -> None:
        # STATUS|agg_count|timestep|rank_count|additional_status
        agg_count, timestep, rank_count = int(parts[1]), int(parts[2]), int(
            parts[3])
        status_text = parts[4] if len(parts) > 4 else ""

        state_manager.update_status(running=True,
                                    aggregator_count=agg_count,
                                    rank_count=rank_count,
                                    timestep=timestep)

    def _handle_schema_add(self, parts: List[str],
                           state_manager: StateManager) -> None:
        # SCHEMA_ADD|schema_id|schema_name
        schema_id, schema_name = int(parts[1]), parts[2]
        state_manager.add_schema(Schema(id=schema_id, name=schema_name))

    def _handle_probe_add(self, parts: List[str],
                          state_manager: StateManager) -> None:
        # PROBE_ADD|schema_id|probe_id|probe_name|active
        schema_id, probe_id, probe_name = int(parts[1]), int(
            parts[2]), parts[3]
        active = parts[4].lower() == "true" if len(parts) > 4 else True

        state_manager.add_probe(
            Probe(id=probe_id,
                  schema_id=schema_id,
                  name=probe_name,
                  active=active))

    def _handle_timestep_advance(self, parts: List[str],
                                 state_manager: StateManager) -> None:
        # TSADV|timestamp|from_timestep|to_timestep
        ts, from_step, to_step = int(parts[1]), int(parts[2]), int(parts[3])

        state_manager.update_timestep(current=to_step)
        state_manager.update_status(timestep=to_step)

        # Add log entry
        state_manager.add_log(
            LogEntry(timestamp=datetime.now(),
                     message=f"Timestep advanced: {from_step}→{to_step}",
                     level=LogLevel.INFO))

    def _handle_log(self, parts: List[str],
                    state_manager: StateManager) -> None:
        # LOG|timestamp|severity|message
        severity = LogLevel.INFO
        if parts[2].upper() == "WARN":
            severity = LogLevel.WARNING
        elif parts[2].upper() == "ERROR":
            severity = LogLevel.ERROR
        elif parts[2].upper() == "DEBUG":
            severity = LogLevel.DEBUG

        state_manager.add_log(
            LogEntry(
                timestamp=datetime.now(
                ),  # We use client time, not server time
                message=parts[3],
                level=severity))

    def _handle_data(self, parts: List[str],
                     state_manager: StateManager) -> None:
        # DATA|timestamp|timestep|size_kb|source
        timestep, size_kb, source = int(parts[2]), parts[3], parts[4]

        state_manager.add_log(
            LogEntry(timestamp=datetime.now(),
                     message=
                     f"Received {size_kb} from {source} (timestep {timestep})",
                     level=LogLevel.INFO))

    def _handle_query_add(self, parts: List[str],
                          state_manager: StateManager) -> None:
        # QUERY_ADD|query_id|query_name|query_text
        query_id, query_name, query_text = int(parts[1]), parts[2], parts[3]

        state_manager.add_query(
            Query(id=query_id, name=query_name, text=query_text))

        state_manager.add_log(
            LogEntry(timestamp=datetime.now(),
                     message=f"Query installed: {query_name}",
                     level=LogLevel.INFO))

    def _handle_probe_state(self, parts: List[str],
                            state_manager: StateManager) -> None:
        # PROBE_STATE|probe_id|active
        probe_id, active = int(parts[1]), parts[2].lower() == "true"

        # Find schema_id for this probe
        schema_id = None
        for s_id, schema in state_manager.schemas.items():
            if probe_id in schema.probes:
                schema_id = s_id
                break

        if schema_id is not None:
            state_manager.set_probe_active(probe_id, schema_id, active)

    def _handle_heartbeat(self, parts: List[str],
                          state_manager: StateManager) -> None:
        # Just ignore heartbeats
        pass

