// lib/metrics_utils.libsonnet
// Minimal, reusable utilities for metrics dashboards
{
  // Datasource constants (override as needed)
  datasourceUid: 'datasource-flightsql',
  datasourceType: 'influxdata-flightsql-datasource',

  // Default field configuration for timeseries panels
  defaultTimeseriesFieldConfig:: {
    defaults: {
      color: { mode: 'palette-classic' },
      custom: {
        axisBorderShow: false,
        axisCenteredZero: false,
        axisColorMode: 'text',
        axisLabel: '',
        axisPlacement: 'auto',
        barAlignment: 0,
        barWidthFactor: 0.6,
        drawStyle: 'line',
        fillOpacity: 0,
        gradientMode: 'none',
        hideFrom: { legend: false, tooltip: false, viz: false },
        insertNulls: false,
        lineInterpolation: 'linear',
        lineWidth: 1,
        pointSize: 5,
        scaleDistribution: { type: 'linear' },
        showPoints: 'auto',
        spanNulls: false,
        stacking: { group: 'A', mode: 'none' },
        thresholdsStyle: { mode: 'off' },
      },
      mappings: [],
      thresholds: {
        mode: 'absolute',
        steps: [
          { color: 'green' },
          { color: 'red', value: 80 },
        ],
      },
      unit: '',  // Default unit - can be overridden
    },
    overrides: [],
  },

  // Helper for panel grid positioning
  basicGridPos(h, w, x, y):: { h: h, w: w, x: x, y: y },

  // filterByValueXf: filter input by (key == value)
  filterByValueXf(key, value):: {
    id: 'filterByValue',
    options: {
      filters: [{
        config: { id: 'equal', options: { value: value } },
        fieldName: key,
      }],
      match: 'all',
      type: 'include',
    },
  },

  // fieldConfigOverrideAssignUnit: override the unit for a field
  fieldConfigOverrideAssignUnit(field, unit):: {
    matcher: { id: 'byName', options: field },
    properties: [{ id: 'unit', value: unit }],
  },
}
