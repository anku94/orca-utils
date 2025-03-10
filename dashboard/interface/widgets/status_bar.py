from textual.widgets import Static

from rich.text import Text

from ..state_manager import StateManager

class StatusBar(Static):
    """Status bar showing system stats"""
    
    def __init__(self, state_manager: StateManager, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.state_manager = state_manager
        
    def on_mount(self):
        self.state_manager.listen("status", self.update_display)
        self.update_display()
    
    def update_display(self):
        status = "Running" if self.state_manager.status.running else "Stopped"
        connection = self.state_manager.status.connection_status

        # Set color based on connection status
        if connection == "Connected":
            conn_color = "bright_green"
        elif connection == "Connecting...":
            conn_color = "yellow"
        else:
            conn_color = "red"
        
        # Create status text with colored connection status
        status_obj = self.state_manager.status
        aggcnt = status_obj.aggregator_count
        rankcnt = status_obj.rank_count
        timestep = status_obj.timestep
        cpu = status_obj.cpu_usage

        status_str = ""
        status_str += f"Status: {status} | "
        status_str += f"Aggs: {aggcnt} | "
        status_str += f"Ranks: {rankcnt} | "
        status_str += f"Timestep: {timestep} | "
        status_str += f"CPU: {cpu:.1f}%"
        status_str += f" | Connection status: "

        status_text = Text()
        status_text.append(status_str)
        status_text.append(connection, style=conn_color)
        self.update(status_text)