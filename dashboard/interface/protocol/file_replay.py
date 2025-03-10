import os
import time
import threading
from typing import Optional, List
from textual import log as tlog

from .transport import MessageReceived, StatusChanged

class FileReplayTransport:
    """Simulates a transport by replaying messages from a file"""
    
    def __init__(self):
        self._file_path: Optional[str] = None
        self._messages: List[str] = []
        self._current_index: int = 0
        self._connected = False
        self._app = None
        self._initialized = False
        
        # Replay control
        self._replay_thread = None
        self._stop_event = threading.Event()
        self._replay_interval = 0.1  # 100ms between messages
    
    def set_app(self, app):
        """Set the app reference after initialization"""
        self._app = app
    
    def initialize(self):
        """Initialize the transport after the app is fully mounted"""
        self._initialized = True
    
    def connect(self, file_path: str, *args, **kwargs) -> bool:
        """Load messages from a file instead of connecting to a server"""
        if not self._initialized:
            return False
            
        try:
            if not os.path.exists(file_path):
                self._post_status_change(f"File not found: {file_path}")
                return False
                
            with open(file_path, 'r') as f:
                self._messages = [line.strip() for line in f if line.strip()]
            
            self._file_path = file_path
            self._current_index = 0
            self._connected = True
            
            self._post_status_change(f"Loaded {len(self._messages)} messages from {file_path}")
            
            # Start the replay thread
            self._stop_event.clear()
            self._replay_thread = threading.Thread(target=self._replay_loop)
            self._replay_thread.daemon = True
            self._replay_thread.start()
            
            return True
            
        except Exception as e:
            self._post_status_change(f"Error loading file: {str(e)}")
            return False
    
    def disconnect(self) -> None:
        """Clear the loaded messages and stop replay"""
        # Stop the replay thread
        if self._replay_thread and self._replay_thread.is_alive():
            self._stop_event.set()
            self._replay_thread.join(timeout=1.0)
            self._replay_thread = None
        
        self._file_path = None
        self._messages = []
        self._current_index = 0
        self._connected = False
    
    def send(self, message: str) -> None:
        """In replay mode, sending is just logged but not processed"""
        tlog(f"[REPLAY] Would send: {message}")
    
    def is_connected(self) -> bool:
        """Return whether a file is loaded"""
        return self._connected
    
    def step_message(self) -> bool:
        """Process the next message in the file (manual stepping)"""
        if not self._connected or not self._messages:
            return False
            
        if self._current_index >= len(self._messages):
            self._post_status_change("End of replay file reached")
            return False
            
        message = self._messages[self._current_index]
        self._current_index += 1
        
        # Post the message as if it was received from a server
        self._post_message_received(message)
        return True
    
    def _replay_loop(self) -> None:
        """Automatically replay messages at regular intervals"""
        while not self._stop_event.is_set() and self._connected:
            if self._current_index < len(self._messages):
                # Get the next message
                message = self._messages[self._current_index]
                self._current_index += 1
                
                # Post the message
                self._post_message_received(message)
                
                # Log progress
                if self._current_index % 10 == 0 or self._current_index == len(self._messages):
                    self._post_status_change(f"Replayed {self._current_index}/{len(self._messages)} messages")
                
                # Wait for the next interval
                time.sleep(self._replay_interval)
            else:
                # End of file reached
                self._post_status_change("End of replay file reached")
                break
    
    def _post_message_received(self, message: str):
        """Post a message received event"""
        if self._app:
            self._app.post_message(MessageReceived(message))
    
    def _post_status_change(self, status: str):
        """Post a status changed event"""
        if self._app:
            self._app.post_message(StatusChanged(status))