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
        fillOpacity: 0, // Slightly increased default fill for visibility
        gradientMode: 'none', // Changed default gradient mode
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
          { color: 'green'},
          { color: 'red', value: 80 },
        ],
      },
      unit: '', // Default unit - can be overridden
    },
    overrides: [],
  },

  // Basic gridPos structure (we'll override h, w, x, y per panel)
  basicGridPos(h, w, x, y):: { h: h, w: w, x: x, y: y },

  // filterByOvidVarXform: filterByOLink panel to dashboard variable 'ovidVarName'
  filterByOvidVarXform(ovidVarName):: {
    id: 'filterByValue',
    options: {
      filters: [
        {
          config: { id: 'equal', options: { value: '$' + '{%s}' % ovidVarName } },
          fieldName: 'ovid',
        },
      ],
      match: 'all',
      type: 'include',
    },
  },

  // Common transformations for time series after filtering
  // First we exclude ovid as it's not a valid time series field and
  // we have already filtered by it.
  // Then apply the multi-frame timeseries format in case there are
  // more than one metric.
  stdTimeseriesXforms:: [
    {
      id: 'organize',
      options: {
        excludeByName: { ovid: true },
        includeByName: {},
        indexByName: {},
        renameByName: {},
      },
    },
    {
      id: 'prepareTimeSeries',
      options: { format: 'multi' },
    },
  ],
}