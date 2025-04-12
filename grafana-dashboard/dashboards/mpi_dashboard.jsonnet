local common = import 'common.libsonnet';
local dashboard = import 'dashboard.libsonnet';
local debug = import 'debug.libsonnet';
local panels = import 'panels.libsonnet';

local dashboardTitle = 'MPI Monitoring Dashboard';
local dashboardUid = 'mpi-dashboard';

local mpi_utils = import 'mpi_utils.libsonnet';

local annotations = mpi_utils.basic_annotations;

// local annotations = {
//   list: [
//     {
//       builtIn: 1,
//       datasource: {
//         type: 'grafana',
//         uid: '-- Grafana --',
//       },
//       enable: true,
//       hide: true,
//       iconColor: 'rgba(0, 211, 255, 1)',
//       name: 'Annotations & Alerts',
//       type: 'dashboard',
//     },
//   ],
// };

local panel_timestep_override = {
  matcher: {
    id: 'byRegexp',
    options: '/timestep/',
  },
  properties: [
    {
      id: 'custom.hideFrom',
      value: {
        tooltip: false,
        viz: false,
        legend: true,
      },
    },
    {
      id: 'custom.lineWidth',
      value: 0,  // Make line invisible
    },
    {
      id: 'custom.axisPlacement',
      value: 'hidden',
    },
    {
      id: 'displayName',
      value: 'MPI Timestep',  // Makes tooltip clearer
    },

    // {
    //   id: 'unit',
    //   value: 'hex0x',
    // },
    // {
    //     id: "custom.axisPlacement",
    //     value: "hidden"

    // }
  ],
};

local panel_rename_overrides = [
  {
    matcher: {
      id: 'byName',
      options: 'max_probe_val',
    },
    properties: [
      {
        id: 'displayName',
        value: 'Max Probe Val',
      },
    ],
  },
];

local panel_probe_override = {
  matcher: {
    id: 'byRegexp',
    options: '/.*probe_val$/',
  },
  properties: [
    // {
    //   id: 'custom.hideFrom',
    //   value: {
    //     tooltip: false,
    //     viz: true,
    //     legend: true,
    //   },
    // },
    {
      id: 'unit',
      value: 'ns',
    },
  ],
};


local field_config = mpi_utils.basicFieldConfig + {
    defaults+: {
        custom+: {
            axisLabel: 'Collective Time',
            axisSoftMin: 1e6,
            axisSoftMax: 10e6,
        },
    },
    overrides: [
        panel_timestep_override,
        // panel_probe_override,
        mpi_utils.unitOverrideByRegex('/.*_probe_val/', 'ns'),
        mpi_utils.renameOverride('max_probe_val', 'Max Probe Val'),
        mpi_utils.renameOverride('min_probe_val', 'Min Probe Val'),
    ]
};

local time_picker = {
  refresh_intervals: ['5s', '10s', '30s', '1m'],
  collapse: false,
  enable: true,
  status: 'info',
};

local panel_opts = {
  legend: {
    calcs: [],
    displayMode: 'list',
    placement: 'bottom',
    showLegend: true,
  },
  tooltip: {
    hideZeros: false,
    mode: 'multi',  // 'single' or 'multi'
    sort: 'none',
  },
};

local fsql_datasource = {
  type: common.datasourceType,
  uid: common.datasourceUid,
};

local mpi_panel = {
  type: 'timeseries',
  title: 'MPI Collective: $collective',
  datasource: fsql_datasource,
  // h w x y
  gridPos: common.basicGridPos(6, 24, 0, 0),
  description: 'MPI Collective Operations',
  fieldConfig: field_config,
  unit: 'ns',
  options: panel_opts,
  repeat: 'collective',
  repeatDirection: 'v',
  targets: [
    {
      refId: 'A',
      datasource: fsql_datasource,
      format: 'table',
      rawQuery: true,
      queryText: |||
        SELECT 
            probe_name,
            MIN(timestamp) as timestamp,
            MAX(probe_val) as max_probe_val,
            MIN(probe_val) as min_probe_val,
            timestep
        FROM mpi_collectives
        WHERE $__timeFilter(timestamp)
        AND (
          probe_name == '${collective}'
        )
        GROUP BY (timestep, probe_name)
      |||,
      rawEditor: true,
    },
  ],
  transformations: [
    // {
    //   id: 'partitionByValues',
    //   options: {
    //     fields: ['probe_name'],
    //   },
    //   keepFields: true,
    //   naming: { asLabels: true },
    // },
    // {
    //   id: 'renameByRegex',
    //   options: {
    //     regex: 'max_probe_val (.*)',
    //     renamePattern: '$1 (max)',
    //   },
    // },
    // {
    //   id: 'renameByRegex',
    //   options: {
    //     regex: 'min_probe_val (.*)',
    //     renamePattern: '$1 (min)',
    //   },
    // },
  ],
};

local template_obj = {
  current: {
    text: [
      'MPI_Init',
    ],
    value: [
      'MPI_Init',
    ],
  },
  datasource: {
    type: 'influxdata-flightsql-datasource',
    uid: 'datasource-flightsql',
  },
  definition: 'SELECT * FROM probe_map;',
  description: '',
  label: 'Collective',
  multi: true,
  name: 'collective',
  options: [],
  query: 'SELECT * FROM probe_map;',
  refresh: 1,
  regex: '',
  type: 'query',
};

// BEGIN DASHBOARD

{
  apiVersion: 'grizzly.grafana.com/v1alpha1',
  kind: 'Dashboard',
  metadata: {
    name: 'mpi-dashboard',
    uid: 'mpi-dashboard',
  },
  spec: {
    tags: ['orca', 'grizzly-managed'],
    timezone: 'browser',
    title: 'MPI Monitoring Dashboard 2',
    uid: 'mpi-dashboard',
    schemaVersion: 40,
    time: { from: 'now-5m', to: 'now' },
    timepicker: time_picker,
    panels: [
      {
        collapsed: false,
        type: 'row',
        title: 'Row 1',
        gridPos: common.basicGridPos(1, 24, 0, 0),
      },
      // debug.testPanel(common.basicGridPos(8, 8, 0, 0)),
      // panels.logsPanel('Logs', common.basicGridPos(8, 8, 0, 0)),
      mpi_panel,
    ],
    annotations: annotations,
    editable: true,
    fiscalYearStartMonth: 1,
    graphTooltip: 1,
    templating: {
      list: [template_obj],
    },
  },
}
