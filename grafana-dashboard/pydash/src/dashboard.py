from grafana_foundation_sdk.builders import dashboard, logs, stat, text, timeseries
from grafana_foundation_sdk.models.dashboard import DashboardCursorSync

from .common import (
    timeseries_panel,
    log_panel,
    stat_panel,
    text_panel,
)
from .rpc_panels import RPCPanels


def metrics_dashboard() -> dashboard.Dashboard:
    """Build the metrics monitoring dashboard with RPC panels."""
    builder = (
        dashboard.Dashboard("Metrics Monitoring Dashboard")
        .uid("metrics-dashboard")
        .tags(["metrics", "monitoring", "orca"])
        .readonly()
        .time("now-5m", "now")
        .tooltip(DashboardCursorSync.CROSSHAIR)
        .refresh("5s")
        .with_panel(RPCPanels.rpc_counts_panel())
        .with_panel(RPCPanels.rpc_bytes_panel())
    )

    return builder