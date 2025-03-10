from textual.app import ComposeResult
from textual.widgets import Static, ProgressBar

from ..state_manager import StateManager


class TimestepWidget(Static):
    """Widget showing timestep progress"""
    
    def __init__(self, state_manager: StateManager, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.state_manager = state_manager
        
    def compose(self) -> ComposeResult:
        self.border_title = "Timestep Progress"
        yield Static(id="timestep_info")
        yield ProgressBar(total=100, show_eta=False, id="progress")
        yield Static(id="timestep_time")
    
    def on_mount(self):
        self.state_manager.listen("timestep", self.update_display)
        self.update_display()
    
    def update_display(self):
        info = self.state_manager.timestep
        
        # Update the info line
        self.query_one("#timestep_info", Static).update(
            f"Current: {info.current}  |  Rate: {info.rate:.1f} ts/sec"
        )
        
        # Update progress bar
        self.query_one("#progress", ProgressBar).update(
            progress=int(info.progress * 100)
        )
        
        # Update time
        self.query_one("#timestep_time", Static).update(
            f"Time in step: {info.step_time_ms}ms"
        )