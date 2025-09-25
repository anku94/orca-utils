"""
Test for the decorator-based protocol handlers
"""
import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime

from ..state_manager import StateManager
from ..models import Schema, Probe, LogLevel, LogEntry
from .protocol_handlers import ProtocolHandlers
from .protocol_handler import ProtocolHandler


class TestProtocolHandlers(unittest.TestCase):
    """Test the decorator-based protocol handlers"""

    def setUp(self):
        """Set up the test environment"""
        self.state_manager = MagicMock(spec=StateManager)
        self.protocol_handler = ProtocolHandler(self.state_manager)
        
    def test_handler_registration(self):
        """Test that handlers are registered correctly"""
        # Check that all handlers are registered
        handlers = ProtocolHandlers.get_all_handlers()
        self.assertIn("CONFIG", handlers)
        self.assertIn("STATUS", handlers)
        self.assertIn("SCHEMA_ADD", handlers)
        self.assertIn("PROBE_ADD", handlers)
        self.assertIn("TSADV", handlers)
        self.assertIn("LOG", handlers)
        
    def test_config_handler(self):
        """Test the CONFIG message handler"""
        # Create a message
        message = "CONFIG|2|4"
        parts = message.split('|')
        
        # Get the handler
        handler = ProtocolHandlers.get_handler("CONFIG")
        self.assertIsNotNone(handler)
        
        # Call the handler
        handler_instance = ProtocolHandlers()
        handler(handler_instance, parts, self.state_manager)
        
        # Check that the state manager was updated
        self.state_manager.update_status.assert_called_once_with(
            aggregator_count=2, rank_count=4
        )
        
    def test_schema_add_handler(self):
        """Test the SCHEMA_ADD message handler"""
        # Create a message
        message = "SCHEMA_ADD|TestSchema"
        parts = message.split('|')
        
        # Get the handler
        handler = ProtocolHandlers.get_handler("SCHEMA_ADD")
        self.assertIsNotNone(handler)
        
        # Call the handler
        handler_instance = ProtocolHandlers()
        handler(handler_instance, parts, self.state_manager)
        
        # Check that the state manager was updated
        self.state_manager.add_schema.assert_called_once()
        schema = self.state_manager.add_schema.call_args[0][0]
        self.assertEqual(schema.name, "TestSchema")
        
    def test_protocol_handler_integration(self):
        """Test that the protocol handler correctly uses the decorator-based handlers"""
        # Create a message
        message = "PROBE_ADD|TestSchema|probe-2|TestProbe|true"
        
        # Process the message
        with patch.object(self.state_manager, 'queue_ui_update') as mock_queue:
            self.protocol_handler._process_message(message)
            
            # Check that the handler was queued
            self.assertEqual(mock_queue.call_count, 1)
            
            # Call the queued function
            queued_func = mock_queue.call_args[0][0]
            queued_func()
            
            # Check that the state manager was updated
            self.state_manager.add_probe.assert_called_once()
            probe = self.state_manager.add_probe.call_args[0][0]
            self.assertEqual(probe.id, "probe-2")
            self.assertEqual(probe.schema, "TestSchema")
            self.assertEqual(probe.name, "TestProbe")
            self.assertEqual(probe.active, True)


if __name__ == "__main__":
    unittest.main() 