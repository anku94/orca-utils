  // Basic annotations: boilerplate
local basic_annotations = {
  list: [
  {
    builtIn: 1,
    datasource: { type: 'grafana', uid: '-- Grafana --' },
    enable: true,
    hide: true,
    iconColor: 'rgba(0, 211, 255, 1)',
      name: 'Annotations & Alerts',
      type: 'dashboard',
    },
  ],
};

// Basic time picker: boilerplate
local basic_time_picker = {
  refresh_intervals: ['5s', '10s', '30s', '1m'],
  collapse: false,
  enable: true,
  status: 'info',
};

local basic_legend = {
  calcs: [],
  displayMode: 'list',
  placement: 'bottom',
  showLegend: true,
};


{
  // Basic annotations: boilerplate
  basic_annotations: basic_annotations,
  // Basic time picker: boilerplate
  basic_time_picker: basic_time_picker,
  // Basic legend: boilerplate
  basic_legend: basic_legend,

  // BasicGridPos: shorthand for gridPos
  basicGridPos(h, w, x, y):: { h: h, w: w, x: x, y: y },

  // Rename override: change the display name of a metric
  renameOverride(name, newName):: {
    matcher: { id: 'byName', options: name },
    properties: [{ id: 'displayName', value: newName }],
  },

  // OverrideUnitByRegex: change the unit of a metric
  overrideUnitByRegex(regex, unit):: {
    matcher: { id: 'byRegexp', options: regex },
    properties: [{ id: 'unit', value: unit }],
  },

  // makeFieldTooltipOnly: make a field only show in tooltip
  // (mostly for MPI timestep)
  // Ideally we should be able to just set viz: false
  // But sometimes it is flaky (not respected) and visually disabling
  // may be better
  makeFieldTooltipOnly(fieldRegex):: {
    matcher: { id: 'byRegexp', options: fieldRegex },
    properties: [
      { id: 'custom.hideFrom', value: { tooltip: false, viz: false, legend: true } },
      { id: 'custom.lineWidth', value: 0 },
      { id: 'custom.axisPlacement', value: 'hidden' },
    ],
  },

  // addTemplateVar: add a template variable to the dashboard
  // override current and datasource
  addTemplateVar(name, label, query):: {
    current: { text: [], value: [] },
    datasource: {},
    definition: query,
    description: '',
    label: label,
    multi: true,
    name: name,
    options: [],
    query: query,
    refresh: 1,
    regex: '',
    type: 'query',
  },

  // basicFieldConfig: default field config for timeseries panels
  basicFieldConfig:: {
    defaults: {
      color: { mode: 'palette-classic' },
      custom: {
        axisBorderShow: false,
        axisLabel: 'Time',  // Can override
        axisSoftMin: 1e6,  // Can override
        axisSoftMax: 10e6,  // Can override
        axisPlacement: 'auto',
        barAlignment: 0,
        barWidthFactor: 0.6,
        drawStyle: 'line',
        fillOpacity: 0,
        gradientMode: 'none',
        hideFrom: { legend: false, tooltip: false, viz: false },
        insertNulls: false,
        lineInterpolation: 'linear', lineWidth: 1,
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
          { color: 'green', value: null },
          { color: 'red', value: 80 },
        ],
      },
      // unit: 'ns', -- disable in favor of overrideUnitByRegex
    },
    overrides: [],
  },

  // basicDashboard: default dashboard config
  basicDashboard(name, uid):: {
    apiVersion: 'grizzly.grafana.com/v1alpha1',
    kind: 'Dashboard',
    metadata: {
      name: name,
      uid: uid,
    },
    spec: {
      tags: [],
      timezone: 'browser',
      title: 'TOBEREPLACED',
      uid: uid,
      schemaVersion: 40,
      time: { from: 'now-5m', to: 'now' },
      timepicker: basic_time_picker,
      panels: [],
      annotations: basic_annotations,
      templating: {
        list: [],
      },
    },
  },
}
