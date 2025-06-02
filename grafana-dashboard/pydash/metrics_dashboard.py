from grafana_foundation_sdk.builders.dashboard import Dashboard
from grafana_foundation_sdk.cog.encoder import JSONEncoder
from grafana_foundation_sdk.models.resource import Manifest, Metadata
from grafana_foundation_sdk.models.dashboard import VariableOption, TemplateVar, VariableType

from src.rpc_panels import RPCPanels
from src.metrics_utils import MetricsUtils


def build_dashboard() -> Dashboard:
    """Build the metrics monitoring dashboard."""
    
    # Create dashboard builder
    builder = (
        Dashboard(
            title="Metrics Monitoring Dashboard",
        )
        .uid("metrics-dashboard")
        .time("now-5m", "now")
        .refresh("5s")
        .tags(["metrics", "monitoring", "orca"])
    )
    
    # Add templating variables
    ovid_variable = TemplateVar(
        name="ovid",
        label="ORCA Overlay OVID",
        type=VariableType.CUSTOM,
        query="CTL, AGG0",
        current=VariableOption(text="CTL", value="CTL", selected=True),
        options=[
            VariableOption(text="CTL", value="CTL", selected=True),
            VariableOption(text="AGG0", value="AGG0", selected=False),
        ],
        multi=False,
        includeAll=False,
    )
    builder.with_template_var(ovid_variable)
    
    # Add RPC bytes panel
    rpc_bytes_panel = RPCPanels.rpc_bytes_panel()
    builder.with_panel(rpc_bytes_panel)
    
    # Add RPC counts panel 
    rpc_counts_panel = RPCPanels.rpc_counts_panel()
    builder.with_panel(rpc_counts_panel)

    return builder


if __name__ == "__main__":
    dashboard = build_dashboard().build()
    manifest = Manifest(
        kind="Dashboard",
        api_version="dashboard.grafana.app/v1beta1",
        metadata=Metadata(name="metrics-dashboard"),
        spec=dashboard,
    )
    encoder = JSONEncoder(sort_keys=True, indent=2)
    print(encoder.encode(manifest))
