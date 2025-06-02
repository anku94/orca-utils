"""
RPC-related panels for the metrics dashboard.
"""

from typing import Dict, Any, Optional
from grafana_foundation_sdk.builders import timeseries
from grafana_foundation_sdk.models import dashboard
from grafana_foundation_sdk.models.common import (
    AxisPlacement,
    AxisColorMode,
    BarAlignment,
    GraphDrawStyle,
    LineInterpolation,
    StackingMode,
    GraphGradientMode,
    GraphThresholdsStyleMode,
    VisibilityMode,
    ScaleDistribution,
    LegendDisplayMode,
    LegendPlacement,
    TooltipDisplayMode,
    DataQuery,
)
from grafana_foundation_sdk.cog import builder as cogbuilder
from .metrics_utils import MetricsUtils
from .fsql_dataquery import FsqlDataQuery


class RPCPanels:
    """Factory class for RPC-related dashboard panels."""

    @staticmethod
    def get_sql_target(query_text: str, ref_id: str) -> FsqlDataQuery:
        """
        Creates a FlightSQL target for a given query text and reference ID.
        """
        sql_target = (
            FsqlDataQuery()
            .ref_id(ref_id)
            .datasource(MetricsUtils.flightsql_datasource_ref())
            .query_text(query_text)
            .format("table")
            .raw_query(True)
            .raw_editor(True)
        )
        return sql_target

    @classmethod
    def rpc_bytes_panel(cls) -> timeseries.Panel:
        """
        Creates the RPC bytes/s panel.
        Displays RPC bytes per second with 3-second rolling average.
        """

        # SQL query equivalent to the Jsonnet version
        query_text = """
        SELECT 
          timestamp, 
          ovid, 
          metric_name, 
          AVG(metric_val) OVER (
            PARTITION BY ovid
            ORDER BY timestamp
            RANGE BETWEEN INTERVAL '3s' PRECEDING AND CURRENT ROW
          ) AS avg_metric_val
        FROM orca_metrics
        WHERE $__timeFilter(timestamp) AND metric_name = 'HGRPC_RATE_BYTES'
        """

        # Create proper transformations using DataTransformerConfig
        partition_transform = dashboard.DataTransformerConfig(
            id_val="partitionByValues",
            options={"fields": ["ovid"], "keepFields": False},
        )

        rename_transform = dashboard.DataTransformerConfig(
            id_val="renameByRegex",
            options={"regex": "metric_val (.*)", "renamePattern": "$1"},
        )

        # Create the timeseries panel using proper SDK methods
        panel = (
            timeseries.Panel()
            .title("RPC bytes/s")
            .datasource(MetricsUtils.flightsql_datasource_ref())
            .unit("Bps")  # bytes per second
            .height(8)
            .span(12)
            .transformations([partition_transform, rename_transform])
            .with_target(cls.get_sql_target(query_text, "rpcBytes"))
            .grid_pos(dashboard.GridPos(h=8, w=12, x=0, y=8))
        )

        return panel

    @classmethod
    def rpc_counts_panel(cls) -> timeseries.Panel:
        """
        Creates the RPC counts/s panel.
        Displays RPC counts per second with 3-second rolling average.
        """

        # SQL query for RPC counts
        query_text = """
        SELECT timestamp, 
          ovid, 
          metric_name, 
          AVG(metric_val) OVER (
            PARTITION BY ovid
            ORDER BY timestamp
            RANGE BETWEEN INTERVAL '3s' PRECEDING AND CURRENT ROW
          ) AS avg_metric_val
        FROM orca_metrics
        WHERE $__timeFilter(timestamp) AND metric_name = 'HGRPC_RATE_COUNT'
        """

        # Create proper transformations using DataTransformerConfig
        partition_transform = dashboard.DataTransformerConfig(
            id_val="partitionByValues",
            options={"fields": ["ovid"], "keepFields": False},
        )

        rename_transform = dashboard.DataTransformerConfig(
            id_val="renameByRegex",
            options={"regex": "metric_val (.*)", "renamePattern": "$1"},
        )

        # Create the timeseries panel using proper SDK methods
        panel = (
            timeseries.Panel()
            .title("RPC counts/s")
            .datasource(MetricsUtils.flightsql_datasource_ref())
            .unit("mps")  # messages per second
            .height(8)
            .span(12)
            .transformations([partition_transform, rename_transform])
            .with_target(cls.get_sql_target(query_text, "rpcCounts"))
            .grid_pos(dashboard.GridPos(h=8, w=12, x=0, y=16))
        )

        return panel
