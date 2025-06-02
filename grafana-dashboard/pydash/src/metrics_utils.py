"""
Metrics utilities for Grafana dashboards - Python equivalent of metrics_utils.libsonnet
"""

from typing import Dict, Any, List, Optional
from grafana_foundation_sdk.models.dashboard import DataSourceRef, DataTransformerConfig, GridPos
from grafana_foundation_sdk.builders import timeseries
from grafana_foundation_sdk.builders.common import GraphFieldConfig, StackingConfig, HideSeriesConfig, GraphThresholdsStyleConfig
from grafana_foundation_sdk.models.common import (
    GraphDrawStyle,
    GraphGradientMode,
    GraphThresholdsStyleMode,
    VisibilityMode,
    AxisPlacement,
    AxisColorMode,
    BarAlignment,
    LineInterpolation,
    StackingMode
)


class MetricsUtils:
    """Utility class for common metrics dashboard configurations."""

    # Datasource constants
    DATASOURCE_UID = 'datasource-flightsql'
    DATASOURCE_TYPE = 'influxdata-flightsql-datasource'

    @classmethod
    def flightsql_datasource_ref(cls) -> DataSourceRef:
        """Returns a reference to the FlightSQL datasource."""
        return DataSourceRef(type_val=cls.DATASOURCE_TYPE,
                             uid=cls.DATASOURCE_UID)

    @classmethod
    def basic_grid_pos(cls, h: int, w: int, x: int, y: int) -> GridPos:
        """Helper for panel grid positioning using proper SDK model."""
        return GridPos(h=h, w=w, x=x, y=y)

    @classmethod
    def default_timeseries_field_config(cls) -> GraphFieldConfig:
        """Default field configuration for timeseries panels using proper SDK builder."""
        
        # Create threshold style config
        thresholds_style = (
            GraphThresholdsStyleConfig()
            .mode(GraphThresholdsStyleMode.OFF)
        )
        
        # Create stacking config
        stacking = (
            StackingConfig()
            .mode(StackingMode.NONE)
            .group('A')
        )
        
        # Create hide series config
        hide_from = (
            HideSeriesConfig()
            .tooltip(False)
            .legend(False)
            .viz(False)
        )
        
        # Build the complete field config using the builder
        return (
            GraphFieldConfig()
            .draw_style(GraphDrawStyle.LINE)
            .gradient_mode(GraphGradientMode.NONE)
            .thresholds_style(thresholds_style)
            .line_width(1)
            .line_interpolation(LineInterpolation.LINEAR)
            .fill_opacity(0)
            .show_points(VisibilityMode.AUTO)
            .point_size(5)
            .axis_placement(AxisPlacement.AUTO)
            .axis_color_mode(AxisColorMode.TEXT)
            .axis_label('')
            .axis_soft_min(0)
            .axis_soft_max(0)
            .axis_border_show(False)
            .axis_centered_zero(False)
            .axis_grid_show(False)
            .bar_alignment(BarAlignment.CENTER)
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
            'refId': ref_id,
            'datasource': cls.flightsql_datasource_ref(),
            'format': 'table',
            'queryText': query_text,
            'rawQuery': True,
            'rawEditor': True,
        }

    @classmethod
    def partition_by_col_transformation(cls, col_name: str) -> DataTransformerConfig:
        """Partition by a column into multiple dataframes using proper SDK model."""
        return DataTransformerConfig(
            id_val='partitionByValues',
            options={
                'fields': [col_name],
                'keepFields': False
            }
        )

    @classmethod
    def rename_by_regex_transformation(cls, regex: str, rename_pattern: str) -> DataTransformerConfig:
        """Rename a column by regex using proper SDK model."""
        return DataTransformerConfig(
            id_val='renameByRegex',
            options={
                'regex': regex,
                'renamePattern': rename_pattern
            }
        )

    @classmethod
    def filter_by_value_transformation(cls, key: str, value: str) -> DataTransformerConfig:
        """Filter input by (key == value) using proper SDK model."""
        return DataTransformerConfig(
            id_val='filterByValue',
            options={
                'filters': [{
                    'config': {
                        'id': 'equal',
                        'options': {
                            'value': value
                        }
                    },
                    'fieldName': key,
                }],
                'match': 'all',
                'type': 'include',
            }
        )

    @classmethod
    def organize_transformation(cls, exclude_by_name: Optional[Dict[str, bool]] = None,
                              include_by_name: Optional[Dict[str, bool]] = None,
                              rename_by_name: Optional[Dict[str, str]] = None) -> DataTransformerConfig:
        """Organize transformation using proper SDK model."""
        return DataTransformerConfig(
            id_val='organize',
            options={
                'excludeByName': exclude_by_name or {},
                'includeByName': include_by_name or {},
                'indexByName': {},
                'renameByName': rename_by_name or {},
            }
        )

    @classmethod
    def prepare_timeseries_transformation(cls, format_type: str = 'multi') -> DataTransformerConfig:
        """Prepare timeseries transformation using proper SDK model."""
        return DataTransformerConfig(
            id_val='prepareTimeSeries',
            options={'format': format_type}
        )

    @classmethod
    def basic_timeseries_panel(cls, title: str, grid_pos: GridPos) -> timeseries.Panel:
        """Create a basic timeseries panel with standard configuration using proper SDK models."""
        panel = (
            timeseries.Panel()
            .title(title)
            .datasource(cls.flightsql_datasource_ref())
            .grid_pos(grid_pos)
        )

        # Configure field config using the proper SDK builder
        panel.fieldConfig = cls.default_timeseries_field_config().build()

        # Configure options using proper structure
        panel.options = {
            'legend': {
                'calcs': [],
                'displayMode': 'list',
                'placement': 'bottom',
                'showLegend': True,
            },
            'tooltip': {
                'mode': 'single',
                'sort': 'none',
            },
        }

        return panel

    @classmethod
    def standard_timeseries_transformations(cls) -> List[DataTransformerConfig]:
        """Standard transformations for timeseries panels."""
        return [
            cls.organize_transformation(exclude_by_name={'ovid': True}),
            cls.prepare_timeseries_transformation()
        ]
