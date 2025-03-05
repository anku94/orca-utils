from textual.app import Screen
from textual.binding import Binding
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical

from .widgets import (
    StatusBar,
    SchemaDisplay,
    TimestepWidget,
    AggregatorsWidget,
    LogStream,
    CommandInput
)
from .protocol import ProtocolHandler
from .state_manager import StateManager

class MonitoringDashboard(Screen):
    """Main dashboard screen"""
    
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("?", "toggle_help", "Help"),
        Binding("s", "step_replay", "Step Replay"),
    ]
    
    def __init__(self, state_manager: StateManager, protocol: ProtocolHandler):
        super().__init__()
        self.state_manager = state_manager
        self.protocol = protocol
    
    def compose(self) -> ComposeResult:
        """Create the UI layout"""
        yield StatusBar(self.state_manager, id="status_bar")
        
        with Horizontal():
            # Left panel
            # yield SchemaProbeTree(self.state_manager, id="schema_tree")
            yield SchemaDisplay(self.state_manager, self.protocol, id="schema_display")
            # Right panel with multiple widgets
            with Vertical():
                yield TimestepWidget(self.state_manager, id="timestep_widget")
                yield AggregatorsWidget(self.state_manager, id="aggregators_widget")
                yield LogStream(self.state_manager, id="log_stream")
        
        yield CommandInput(self.state_manager, self.protocol, id="cmdbox")
    
    def on_mount(self) -> None:
        """Set up the screen when mounted"""
        # Process UI updates on a timer
        self.set_interval(1/60, self.process_ui_updates)
    
    def process_ui_updates(self) -> None:
        """Process any queued UI updates"""
        self.state_manager.process_ui_updates()
        
    def action_step_replay(self) -> None:
        """Step through the replay file when 's' is pressed"""
        self.protocol.step_replay()