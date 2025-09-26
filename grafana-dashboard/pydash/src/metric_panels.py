"""
RPC-related panels for the metrics dashboard.
"""

from grafana_foundation_sdk.models import common as gfmc
from grafana_foundation_sdk.builders import common as gfbc
from grafana_foundation_sdk.builders import timeseries as gfb_timeseries
from grafana_foundation_sdk.builders import table as gfb_table
from grafana_foundation_sdk.builders import stat as gfb_stat
from grafana_foundation_sdk.builders import datagrid as gfb_datagrid
from grafana_foundation_sdk.models import dashboard as gfm_dash

from .utils import Utils
from .fsql_dataquery import FsqlDataQuery


class MetricPanels:
    """Factory class for RPC-related dashboard panels."""

    @staticmethod
    def get_sql_target(query_text: str, ref_id: str) -> FsqlDataQuery:
        """
        Creates a FlightSQL target for a given query text and reference ID.
        """
        sql_target = (
            FsqlDataQuery()
            .ref_id(ref_id)
            .datasource(Utils.fsql_ref())
            .query_text(query_text)
            .format("table")
            .raw_query(True)
            .raw_editor(True)
        )
        return sql_target

    @classmethod
    def rpc_bytes_panel(cls) -> gfb_timeseries.Panel:
        # SQL query equivalent to the Jsonnet version
        query_text = """
        SELECT 
          timestamp, 
          ovid, 
          metric_name, 
          AVG(metric_val) OVER (
            PARTITION BY ovid, metric_name
            ORDER BY timestamp
            RANGE BETWEEN INTERVAL '4s' PRECEDING AND CURRENT ROW
          ) AS avg_metric_val
        FROM orca_metrics
        WHERE $__timeFilter(timestamp) AND metric_name = 'HGRPC_RATE_BYTES'
        """

        all_xf = [
            Utils.partition_by_cols_xf(["ovid"]),
            Utils.rename_by_regex_xf("avg_metric_val (.*)", "$1"),
        ]

        # Create the timeseries panel using proper SDK methods
        panel = (
            gfb_timeseries.Panel()
            .title("RPC bytes/s")
            .datasource(Utils.fsql_ref())
            .unit("Bps")  # bytes per second
            .height(8)
            .span(12)
            .tooltip(Utils.default_tooltip())
            .legend(Utils.default_legend())
            .transformations(all_xf)
            .with_target(cls.get_sql_target(query_text, "rpcBytes"))
        )

        return panel

    @classmethod
    def rpc_counts_panel(cls) -> gfb_timeseries.Panel:
        # SQL query for RPC counts
        query_text = """
        SELECT timestamp, 
          ovid, 
          metric_name, 
          AVG(metric_val) OVER (
            PARTITION BY ovid, metric_name
            ORDER BY timestamp
            RANGE BETWEEN INTERVAL '4s' PRECEDING AND CURRENT ROW
          ) AS avg_metric_val
        FROM orca_metrics
        WHERE $__timeFilter(timestamp) AND metric_name = 'HGRPC_RATE_COUNT'
        """

        all_xf = [
            Utils.partition_by_cols_xf(["ovid"]),
            Utils.rename_by_regex_xf("avg_metric_val (.*)", "$1"),
        ]

        # Create the timeseries panel using proper SDK methods
        panel = (
            gfb_timeseries.Panel()
            .title("RPC counts/s")
            .datasource(Utils.fsql_ref())
            .unit("mps")  # messages per second
            .height(8)
            .span(12)
            .tooltip(Utils.default_tooltip())
            .legend(Utils.default_legend())
            .transformations(all_xf)
            .with_target(cls.get_sql_target(query_text, "rpcCounts"))
        )

        return panel

    @classmethod
    def rpcsz_panel(cls) -> gfb_timeseries.Panel:
        query_text = """
        SELECT 
          timestamp, 
          ovid, 
          metric_name, 
          AVG(metric_val) OVER (
            PARTITION BY ovid
            ORDER BY timestamp
            RANGE BETWEEN INTERVAL '1s' PRECEDING AND CURRENT ROW
          ) AS avg_metric_val
        FROM orca_metrics
        WHERE $__timeFilter(timestamp) AND metric_name LIKE 'HGRPC_RPCSZ_AVG'
        """

        all_xf = [
            Utils.partition_by_cols_xf(["ovid", "metric_name"]),
            Utils.rename_by_regex_xf(
                "avg_metric_val {metric_name=\"HGRPC_RPCSZ_(.*)\", ovid=\"(.*)\"}",
                "$2-$1"
            ),
        ]

        panel = (
            gfb_timeseries.Panel()
            .title("RPC size")
            .datasource(Utils.fsql_ref())
            .with_target(cls.get_sql_target(query_text, "rpcsz"))
            .height(8)
            .span(8)
            .transformations(all_xf)
            .unit("bytes")
            .tooltip(Utils.default_tooltip())
            .legend(Utils.default_legend())
        )

        return panel

    @classmethod
    def table_panel(cls) -> gfb_table.Panel:
        query_text = """
        SELECT * FROM orca_flowexec_stats
        WHERE metric_name LIKE 'FLOW_%'
        """

        query_text = """
        SELECT DISTINCT(metric_name) FROM orca_metrics
        WHERE metric_name LIKE '%_CPU_PCT'
        AND ovid != 'INVALID_AGG'
        """

        panel = (
            gfb_table.Panel()
            .title("Another Table Panel")
            .datasource(Utils.fsql_ref())
            .with_target(cls.get_sql_target(query_text, "anotherTablePanel"))
            .height(8)
            .span(12)
        )

        return panel

    @classmethod
    def cpu_usage_panel(cls) -> gfb_timeseries.Panel:
        query_text = """
        SELECT 
          timestamp, 
          ovid, 
          metric_name, 
          AVG(metric_val) OVER (
            PARTITION BY ovid, metric_name
            ORDER BY timestamp
            RANGE BETWEEN INTERVAL '3s' PRECEDING AND CURRENT ROW
          ) AS avg_metric_val
        FROM orca_metrics
        WHERE $__timeFilter(timestamp) 
        AND metric_name LIKE '%_CPU_PCT'
        AND ovid != 'INVALID_AGG'
        AND ovid = 'AGG0'
        """

        all_xf = [
            Utils.partition_by_cols_xf(["ovid", "metric_name"]),
            Utils.rename_by_regex_xf(
                'avg_metric_val {metric_name="t(.*)_CPU_PCT", ovid="(.*)"}', "$2-$1"
            ),
        ]

        panel = (
            gfb_timeseries.Panel()
            .title("CPU usage")
            .datasource(Utils.fsql_ref())
            .with_target(cls.get_sql_target(query_text, "cpuUsage"))
            .height(8)
            .span(8)
            .tooltip(Utils.default_tooltip())
            .transformations(all_xf)
            .min(0)
            .max(1)
            .unit("percentunit")  # percent [0, 1]
            .legend(Utils.default_legend())
        )

        return panel

    @classmethod
    def flow_panel(cls) -> gfb_timeseries.Panel:
        query_text = """
        SELECT 
          timestamp, 
          ovid, 
          metric_name, 
          AVG(metric_val) OVER (
            PARTITION BY ovid, metric_name
            ORDER BY timestamp
            RANGE BETWEEN INTERVAL '4s' PRECEDING AND CURRENT ROW
          ) AS avg_metric_val
        FROM orca_metrics
        WHERE $__timeFilter(timestamp) AND metric_name LIKE 'FLOW_%'
        """

        all_xf = [
            Utils.partition_by_cols_xf(["ovid", "metric_name"]),
            Utils.rename_by_regex_xf(
                'avg_metric_val {metric_name="(.*)", ovid="(.*)"}', "$2-$1"
            ),
        ]

        panel = (
            gfb_timeseries.Panel()
            .title("Flow Exec Stats")
            .datasource(Utils.fsql_ref())
            .with_target(cls.get_sql_target(query_text, "flow"))
            .height(8)
            .span(8)
            .min(0)
            .unit("rowsps")  # rows per second
            .tooltip(Utils.default_tooltip())
            .transformations(all_xf)
            .legend(Utils.default_legend())
            .overrides([Utils.override_to_right(".*PENDCNT", "jobs")])
        )
        
        return panel

    @classmethod
    def stat_panel(cls) -> gfb_stat.Panel:
        query_text = """
        SELECT metric_val FROM orca_metrics
        WHERE metric_name = 'FLOW_TS_PENDCNT'
        AND ovid = 'AGG0'
        """

        panel = (
            gfb_stat.Panel()
            .title("Flow: Pending Jobs")
            .datasource(Utils.fsql_ref())
            .with_target(cls.get_sql_target(query_text, "flow"))
            .height(8)
            .span(4)
            .min(0)
            .unit("jobs")
        )

        return panel

    @classmethod
    def flow_exec_datagrid_panel(cls) -> gfb_table.Panel:
        query_text = """
        SELECT * FROM orca_flowexec_stats
        ORDER BY ts DESC
        LIMIT 10
        """

        panel = (
            gfb_table.Panel()
            .title("Flow Exec Stats")
            .datasource(Utils.fsql_ref())
            .with_target(cls.get_sql_target(query_text, "flow"))
            .height(8)
            .span(8)
        )

        return panel

    @classmethod
    def agg_bufstats_panel(cls) -> gfb_timeseries.Panel:
        query_text = """
        SELECT 
          timestamp, 
          ovid, 
          metric_name, 
          AVG(metric_val) OVER (
            PARTITION BY ovid, metric_name
            ORDER BY timestamp
            RANGE BETWEEN INTERVAL '1s' PRECEDING AND CURRENT ROW
          ) AS avg_metric_val
        FROM orca_metrics
        WHERE $__timeFilter(timestamp) 
        AND metric_name LIKE 'AGGBUF_%'
        AND ovid != 'INVALID_AGG'
        AND ovid = 'AGG0'
        """

        all_xf = [
            Utils.partition_by_cols_xf(["ovid", "metric_name"]),
            Utils.rename_by_regex_xf(
                'avg_metric_val {metric_name="(.*)", ovid="(.*)"}', "$2-$1"
            ),
        ]

        panel = (
            gfb_timeseries.Panel()
            .title("Agg Bufstats")
            .datasource(Utils.fsql_ref())
            .with_target(cls.get_sql_target(query_text, "aggBufstats"))
            .height(8)
            .span(8)
            .min(0)
            .unit("bytes")
            .tooltip(Utils.default_tooltip())
            .legend(Utils.default_legend())
            .transformations(all_xf)
            .overrides([Utils.override_to_right(".*CNT", "count")])
        )

        return panel

    @classmethod
    def bulk_latency_panel(cls) -> gfb_timeseries.Panel:
        query_text = """
        SELECT 
          timestamp, 
          ovid, 
          metric_name, 
          AVG(metric_val) OVER (
            PARTITION BY ovid, metric_name
            ORDER BY timestamp
            RANGE BETWEEN INTERVAL '4s' PRECEDING AND CURRENT ROW
          ) AS avg_metric_val
        FROM orca_metrics
        WHERE $__timeFilter(timestamp) AND metric_name LIKE 'HGRPC_BLKLAT_NS_%'
        """

        all_xf = [
            Utils.partition_by_cols_xf(["ovid", "metric_name"]),
            Utils.rename_by_regex_xf(
                'avg_metric_val {metric_name="(.*)", ovid="(.*)"}', "$2-$1"
            ),
            Utils.rename_by_regex_xf(
                "(.*)-HGRPC_BLKLAT_NS_(.*)", "$1-$2"
            )
        ]

        panel = (
            gfb_timeseries.Panel()
            .title("Bulk Latency")
            .datasource(Utils.fsql_ref())
            .with_target(cls.get_sql_target(query_text, "bulkLatency"))
            .height(8)
            .span(8)
            .min(0)
            .unit("ns")
            .tooltip(Utils.default_tooltip())
            .legend(Utils.default_legend())
            .transformations(all_xf)
        )
        
        return panel

    @classmethod
    def bulk_qsz_panel(cls) -> gfb_timeseries.Panel:
        query_text = """
        SELECT 
          timestamp, 
          ovid, 
          metric_name, 
          AVG(metric_val) OVER (
            PARTITION BY ovid, metric_name
            ORDER BY timestamp
            RANGE BETWEEN INTERVAL '4s' PRECEDING AND CURRENT ROW
          ) AS avg_metric_val
        FROM orca_metrics
        WHERE $__timeFilter(timestamp) AND metric_name = 'HGRPC_BLKQ_SZ'
        """

        all_xf = [
            Utils.partition_by_cols_xf(["ovid", "metric_name"]),
            Utils.rename_by_regex_xf(
                'avg_metric_val {metric_name="(.*)", ovid="(.*)"}', "$2-$1"
            ),
        ]

        panel = (
            gfb_timeseries.Panel()
            .title("Bulk Queue Size")
            .datasource(Utils.fsql_ref())
            .with_target(cls.get_sql_target(query_text, "bulkQueueSize"))
            .height(8)
            .span(8)
            .min(0)
            .unit("reqps")
            .tooltip(Utils.default_tooltip())
            .legend(Utils.default_legend())
            .transformations(all_xf)
        )

        return panel    
    
    @classmethod
    def bulk_qcnt_panel(cls) -> gfb_timeseries.Panel:
        query_text = """
        SELECT 
          timestamp, 
          ovid, 
          metric_name, 
          AVG(metric_val) OVER (
            PARTITION BY ovid, metric_name
            ORDER BY timestamp
            RANGE BETWEEN INTERVAL '4s' PRECEDING AND CURRENT ROW
          ) AS avg_metric_val
        FROM orca_metrics
        WHERE $__timeFilter(timestamp) AND metric_name = 'HGRPC_BLKQ_INFLTCNT'
        """

        all_xf = [
            Utils.partition_by_cols_xf(["ovid", "metric_name"]),
            Utils.rename_by_regex_xf(
                'avg_metric_val {metric_name="(.*)", ovid="(.*)"}', "$2-$1"
            ),
        ]

        panel = (
            gfb_timeseries.Panel()
            .title("Bulk Inflight Count")
            .datasource(Utils.fsql_ref())
            .with_target(cls.get_sql_target(query_text, "bulkQueueCount"))
            .height(8)
            .span(8)
            .min(0)
            .unit("reqs")
            .tooltip(Utils.default_tooltip())
            .legend(Utils.default_legend())
            .transformations(all_xf)
        )

        return panel

    @classmethod
    def twopc_exec_datagrid_panel(cls) -> gfb_table.Panel:
        query_text = """
        SELECT * FROM orca_twopc_events
        ORDER BY (txnseq, ovid) DESC
        """
        
        panel = (
            gfb_table.Panel()
            .title("TwoPC Events")
            .datasource(Utils.fsql_ref())
            .with_target(cls.get_sql_target(query_text, "twopcEvents"))
            .height(8)
            .span(8)
        )

        return panel

    @classmethod
    def twopc_misc_panel(cls) -> gfb_timeseries.Panel:
        query_text = """
        SELECT ovid, key, value
FROM (
  SELECT
    ovid,
    key,
    value,
    timestamp_ns,
    ROW_NUMBER() OVER (
      PARTITION BY ovid, key
      ORDER BY timestamp_ns DESC
    ) AS rn
  FROM main.orca_misc_events
) t
WHERE rn = 1
ORDER BY ovid, key;
        """

        panel = (
            gfb_table.Panel()
            .title("TwoPC Misc")
            .datasource(Utils.fsql_ref())
            .with_target(cls.get_sql_target(query_text, "twopcMisc"))
            .height(8)
            .span(8)
        )

        return panel