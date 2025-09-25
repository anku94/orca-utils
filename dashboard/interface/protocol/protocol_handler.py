from typing import Dict, List, Callable, Optional
from datetime import datetime
from ..models import Schema, Probe, Aggregator, LogEntry, Query, LogLevel, TimestepInfo, SystemStatus
from ..state_manager import StateManager
from .transport import TCPTransport, MessageReceived, StatusChanged
from .command_protocol import serialize_commands
from .command_defs import COMMAND_METADATA, DEFAULT_DOMAINS
from .file_replay import FileReplayTransport
from .protocol_handlers import ProtocolHandlers

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

        # Create handlers instance
        self.handlers = ProtocolHandlers(self)
        
        # Dictionary of message handlers - populated from the decorator-based handlers
        self._message_handlers: Dict[str, MessageHandler] = {}
        
        # Register handlers from the ProtocolHandlers class
        self._register_handlers()

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

    def _register_handlers(self) -> None:
        """Register all handlers from the ProtocolHandlers class"""
        for message_type, handler_func in ProtocolHandlers.get_all_handlers().items():
            # Create a wrapper that adapts the handler function signature
            # Use a factory function to avoid closure issues
            def create_wrapper(handler_func=handler_func):
                return lambda parts, state_manager: handler_func(self.handlers, parts, state_manager)
            
            self._message_handlers[message_type] = create_wrapper()

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
        tokens = command.split()
        verb = tokens[0].upper() if tokens else ""
        meta = COMMAND_METADATA.get(verb)
        domains = meta.domains if meta else DEFAULT_DOMAINS
        payload = serialize_commands(domains, [command])
        self._transport.send(payload)

    def send_toggle_command(self, schema: str, probe: str, activate: bool) -> None:
        """Send a probe toggle command to the server"""
        op = "ENABLE_PROBE" if activate else "DISABLE_PROBE"
        msg = f"{op}|{schema}|{probe}"
        self.send_command(msg)

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

    # The message handlers have been moved to protocol_handlers.py
