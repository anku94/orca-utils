from grafana_foundation_sdk.builders import dashboard, logs, stat, text, timeseries
from grafana_foundation_sdk.models.dashboard import DashboardCursorSync

from .metric_panels import MetricPanels


def metrics_dashboard() -> dashboard.Dashboard:
    """Build the metrics monitoring dashboard with RPC panels."""
    builder = (
        dashboard.Dashboard("Metrics Monitoring Dashboard")
        .uid("metrics-dashboard")
        .tags(["metrics", "monitoring", "orca"])
        .time("now-5m", "now")
        .tooltip(DashboardCursorSync.CROSSHAIR)
        .refresh("5s")
        # .with_panel(MetricPanels.stat_panel())
        .with_panel(MetricPanels.rpc_counts_panel())
        .with_panel(MetricPanels.rpc_bytes_panel())
        .with_panel(MetricPanels.rpcsz_panel())
        # .with_panel(MetricPanels.table_panel())
        .with_panel(MetricPanels.cpu_usage_panel())
        .with_panel(MetricPanels.flow_exec_datagrid_panel())
        .with_panel(MetricPanels.flow_panel())
        .with_panel(MetricPanels.agg_bufstats_panel())
        .with_panel(MetricPanels.bulk_latency_panel())
        .with_panel(MetricPanels.bulk_qsz_panel())
        .with_panel(MetricPanels.bulk_qcnt_panel())
        .with_panel(MetricPanels.twopc_exec_datagrid_panel())
        .with_panel(MetricPanels.twopc_misc_panel())
    )

    return builder
