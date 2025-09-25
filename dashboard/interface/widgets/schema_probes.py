import re
from collections import OrderedDict
from textual.widget import Widget
from textual.widgets import Static
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Switch, Collapsible
from textual.reactive import reactive

from interface.state_manager import StateManager
from interface.models import LogLevel, Schema
from interface.protocol import ProtocolHandler


class SchemaDisplay(Widget):
    schemas: reactive[dict[str, Schema]] = reactive({}, recompose=True)

    def __init__(self, state_manager: StateManager, protocol: ProtocolHandler, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.state_manager = state_manager
        self.protocol = protocol
        self.state_manager.listen("schemas", self.update_display)
        self._schema_lookup: dict[int, str] = {}
        self._probe_lookup: dict[tuple[int, int], tuple[str, str]] = {}

    def on_mount(self) -> None:
        self.border_title = "Schema Display"

    def compose(self) -> ComposeResult:
        if not self.schemas:
            yield Static("No schemas found")
            return

        self._schema_lookup.clear()
        self._probe_lookup.clear()

        for sid, (schema_name, schema) in enumerate(self.schemas.items()):
            self._schema_lookup[sid] = schema_name
            heading = f"Schema: {schema.name}"
            with Collapsible(title=heading, collapsed=False):
                for pid, (probe_id, probe) in enumerate(schema.probes.items()):
                    self._probe_lookup[(sid, pid)] = (schema_name, probe_id)
                    yield Horizontal(
                        Switch(
                            animate=False,
                            id=f"s{sid}p{pid}",
                            value=probe.active,
                        ),
                        Static(probe.name),
                        classes="probe-container",
                    )

    def on_switch_changed(self, event: Switch.Changed) -> None:
        match = re.match(r"s(\d+)p(\d+)", event.switch.id or "")
        if not match:
            return

        sid, pid = map(int, match.groups())
        key = self._probe_lookup.get((sid, pid))
        if not key:
            return

        schema_name, probe_id = key
        schema = self.schemas.get(schema_name)
        if not schema:
            return

        probe = schema.probes.get(probe_id)
        if not probe:
            return

        log_msg = f"Probe {probe.name} in schema {schema.name} switched to {event.switch.value}"
        self.state_manager.log(LogLevel.INFO, log_msg)
        self.protocol.send_toggle_command(schema_name, probe_id, event.switch.value)

    def update_display(self) -> None:
        self.schemas = OrderedDict(self.state_manager.schemas)
        self.mutate_reactive(SchemaDisplay.schemas)
