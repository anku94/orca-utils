# widgets.py
from textual.app import App, ComposeResult
from textual.content import Content
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, DataTable, Footer, Header, Input, Static, Tree, ProgressBar
from textual.widgets.tree import TreeNode
from textual import log
from rich.text import Text
from rich.markup import escape as rescape
from textual.reactive import reactive
from textual.binding import Binding
import time
from typing import Dict, Set, List, Optional, Callable
from datetime import datetime

from .models import Schema, Probe, Aggregator, LogEntry, LogLevel, Query, TimestepInfo, SystemStatus
from .state_manager import StateManager
from .protocol import ProtocolHandler


class StatusBar(Static):
    """Status bar showing system stats"""
    
    def __init__(self, state_manager: StateManager, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.state_manager = state_manager
        
    def on_mount(self):
        self.styles.background = "blue"
        self.styles.color = "white"
        self.styles.padding = (0, 1)
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


class SchemaProbeTree(Tree):
    """Tree view of schemas and probes"""

    schemas: reactive[Dict[int, Schema]] = reactive({})
    
    def __init__(self, state_manager: StateManager, *args, **kwargs):
        super().__init__("Schemas & Probes", *args, **kwargs)
        self.state_manager = state_manager
        self.schema_nodes: Dict[int, TreeNode] = {}
    
    def on_mount(self):
        self.styles.padding = (1, 1)
        self.border_title = "Schemas & Probes"
        self.state_manager.listen("schemas", self.update_display)

    def rebuild_tree(self):
        # Add debugging
        log(f"rebuild_tree called. Current schemas: {list(self.state_manager.schemas.keys())}")
        
        # Clear all nodes from the tree
        log(f"Removing {len(list(self.root.children))} existing nodes")
        for node in list(self.root.children):  # Create a copy of the list to safely iterate
            node.remove()

        # Clear the schema_nodes dictionary
        self.schema_nodes.clear()

        # add all schema nodes
        schema_ids_added = set()  # Track which schemas we've already added
        for schema_id, schema in self.state_manager.schemas.items():
            if schema_id in schema_ids_added:
                log(f"WARNING: Duplicate schema ID {schema_id} ({schema.name}) detected!")
                continue
                
            log(f"Adding schema node: {schema_id} ({schema.name})")
            node = self.root.add(schema.name, expand=True)
            self.schema_nodes[schema_id] = node
            schema_ids_added.add(schema_id)

        # add all probe nodes
        for schema_id, schema in self.state_manager.schemas.items():
            if schema_id not in self.schema_nodes:
                log(f"Schema {schema_id} not in schema_nodes dictionary!")
                continue
                
            schema_node = self.schema_nodes[schema_id]
            for probe_id, probe in schema.probes.items():
                log(f"Adding probe node: {probe_id} ({probe.name}) to schema {schema_id}")
                schema_node.add(probe.name, expand=True)

        self.root.expand_all()
        log(f"Tree rebuild complete. Added {len(self.schema_nodes)} schema nodes")
    
    def update_display(self):
        # Add debugging to track when this is called
        log(f"update_display called for SchemaProbeTree")
        log(f"State manager schemas: {list(self.state_manager.schemas.keys())}")
        self.rebuild_tree()

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Handle node selection to toggle expand/collapse for schemas"""
        node = event.node
        
        # Toggle schema expansion
        if node.parent == self.root:
            # This is a schema node, find its ID
            for schema_id, schema_node in self.schema_nodes.items():
                if schema_node == node:
                    self.state_manager.toggle_schema_expanded(schema_id)
                    break



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


class AggregatorsWidget(Static):
    """Widget showing aggregator status"""
    
    def __init__(self, state_manager: StateManager, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.state_manager = state_manager
        self.table = DataTable()
    
    def compose(self) -> ComposeResult:
        self.border_title = "Aggregators"
        self.table.add_columns("Aggregator", "Ranks", "Data Rate", "Status")
        yield self.table
    
    def on_mount(self):
        self.state_manager.listen("aggregators", self.update_display)
        self.update_display()
    
    def update_display(self):
        # Clear and rebuild table
        self.table.clear()
        
        for agg_id, agg in sorted(self.state_manager.aggregators.items()):
            status = "✓" if agg.status else "✗"
            self.table.add_row(
                agg_id,
                f"{agg.rank_count} ranks",
                f"{agg.data_rate:.1f} MB/s",
                status
            )

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
            color = "blue"
            if entry.level == LogLevel.WARNING:
                color = "yellow"
            elif entry.level == LogLevel.ERROR:
                color = "red"
            elif entry.level == LogLevel.DEBUG:
                color = "grey"
            
            # log_entries.append(f"{entry.formatted_time} [{color}]{entry.message}[/{color}]")
            # log_entry = f"{rescape(entry.formatted_time)} [{color}]{rescape(entry.message)}[/{color}]"
            log_entry = f"{entry.formatted_time} {entry.message}"
            log_entries.append(log_entry)
        
        try:
            content = Content("\n".join(log_entries))
            self.update(content)
        except Exception as e:
            print("Exception in LogStream.update")
            print(log_entries)
            raise e

class CommandInput(Input):
    """Command input field"""
    
    def __init__(self, state_manager: StateManager, protocol: ProtocolHandler, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.state_manager = state_manager
        self.protocol = protocol
        self.placeholder = "Enter command..."
    
    def on_mount(self):
        self.border_title = "Command"
        self.styles.margin = (1, 1)
        self.focus()
    
    def on_input_submitted(self, event: Input.Submitted) -> None:
        command = event.value.strip()
        
        if command:
            # Log the command
            self.state_manager.add_log(LogEntry(
                timestamp=datetime.now(),
                message=f"> {command}",
                level=LogLevel.DEBUG
            ))
            
            # Send command to protocol handler
            self.protocol.send_command(command)
        
        # Clear input
        self.value = ""
