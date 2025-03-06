from textual.content import Content
from textual.widgets import Static

from ..state_manager import StateManager
from textual.widgets import RichLog

class LogStream(RichLog):
    """Widget showing log messages"""

    def __init__(self, state_manager: StateManager, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.state_manager = state_manager
        self.state_manager.listen("logs", self.update_display)

    def on_ready(self) -> None:
        self.write("Log ready")

    def update_display(self):
        logs = self.state_manager.logs
        for log in logs:
            self.write(log.formatted_time, log.message)
