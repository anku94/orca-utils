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
        self._ensure_thread_running(self._connection_thread, self._connection_manager, '_connection_thread')
        
        # Start send thread if not already running
        self._ensure_thread_running(self._send_thread, self._send_loop, '_send_thread')
    
    def _ensure_thread_running(self, thread, target_func, thread_attr_name):
        """Utility to ensure a thread is running"""
        if not thread or not thread.is_alive():
            new_thread = threading.Thread(target=target_func)
            new_thread.daemon = True
            new_thread.start()
            setattr(self, thread_attr_name, new_thread)
    
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
        self._trigger_reconnect()
        return True
    
    def _trigger_reconnect(self):
        """Utility to trigger a reconnection attempt"""
        self._reconnect_event.set()
    
    def disconnect(self) -> None:
        """Disconnect from the server and stop auto-reconnect"""
        self._auto_reconnect = False
        self._stop_event.set()
        self._connected = False
        
        self._close_socket()
        
        # Update connection status
        self._post_status_change("Disconnected")
    
    def _close_socket(self):
        """Utility to safely close the socket"""
        if self._socket:
            try:
                self._socket.close()
            except:
                pass
            self._socket = None
    
    def send(self, message: str) -> None:
        """Queue a message to be sent to the server"""
        if not self._connected and not self._auto_reconnect:
            self._post_status_change("Cannot send: Not connected to server")
            return
        
        # If we're not connected but auto-reconnect is enabled, trigger a reconnect
        if not self._connected and self._auto_reconnect:
            self._trigger_reconnect()
        
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
    
    def _handle_connection_error(self, error, error_context=""):
        """Utility to handle connection errors consistently"""
        self._connected = False
        error_msg = f"{error_context}: {str(error)} ({type(error).__name__})"
        self._post_status_change(error_msg)
        
        # Trigger reconnection if auto-reconnect is enabled
        if self._auto_reconnect:
            self._trigger_reconnect()
        
        # Avoid tight loop on error
        time.sleep(1.0)
    
    def _create_and_connect_socket(self):
        """Utility to create and connect a socket"""
        self._close_socket()
        
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
            self._start_receive_thread()
            
            return True
            
        except socket.error as e:
            # Handle specific socket errors
            error_msg = f"Can't connect to {self._host}:{self._port}"
            if e.errno == 49:  # Can't assign requested address
                error_msg += " - Address not available"
            else:
                error_msg += f" - {str(e)}"
            
            self._post_status_change(error_msg)
            
            # Close the socket and mark as disconnected
            self._close_socket()
            self._connected = False
            return False
    
    def _start_receive_thread(self):
        """Utility to start the receive thread"""
        self._ensure_thread_running(self._receive_thread, self._receive_loop, '_receive_thread')
    
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
                success = self._create_and_connect_socket()
                
                # If connection failed and auto-reconnect is disabled, break the loop
                if not success and not self._auto_reconnect:
                    break
                    
            except Exception as e:
                # Connection failed
                self._handle_connection_error(e, "Connection failed")
                
                # If auto-reconnect is disabled, break the loop
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
                    self._handle_connection_error(e, "Send error")
                    
                    # Put the message back in the queue to retry after reconnection
                    self._send_queue.put(message)
            except Exception as e:
                # Catch any other exceptions to keep the loop running
                self._handle_connection_error(e, "Send loop error")
    
    def _receive_loop(self) -> None:
        """Loop that receives messages from the server"""
        while not self._stop_event.is_set() and self._socket and self._connected:
            try:
                # First read the 4-byte size prefix
                size_bytes = self._receive_exact_bytes(4)
                if not size_bytes:
                    return
                
                # Convert size bytes to integer (big-endian/network byte order)
                message_size = int.from_bytes(size_bytes, byteorder='big')
                
                # Now read exactly message_size bytes
                message_bytes = self._receive_exact_bytes(message_size)
                if not message_bytes:
                    return
                
                # Decode the message and process it
                message = message_bytes.decode('utf-8')
                tlog("Msg received:")
                tlog(message)
                self._post_message_received(message)
            
            except Exception as e:
                # Receive failed - likely a connection issue
                self._handle_connection_error(e, "Receive error")
                break
    
    def _receive_exact_bytes(self, num_bytes):
        """Utility to receive exactly num_bytes from the socket"""
        data = b''
        while len(data) < num_bytes:
            try:
                chunk = self._socket.recv(min(4096, num_bytes - len(data)))
                if not chunk:
                    # Connection closed by server
                    self._handle_connection_error("Connection closed by server", "Server disconnected")
                    return None
                data += chunk
            except Exception as e:
                self._handle_connection_error(e, "Socket read error")
                return None
        return data

