from grafana_foundation_sdk.builders import (
    logs,
    loki,
    prometheus,
    stat,
    text,
    timeseries,
)
from grafana_foundation_sdk.models.dashboard import DataSourceRef
from grafana_foundation_sdk.models.prometheus import PromQueryFormat

# This file contains a series of utility functions to simplify the creation
# of panels while providing a consistent "look and feel".


def stat_panel() -> stat.Panel:
    """
    Creates a pre-configured stat panel.
    """

    # no specific options required for this lab.
    return stat.Panel()


def text_panel(content: str) -> text.Panel:
    """
    Creates a pre-configured text panel.
    """
    return (
        text.Panel()
        # TODO: configure default options for text panels
        #
        #  * `content` set to content
        #  * `mode` set to `markdown`
        #
        # See: https://grafana.github.io/grafana-foundation-sdk/v11.6.x+cog-v0.0.x/python/Reference/text/builder-Panel/
    )


def timeseries_panel() -> timeseries.Panel:
    """
    Creates a pre-configured timeseries panel.
    """
    return (
        timeseries.Panel()
        # TODO: configure default options for timeseries panels
        #
        #  * `fillOpacity` set to `20`
        #  * `gradientMode` set to  `opacity`
        #  * `legend` options:
        #    * `displayMode` set to `list`
        #    * `placement` set to `bottom`
        #    * `showLegend` set to `true`
        #
        # See: https://grafana.github.io/grafana-foundation-sdk/v11.6.x+cog-v0.0.x/python/Reference/timeseries/builder-Panel/
    )


def log_panel() -> logs.Panel:
    """
    Creates a pre-configured logs panel.
    """
    return (
        logs.Panel()
        # TODO: configure default options for logs panels
        #
        #  * `showTime` set to `true`
        #  * `sortOrder` set to `Descending`
        #  * `enableLogDetails` set to `true`
        #
        # See: https://grafana.github.io/grafana-foundation-sdk/v11.6.x+cog-v0.0.x/python/Reference/logs/builder-Panel/
    )


def loki_datasource_ref() -> DataSourceRef:
    """
    Returns a reference to the Loki datasource used by the
    workshop stack.
    """
    return DataSourceRef(type_val="loki", uid="loki")


def prometheus_datasource_ref() -> DataSourceRef:
    """
    Returns a reference to the Prometheus datasource used by the
    workshop stack.
    """
    return DataSourceRef(type_val="prometheus", uid="prometheus")


def loki_query(expression: str) -> loki.Dataquery:
    """
    Creates a Loki query pre-configured for range vectors.
    """
    return loki.Dataquery().expr(expression).query_type("range").legend_format("__auto")


def prometheus_query(expression: str) -> prometheus.Dataquery:
    """
    Creates a Prometheus query pre-configured for range vectors.
    """
    return (
        prometheus.Dataquery()
        .expr(expression)
        .range()
        .format(PromQueryFormat.TIME_SERIES)
        .legend_format("__auto")
    )


def instant_prometheus_query(expression: str) -> prometheus.Dataquery:
    """
    Creates a Prometheus query pre-configured for instant
    vectors and table data formatting.
    """
    return (
        prometheus.Dataquery()
        .expr(expression)
        .instant()
        .format(PromQueryFormat.TABLE)
        .legend_format("__auto")
    )
