import socket
import threading
import queue
import time
from typing import Optional, Callable, Any
from datetime import datetime
from textual.message import Message
from dataclasses import dataclass
from textual import log as tlog

class TransportEvent(Message):
    """Base class for transport events"""
    pass

@dataclass
class MessageReceived(TransportEvent):
    """Event fired when a message is received"""
    message: str

@dataclass
class StatusChanged(TransportEvent):
    """Event fired when connection status changes"""
    status: str

class TCPTransport:
    """Handles low-level TCP communication with size-prefixed messages"""
    
    def __init__(self):
        self._socket: Optional[socket.socket] = None
        self._connected = False
        self._send_queue = queue.Queue()
        self._stop_event = threading.Event()
        self._reconnect_event = threading.Event()
        self._host = ""
        self._port = 0
        self._auto_reconnect = False
        
        # App reference for posting messages
        self.app = None
        
        # Threads
        self._connection_thread: Optional[threading.Thread] = None
        self._receive_thread: Optional[threading.Thread] = None
        self._send_thread: Optional[threading.Thread] = None
        
        # Flag to track if we've been initialized
        self._initialized = False
    
    def set_app(self, app):
        """Set the app reference after initialization"""
        self.app = app
    
    def initialize(self):
        """Initialize the transport after the app is fully mounted"""
        self._initialized = True
        
        # Start the connection manager thread if not already running
        if not self._connection_thread or not self._connection_thread.is_alive():
            self._connection_thread = threading.Thread(target=self._connection_manager)
            self._connection_thread.daemon = True
            self._connection_thread.start()
        
        # Start send thread if not already running
        if not self._send_thread or not self._send_thread.is_alive():
            self._send_thread = threading.Thread(target=self._send_loop)
            self._send_thread.daemon = True
            self._send_thread.start()
    
    def connect(self, host: str, port: int, auto_reconnect: bool = True) -> bool:
        """Connect to the server"""
        if not self._initialized:
            return False
            
        # Validate host and port
        if not host:
            self._post_status_change("Invalid host: empty host name")
            return False
            
        if not isinstance(port, int) or port <= 0 or port > 65535:
            self._post_status_change(f"Invalid port: {port}")
            return False
            
        self._host = host
        self._port = port
        self._auto_reconnect = auto_reconnect
        
        # Trigger an immediate connection attempt
        self._reconnect_event.set()
        return True
    
    def disconnect(self) -> None:
        """Disconnect from the server and stop auto-reconnect"""
        self._auto_reconnect = False
        self._stop_event.set()
        self._connected = False
        
        if self._socket:
            try:
                self._socket.close()
            except:
                pass
            self._socket = None
        
        # Update connection status
        self._post_status_change("Disconnected")
    
    def send(self, message: str) -> None:
        """Queue a message to be sent to the server"""
        if not self._connected and not self._auto_reconnect:
            self._post_status_change("Cannot send: Not connected to server")
            return
        
        # If we're not connected but auto-reconnect is enabled, trigger a reconnect
        if not self._connected and self._auto_reconnect:
            self._reconnect_event.set()
        
        # Queue the message regardless - it will be sent once connected
        self._send_queue.put(message)
    
    def is_connected(self) -> bool:
        """Return the current connection status"""
        return self._connected
    
    def _post_message_received(self, message: str):
        """Post a message received event"""
        if self.app:
            self.app.post_message(MessageReceived(message))
    
    def _post_status_change(self, status: str):
        """Post a status changed event"""
        if self.app:
            self.app.post_message(StatusChanged(status))
    
    def _connection_manager(self) -> None:
        """Manages connection and reconnection attempts"""
        while not self._stop_event.is_set():
            # Wait for a reconnect event or timeout (for periodic reconnect attempts)
            self._reconnect_event.wait(timeout=1.0)
            self._reconnect_event.clear()
            
            # If we're already connected or stopping, skip this attempt
            if self._connected or self._stop_event.is_set():
                continue
            
            # Update connection status
            self._post_status_change("Connecting...")
            
            # Attempt to connect
            try:
                # Close any existing socket
                if self._socket:
                    try:
                        self._socket.close()
                    except:
                        pass
                    self._socket = None
                
                # Create a new socket and connect
                self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self._socket.settimeout(5.0)  # Set a timeout for the connection attempt
                
                try:
                    # Try to connect to the server
                    self._socket.connect((self._host, self._port))
                    self._socket.settimeout(None)  # Reset timeout for normal operation
                    self._connected = True
                    
                    # Update connection status
                    self._post_status_change("Connected")
                    
                    # Start receive thread
                    if self._receive_thread and self._receive_thread.is_alive():
                        # Wait for old thread to terminate
                        self._receive_thread.join(timeout=1.0)
                    
                    self._receive_thread = threading.Thread(target=self._receive_loop)
                    self._receive_thread.daemon = True
                    self._receive_thread.start()
                    
                except socket.error as e:
                    # Handle specific socket errors
                    if e.errno == 49:  # Can't assign requested address
                        self._post_status_change(f"Can't connect to {self._host}:{self._port} - Address not available")
                    else:
                        self._post_status_change(f"Socket error: {str(e)} (errno: {e.errno})")
                    
                    # Close the socket and mark as disconnected
                    try:
                        self._socket.close()
                    except:
                        pass
                    self._socket = None
                    self._connected = False
                    
                    # If auto-reconnect is disabled, break the loop
                    if not self._auto_reconnect:
                        break
                    
                    # Skip the rest of this iteration
                    continue
            
            except Exception as e:
                # Connection failed
                self._connected = False
                error_msg = f"Connection failed: {str(e)} ({type(e).__name__})"
                self._post_status_change(error_msg)
                
                # If auto-reconnect is enabled, we'll try again on the next loop iteration
                if not self._auto_reconnect:
                    break
    
    def _send_loop(self) -> None:
        """Loop that sends queued messages to the server"""
        while not self._stop_event.is_set():
            try:
                # Wait for a message to send with a timeout
                try:
                    message = self._send_queue.get(timeout=0.1)
                except queue.Empty:
                    continue
                
                try:
                    if self._socket and self._connected:
                        # Encode the message to bytes
                        message_bytes = message.encode('utf-8')
                        # Create size prefix (4 bytes, network byte order)
                        size_prefix = len(message_bytes).to_bytes(4, byteorder='big')
                        
                        # Send size prefix followed by the message
                        self._socket.sendall(size_prefix)
                        self._socket.sendall(message_bytes)
                except Exception as e:
                    # Send failed - likely a connection issue
                    self._connected = False
                    self._post_status_change(f"Send error: {str(e)}")
                    
                    # Trigger reconnection if auto-reconnect is enabled
                    if self._auto_reconnect:
                        self._reconnect_event.set()
                    
                    # Put the message back in the queue to retry after reconnection
                    self._send_queue.put(message)
                    
                    # Avoid tight loop on error
                    time.sleep(1.0)
            except Exception as e:
                # Catch any other exceptions to keep the loop running
                self._post_status_change(f"Send loop error: {str(e)}")
                time.sleep(1.0)
    
    def _receive_loop(self) -> None:
        """Loop that receives messages from the server"""
        while not self._stop_event.is_set() and self._socket and self._connected:
            try:
                # First read the 4-byte size prefix
                size_bytes = b''
                while len(size_bytes) < 4:
                    chunk = self._socket.recv(4 - len(size_bytes))
                    if not chunk:
                        # Connection closed by server
                        self._connected = False
                        self._post_status_change("Connection closed by server")
                        
                        # Trigger reconnection if auto-reconnect is enabled
                        if self._auto_reconnect:
                            self._reconnect_event.set()
                        
                        return
                    size_bytes += chunk
                
                # Convert size bytes to integer (big-endian/network byte order)
                message_size = int.from_bytes(size_bytes, byteorder='big')
                
                # Now read exactly message_size bytes
                message_bytes = b''
                while len(message_bytes) < message_size:
                    chunk = self._socket.recv(min(4096, message_size - len(message_bytes)))
                    if not chunk:
                        # Connection closed by server
                        self._connected = False
                        self._post_status_change("Connection closed by server")
                        
                        # Trigger reconnection if auto-reconnect is enabled
                        if self._auto_reconnect:
                            self._reconnect_event.set()
                        
                        return
                    message_bytes += chunk
                
                # Decode the message and process it
                message = message_bytes.decode('utf-8')
                tlog("Msg received:")
                tlog(message)
                self._post_message_received(message)
            
            except Exception as e:
                # Receive failed - likely a connection issue
                self._connected = False
                self._post_status_change(f"Receive error: {str(e)}")
                
                # Trigger reconnection if auto-reconnect is enabled
                if self._auto_reconnect:
                    self._reconnect_event.set()
                
                # Avoid tight loop on error
                time.sleep(1.0)
                break

