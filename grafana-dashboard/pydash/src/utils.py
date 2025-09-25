"""
Metrics utilities for Grafana dashboards - Python equivalent of metrics_utils.libsonnet
"""

from typing import Dict, Any, List, Optional
from grafana_foundation_sdk.models.dashboard import (
    DataSourceRef,
    DataTransformerConfig,
    GridPos,
)
from grafana_foundation_sdk.builders import timeseries
from grafana_foundation_sdk.builders import common as bcommon
from grafana_foundation_sdk.builders.common import (
    GraphFieldConfig,
    StackingConfig,
    HideSeriesConfig,
    GraphThresholdsStyleConfig,
)

import grafana_foundation_sdk.models.common as gfmc

from grafana_foundation_sdk.models import dashboard as gfm_dash


class Utils:
    """Utility class for bcommon metrics dashboard configurations."""

    # Datasource constants
    DATASOURCE_UID = "datasource-flightsql"
    DATASOURCE_TYPE = "influxdata-flightsql-datasource"

    @classmethod
    def fsql_ref(cls) -> DataSourceRef:
        """Returns a reference to the FlightSQL datasource."""
        return DataSourceRef(type_val=cls.DATASOURCE_TYPE, uid=cls.DATASOURCE_UID)

    @classmethod
    def default_tooltip(cls) -> bcommon.VizTooltipOptions:
        """Default tooltip configuration for timeseries panels using proper SDK builder."""
        return (
            bcommon.VizTooltipOptions()
            .mode(gfmc.TooltipDisplayMode.MULTI)
            .sort(gfmc.SortOrder.ASCENDING)
        )

    @classmethod
    def default_legend(cls) -> bcommon.VizLegendOptions:
        """Default legend configuration for timeseries panels using proper SDK builder."""
        return (
            bcommon.VizLegendOptions()
            .display_mode(gfmc.LegendDisplayMode.LIST)
            .placement(gfmc.LegendPlacement.BOTTOM)
            .show_legend(True)
        )

    @classmethod
    def default_timeseries_field_config(cls) -> GraphFieldConfig:
        """Default field configuration for timeseries panels using proper SDK builder."""

        # Create threshold style config
        thresholds_style = GraphThresholdsStyleConfig().mode(
            gfmc.GraphThresholdsStyleMode.OFF
        )

        # Create stacking config
        stacking = StackingConfig().mode(gfmc.StackingMode.NONE).group("A")

        # Create hide series config
        hide_from = HideSeriesConfig().tooltip(False).legend(False).viz(False)

        # Build the complete field config using the builder
        return (
            GraphFieldConfig()
            .draw_style(gfmc.GraphDrawStyle.LINE)
            .gradient_mode(gfmc.GraphGradientMode.NONE)
            .thresholds_style(thresholds_style)
            .line_width(1)
            .line_interpolation(gfmc.LineInterpolation.LINEAR)
            .fill_opacity(0)
            .show_points(gfmc.VisibilityMode.AUTO)
            .point_size(5)
            .axis_placement(gfmc.AxisPlacement.AUTO)
            .axis_color_mode(gfmc.AxisColorMode.TEXT)
            .axis_label("")
            .axis_soft_min(0)
            .axis_soft_max(0)
            .axis_border_show(False)
            .axis_centered_zero(False)
            .axis_grid_show(False)
            .bar_alignment(gfmc.BarAlignment.CENTER)
            .bar_width_factor(0.6)
            .stacking(stacking)
            .hide_from(hide_from)
            .insert_nulls(False)
            .span_nulls(False)
        )

    @classmethod
    def sql_table_target(cls, ref_id: str, query_text: str) -> Dict[str, Any]:
        """Template for SQL table target - still using dict due to FlightSQL specifics."""
        return {
            "refId": ref_id,
            "datasource": cls.fsql_ref(),
            "format": "table",
            "queryText": query_text,
            "rawQuery": True,
            "rawEditor": True,
        }

    @classmethod
    def partition_by_cols_xf(cls, col_names: List[str]) -> DataTransformerConfig:
        """Partition by a column into multiple dataframes using proper SDK model."""
        return DataTransformerConfig(
            id_val="partitionByValues",
            options={"fields": col_names, "keepFields": False},
        )

    @classmethod
    def rename_by_regex_xf(
        cls, regex: str, rename_pattern: str
    ) -> DataTransformerConfig:
        """Rename a column by regex using proper SDK model."""
        return DataTransformerConfig(
            id_val="renameByRegex",
            options={"regex": regex, "renamePattern": rename_pattern},
        )

    @classmethod
    def filter_by_value_transformation(
        cls, key: str, value: str
    ) -> DataTransformerConfig:
        """Filter input by (key == value) using proper SDK model."""
        return DataTransformerConfig(
            id_val="filterByValue",
            options={
                "filters": [
                    {
                        "config": {"id": "equal", "options": {"value": value}},
                        "fieldName": key,
                    }
                ],
                "match": "all",
                "type": "include",
            },
        )

    @classmethod
    def organize_xf(
        cls,
        exclude_by_name: Optional[Dict[str, bool]] = None,
        include_by_name: Optional[Dict[str, bool]] = None,
        rename_by_name: Optional[Dict[str, str]] = None,
    ) -> DataTransformerConfig:
        """Organize transformation using proper SDK model."""
        return DataTransformerConfig(
            id_val="organize",
            options={
                "excludeByName": exclude_by_name or {},
                "includeByName": include_by_name or {},
                "indexByName": {},
                "renameByName": rename_by_name or {},
            },
        )

    @classmethod
    def prepare_timeseries_xf(cls, format_type: str = "multi") -> DataTransformerConfig:
        """Prepare timeseries transformation using proper SDK model."""
        return DataTransformerConfig(
            id_val="prepareTimeSeries", options={"format": format_type}
        )

    @classmethod
    def basic_timeseries_panel(cls, title: str, grid_pos: GridPos) -> timeseries.Panel:
        """Create a basic timeseries panel with standard configuration using proper SDK models."""
        panel = (
            timeseries.Panel()
            .title(title)
            .datasource(cls.fsql_ref())
            .grid_pos(grid_pos)
        )

        # Configure field config using the proper SDK builder
        panel.fieldConfig = cls.default_timeseries_field_config().build()

        # Configure options using proper structure
        panel.options = {
            "legend": {
                "calcs": [],
                "displayMode": "list",
                "placement": "bottom",
                "showLegend": True,
            },
            "tooltip": {
                "mode": "single",
                "sort": "none",
            },
        }

        return panel

    @classmethod
    def standard_timeseries_xf(cls) -> List[DataTransformerConfig]:
        """Standard transformations for timeseries panels."""
        return [
            cls.organize_xf(exclude_by_name={"ovid": True}),
            cls.prepare_timeseries_xf(),
        ]

    @classmethod
    def override_to_right(cls, regexp: str, unit: str):
        from grafana_foundation_sdk.builders import dashboard as gfb_dashboard
        
        regexp_matcher = gfm_dash.MatcherConfig(
            id_val="byRegexp",
            options=regexp,
        )

        properties = [
            gfm_dash.DynamicConfigValue(
                id_val="custom.axisPlacement",
                value=gfmc.AxisPlacement.RIGHT,
            ),
            gfm_dash.DynamicConfigValue(
                id_val="unit",
                value=unit,
            )]

        return (
            gfb_dashboard.DashboardFieldConfigSourceOverrides()
            .matcher(regexp_matcher)
            .properties(properties)
        )
