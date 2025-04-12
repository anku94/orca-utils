{
  // Basic annotations: boilerplate
  basic_annotations: {
    list: [
      {
        builtIn: 1,
        datasource: {
          type: 'grafana',
          uid: '-- Grafana --',
        },
        enable: true,
        hide: true,
        iconColor: 'rgba(0, 211, 255, 1)',
        name: 'Annotations & Alerts',
        type: 'dashboard',
      },
    ],
  },

  // Rename override: change the display name of a metric
  renameOverride(name, newName):: {
    matcher: { id: 'byName', options: name },
    properties: [{ id: 'displayName', value: newName }],
  },

  // Unit override: change the unit of a metric
  unitOverrideByRegex(regex, unit):: {
    matcher: { id: 'byRegexp', options: regex },
    properties: [{ id: 'unit', value: unit }],
  },

  // basicFieldConfig
  basicFieldConfig:: {
    defaults: {
      color: {
        mode: 'palette-classic',
      },
      custom: {
        axisBorderShow: false,
        axisLabel: 'Time', // Can override
        axisSoftMin: 1e6,  // Can override
        axisSoftMax: 10e6,  // Can override
        axisPlacement: 'auto',
        barAlignment: 0,
        barWidthFactor: 0.6,
        drawStyle: 'line',
        fillOpacity: 0,
        gradientMode: 'none',
        hideFrom: {
          legend: false,
          tooltip: false,
          viz: false,
        },
        insertNulls: false,
        lineInterpolation: 'linear',
        lineWidth: 1,
        pointSize: 5,
        scaleDistribution: {
          type: 'linear',
        },
        showPoints: 'auto',
        spanNulls: false,
        stacking: {
          group: 'A',
          mode: 'none',
        },
        thresholdsStyle: {
          mode: 'off',
        },
      },
      mappings: [],
      thresholds: {
        mode: 'absolute',
        steps: [
          {
            color: 'green',
            value: null,
          },
          {
            color: 'red',
            value: 80,
          },
        ],
      },
      // unit: 'ns',
    },
    overrides: [],
  },
}
