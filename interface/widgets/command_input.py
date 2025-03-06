from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Input
from textual_autocomplete._autocomplete import AutoComplete, Dropdown, DropdownItem
from datetime import datetime

from ..state_manager import StateManager
from ..protocol import ProtocolHandler
from ..models import LogEntry, LogLevel


class CommandInput(Container):
    """Command input with dropdown autocomplete"""
    
    def __init__(self, state_manager: StateManager, protocol: ProtocolHandler, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.state_manager = state_manager
        self.protocol = protocol
        suggest_list = ["PAUSE", "RESUME"]
        self.suggest_list = [DropdownItem(item) for item in suggest_list]
        self.border_title = "Command"
        self.styles.margin = (1, 1)

    def on_mount(self):
        self.input.focus()
    
    def compose(self) -> ComposeResult:
        # Create an AutoComplete widget with Input and Dropdown
        input_widget = Input(placeholder="Enter command...", id="cmdbox-input")
        dropdown = Dropdown(items=self.suggest_list, id="cmdbox-dropdown")
        
        # Hook up the input submitted event
        input_widget.on_input_submitted = self._on_input_submitted
        
        # Store reference to access it later
        self.input = input_widget
        
        # Yield the AutoComplete widget with its children
        yield AutoComplete(input_widget, dropdown)
    
    def _on_input_submitted(self, event: Input.Submitted) -> None:
        command = event.value.strip()
        
        if command:
            # Log the command
            self.state_manager.add_log(LogEntry(
                timestamp=datetime.now(),
                message=f"> {command}",
                level=LogLevel.DEBUG
            ))
            
            # Send command to protocol handler
            self.protocol.send_command(command)
        
        # Clear input
        self.input.value = ""