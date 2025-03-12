from textual.app import Screen
from textual.binding import Binding
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, Container
from textual.widgets import (
    Log,
    TabPane,
    TabbedContent,
    Placeholder
)
from .widgets import (
    StatusBar,
    SchemaDisplay,
    TimestepWidget,
    AggregatorsWidget,
    CommandInput,
    Orca
)
from textual_plotext import PlotextPlot
from .protocol import ProtocolHandler
from .state_manager import StateManager
import numpy as np

class MainTab(Container):
    def __init__(self, state_manager: StateManager, protocol: ProtocolHandler):
        super().__init__()
        self.state_manager = state_manager
        self.protocol = protocol
    
    def compose(self) -> ComposeResult:
        with Horizontal():
            yield SchemaDisplay(self.state_manager, self.protocol, id="schema_display")
            with Vertical():
                yield TimestepWidget(self.state_manager, id="timestep_widget")
                yield AggregatorsWidget(self.state_manager, id="aggregators_widget")
                yield Log(id="log_stream", auto_scroll=True)

class PlotsTab(Container):
    def __init__(self, state_manager: StateManager, protocol: ProtocolHandler):
        super().__init__()
        self.state_manager = state_manager
        self.state_manager.listen("timestep", self.update_plot)
        self.protocol = protocol
    
    def compose(self) -> ComposeResult:
        yield Placeholder(id="plot")

    def on_mount(self) -> None:
        pass

    def update_plot(self):
        pass

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
        yield CommandInput(self.state_manager, self.protocol, id="cmdbox")
        with TabbedContent(initial="main_tab"):
            with TabPane(title="Main", id="main_tab"):
                yield MainTab(self.state_manager, self.protocol)
            with TabPane(title="Plots", id="plots_tab"):
                yield PlotsTab(self.state_manager, self.protocol)
        # with Horizontal():
        #     # Left panel
        #     # yield SchemaProbeTree(self.state_manager, id="schema_tree")
        #     yield SchemaDisplay(self.state_manager, self.protocol, id="schema_display")
        #     # Right panel with multiple widgets
        #     with Vertical():
        #         yield TimestepWidget(self.state_manager, id="timestep_widget")
        #         yield AggregatorsWidget(self.state_manager, id="aggregators_widget")
        #         yield Log(id="log_stream", auto_scroll=True)
        yield StatusBar(self.state_manager, id="status_bar")
        

    def update_logs(self):
        log_lines = self.state_manager.get_logs()
        log = self.query_one(Log)
        log.write_lines(log_lines)
    
    def on_mount(self) -> None:
        """Set up the screen when mounted"""
        # Process UI updates on a timer
        self.set_interval(1/60, self.process_ui_updates)

    def process_ui_updates(self) -> None:
        """Process any queued UI updates"""
        self.state_manager.process_ui_updates()
        self.update_logs()
        
    def action_step_replay(self) -> None:
        """Step through the replay file when 's' is pressed"""
        self.protocol.step_replay()