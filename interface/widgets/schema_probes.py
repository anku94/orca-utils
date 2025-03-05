import re
from textual.widget import Widget
from textual.widgets import Static
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Switch
from textual.widgets import Collapsible

from interface.state_manager import StateManager
from interface.models import LogLevel
from textual.reactive import reactive
from interface.models import Schema
from interface.protocol import ProtocolHandler


class SchemaDisplay(Widget):
    schemas: reactive[dict[int, Schema]] = reactive({}, recompose=True)

    def __init__(self, state_manager: StateManager, protocol: ProtocolHandler, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.state_manager = state_manager
        self.state_manager.listen("schemas", self.update_display)
        self.protocol = protocol

    def on_mount(self):
        self.border_title = "Schema Display"

    def compose(self) -> ComposeResult:
        for sid, schema in self.schemas.items():
            heading = f"Schema: {schema.name}"
            with Collapsible(title=heading, collapsed=False):
                for pid, probe in schema.probes.items():
                    yield Horizontal(
                        Switch(animate=False, id=f"s{sid}p{pid}"),
                        Static(f"{probe.name}"),
                        classes="probe-container",
                    )

    def on_switch_changed(self, event: Switch.Changed) -> None:
        switch_id = event.switch.id
        match = re.match(r"s(\d+)p(\d+)", switch_id)
        if not match:
            return
        sid, pid = map(int, match.groups())
        schema = self.schemas[sid]
        probe = schema.probes[pid]
        log_msg = f"Probe {probe.name} in schema {schema.name} switched to {event.switch.value}"
        self.state_manager.log(LogLevel.INFO, log_msg)
        self.protocol.send_toggle_command(sid, pid, event.switch.value)

    def update_display(self):
        self.schemas = self.state_manager.schemas
        self.mutate_reactive(SchemaDisplay.schemas)
