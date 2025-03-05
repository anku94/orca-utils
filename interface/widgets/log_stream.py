from textual.content import Content
from textual.widgets import Static

from ..state_manager import StateManager

class LogStream(Static):
    """Widget showing log messages"""
    
    def __init__(self, state_manager: StateManager, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.state_manager = state_manager
    
    def on_mount(self):
        self.border_title = "Log Stream"
        self.state_manager.listen("logs", self.update_display)
        self.update_display()
    
    def update_display(self):
        log_entries = []
        
        for entry in self.state_manager.logs[-30:]:  # Show last 30 logs
            log_entry = f"{entry.formatted_time} {entry.message}"
            log_entries.append(log_entry)
        
        try:
            content = Content("\n".join(log_entries))
            self.update(content)
        except Exception as e:
            print("Exception in LogStream.update")
            print(log_entries)
            raise e
