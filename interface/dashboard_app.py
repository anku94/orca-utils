# dashboard.py
from dataclasses import dataclass
from textual import log as tlog
from textual.app import App
import argparse

from .state_manager import StateManager
from .protocol import ProtocolHandler
from .protocol.transport import MessageReceived, StatusChanged


from .dashboard_screen import MonitoringDashboard

@dataclass
class DashboardAppConfig:
    host: str = "localhost"
    port: int = 8989
    replay_file: str | None = None

def parse_args() -> DashboardAppConfig:
    parser = argparse.ArgumentParser(description="Controller Dashboard")
    parser.add_argument("--host", default="localhost", help="Controller host address")
    parser.add_argument("--port", type=int, default=8989, help="Controller port number") 
    parser.add_argument("-r", "--replay", help="Path to protocol replay file")

    args = parser.parse_args()
    tlog(f"parse_args: args={args}")

    return DashboardAppConfig(host=args.host, port=args.port, replay_file=args.replay)

class DashboardApp(App):
    """Controller Dashboard Application"""
    
    CSS_PATH = "dashboard.tcss"
    TITLE = "Controller Dashboard"
    
    def __init__(self):
        super().__init__()

        config = parse_args()
        self.config = config

        tlog(f"App.__init__: host={config.host}, port={config.port}, replay_file={config.replay_file}")
        self.state_manager = StateManager()
        
        # Determine if we're in replay mode
        self.replay_mode = config.replay_file is not None
        
        # Create protocol handler with appropriate mode
        self.protocol = ProtocolHandler(self.state_manager, use_replay=self.replay_mode)
        
        # Set connection parameters
        self.connect_host = None if self.replay_mode else config.host
        self.connect_port = None if self.replay_mode else config.port
        self.replay_file = config.replay_file
    
    def on_mount(self) -> None:
        """Set up the application when mounted"""
        # Create and push the main dashboard screen
        dashboard = MonitoringDashboard(self.state_manager, self.protocol)
        self.push_screen(dashboard)
        
        # Set the app reference in the protocol handler
        self.protocol.set_app(self)
        
        # Initialize the protocol handler
        self.protocol.initialize()
        
        # Connect to controller or load replay file
        if self.replay_mode and self.replay_file:
            self.run_worker(self.load_replay_file(self.replay_file))
        elif self.connect_host and self.connect_port:
            self.run_worker(self.connect_to_server(self.connect_host, self.connect_port))
    
    async def connect_to_server(self, host: str, port: int) -> bool:
        """Worker function to connect to server"""
        return self.protocol.connect(host, port)
    
    async def load_replay_file(self, file_path: str) -> bool:
        """Worker function to load a replay file"""
        return self.protocol.connect(file_path)
    
    def on_message_received(self, event: MessageReceived) -> None:
        """Handle message received from transport"""
        self.protocol.handle_message_received(event)
    
    def on_status_changed(self, event: StatusChanged) -> None:
        """Handle status changed event"""
        self.protocol.handle_status_changed(event)
    
    def on_unmount(self) -> None:
        """Clean up when app exits"""
        self.protocol.disconnect()


if __name__ == "__main__":
    app = DashboardApp()
    app.run()
