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
        cur_ts = info.cur_ts
        self.query_one("#timestep_info", Static).update(f"Current: {cur_ts}")
        