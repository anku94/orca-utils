
from textual.widgets import Tree
from textual.widgets.tree import TreeNode

from textual import log
from textual.reactive import reactive
from typing import Dict

from ..models import Schema
from ..state_manager import StateManager



class SchemaProbeTree(Tree):
    """Tree view of schemas and probes"""

    schemas: reactive[Dict[str, Schema]] = reactive({})
    
    def __init__(self, state_manager: StateManager, *args, **kwargs):
        super().__init__("Schemas & Probes", *args, **kwargs)
        self.state_manager = state_manager
        self.schema_nodes: Dict[str, TreeNode] = {}
    
    def on_mount(self):
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
        schema_names_added = set()  # Track which schemas we've already added
        for schema_name, schema in self.state_manager.schemas.items():
            if schema_name in schema_names_added:
                log(f"WARNING: Duplicate schema name {schema_name} detected!")
                continue
                
            log(f"Adding schema node: {schema_name}")
            node = self.root.add(schema.name, expand=True)
            self.schema_nodes[schema_name] = node
            schema_names_added.add(schema_name)

        # add all probe nodes
        for schema_name, schema in self.state_manager.schemas.items():
            if schema_name not in self.schema_nodes:
                log(f"Schema {schema_name} not in schema_nodes dictionary!")
                continue
                
            schema_node = self.schema_nodes[schema_name]
            for probe_id, probe in schema.probes.items():
                log(f"Adding probe node: {probe_id} ({probe.name}) to schema {schema_name}")
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
            for schema_name, schema_node in self.schema_nodes.items():
                if schema_node == node:
                    self.state_manager.toggle_schema_expanded(schema_name)
                    break