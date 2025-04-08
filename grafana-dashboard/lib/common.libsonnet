// lib/common.libsonnet
{
  // Datasource UID used across panels
  datasourceUid: 'datasource-flightsql',
  datasourceType: 'influxdata-flightsql-datasource',

  // Default field configuration for timeseries panels (can be customized further)
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
        fillOpacity: 10, // Slightly increased default fill for visibility
        gradientMode: 'opacity', // Changed default gradient mode
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
          { color: 'green', value: null }, // Grafana uses null for base
          { color: 'red', value: 80 },
        ],
      },
      unit: '', // Default unit - can be overridden
    },
    overrides: [],
  },

  // Basic gridPos structure (we'll override h, w, x, y per panel)
  basicGridPos(h, w, x, y):: { h: h, w: w, x: x, y: y },

  // Common transformation to filter by the 'ovid' variable
  filterByOvidTransformation(ovidVarName):: {
    id: 'filterByValue',
    options: {
      filters: [
        {
          config: { id: 'equal', options: { value: '$' + '{%s}' % ovidVarName } },
          fieldName: 'ovid',
        },
      ],
      match: 'any', // Changed from 'all' in some original panels for flexibility
      type: 'include',
    },
  },

  // Common transformations for time series after filtering
  standardTimeseriesTransformations:: [
    {
      id: 'organize',
      options: {
        excludeByName: { ovid: true }, // Commonly exclude ovid after filtering
        includeByName: {},
        indexByName: {},
        renameByName: {},
      },
    },
    {
      id: 'prepareTimeSeries',
      options: { format: 'multi' }, // Standard format
    },
  ],
}