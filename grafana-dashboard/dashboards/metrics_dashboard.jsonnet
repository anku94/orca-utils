// metrics_dashboard.jsonnet
local metrics_utils = import 'metrics_utils.libsonnet';

// Dashboard metadata
local dashboardTitle = 'Metrics Monitoring Dashboard';
local dashboardUid = 'metrics-dashboard';

// Datasource
local fsql_datasource = {
  type: 'influxdata-flightsql-datasource',
  uid: 'datasource-flightsql',
};

// stdTimeseriesXf: standard transformations for timeseries panels
local stdTimeseriesXf = [
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
];

// partitionByColXf: partition by a column into multiple df's
local partitionByColXf(colname) = {
  id: 'partitionByValues',
  options: { fields: [colname] },
  keepFields: false,
};

// renameByRegexXf: rename a column by regex
local renameByRegexXf(regex, renamePattern) = {
  id: 'renameByRegex',
  options: { regex: regex, renamePattern: renamePattern },
};

// sqlTableTgt: template/schema for SQL table target
local sqlTableTgt = {
  refId: 'A',
  datasource: fsql_datasource,
  format: 'table',
  queryText: '',
  rawQuery: true,
  rawEditor: true,  // switch from query editor to raw editor
};

// --- Begin panel definitions ---

// Log panel: opts
local logPanelOpts = {
  enableLogDetails: true,
  sortOrder: 'Descending',
  wrapLogMessage: false,
  prettifyLogMessage: false,
  showTime: false,
  showLabels: false,
  showCommonLabels: false,
  dedupStrategy: 'none',
  enableInfiniteScrolling: false,
};

// Log panel: targets
local logsPanelTargets = [
  sqlTableTgt {
    refId: 'logs',
    queryText: |||
      SELECT timestamp,message,level,ovid 
      FROM orca_logs 
      WHERE $__timeFilter(timestamp)
    |||,
  },
];

// Log panel: Actual panel spec
local logsPanel = {
  type: 'logs',
  title: 'ORCA Logs',
  datasource: fsql_datasource,
  fieldConfig: { defaults: {}, overrides: [] },
  gridPos: metrics_utils.basicGridPos(16, 12, 0, 0),
  options: logPanelOpts,
  pluginVersion: '11.6.0',
  targets: logsPanelTargets,
  transformations: [metrics_utils.filterByValueXf('ovid', '$ovid')],
};

// New basicTimeseriesPanel template as an object that can be overridden
local basicTimeseriesPanel = {
  type: 'timeseries',
  datasource: fsql_datasource,
  fieldConfig: metrics_utils.defaultTimeseriesFieldConfig,
  options: {
    legend: { calcs: [], displayMode: 'list', placement: 'bottom', showLegend: true },
    tooltip: { mode: 'single', sort: 'none' },
  },
  targets: [sqlTableTgt],
  transformations: [],
};

// jobStatsPanel: Shows ORCA job statistics.
local jobStatsPanel = basicTimeseriesPanel {
  title: 'ORCA Job Stats',
  gridPos: metrics_utils.basicGridPos(8, 12, 12, 0),
  targets: [
    sqlTableTgt {
      refId: 'jobStats',
      queryText: |||
        SELECT ovid, job_id, sql, name, enter_time, end_time, status, error
        FROM orca_job_stats
      |||,
    },
  ],
};

// rpcBytesPanel: Displays RPC bytes/s.
local rpcBytesPanel = basicTimeseriesPanel {
  title: 'RPC bytes/s',
  gridPos: metrics_utils.basicGridPos(8, 12, 0, 8),
  targets: [
    sqlTableTgt {
      refId: 'rpcbytes',
      queryText: |||
        SELECT timestamp, ovid, metric_name, metric_val
        FROM orca_metrics
        WHERE $__timeFilter(timestamp) AND metric_name = 'HGRPC_RATE_BYTES'
      |||,
    },
  ],
  fieldConfig+: { defaults+: { unit: 'Bps' } },
  transformations: [partitionByColXf('ovid'), renameByRegexXf('metric_val (.*)', '$1')],
};

// rpcCountsPanel: Displays RPC counts/s.
local rpcCountsPanel = basicTimeseriesPanel {
  title: 'RPC counts/s',
  gridPos: metrics_utils.basicGridPos(8, 12, 0, 16),
  targets: [
    sqlTableTgt {
      refId: 'rpcCounts',
      queryText: |||
        SELECT timestamp, ovid, metric_name, metric_val 
        FROM orca_metrics
        WHERE $__timeFilter(timestamp) AND metric_name = 'HGRPC_RATE_COUNT'
      |||,
    },
  ],
  fieldConfig+: { defaults+: { unit: 'mps' } },
  transformations: [partitionByColXf('ovid'), renameByRegexXf('metric_val (.*)', '$1')],
};

// cpuUsagePanelTemplate: template for CPU usage panel
local cpuUsagePanelTemplate(ovid, gridPos) = basicTimeseriesPanel {
  title: 'CPU Usage (Ovid: ' + ovid + ')',
  gridPos: gridPos,
  options+: { tooltip+: { mode: 'multi', hideZeros: false } },
  targets: [sqlTableTgt {
    refId: 'cpuUsage' + ovid,
    queryText: |||
      SELECT timestamp, ovid, metric_name, metric_val
      FROM orca_metrics
      WHERE $__timeFilter(timestamp)
      AND metric_name LIKE 'CPU%%_USAGE_PCT'
      AND ovid = ovid
    |||,
  }],
  fieldConfig+: { defaults+: { unit: 'percent' } },
  transformations: [
    partitionByColXf('metric_name'),
    renameByRegexXf('metric_val CPU(.*)_USAGE_PCT', 'Core $1'),
  ],
};

// memUsagePanelTemplate: template for memory usage panel
local memUsagePanelTemplate(ovid, gridPos) = basicTimeseriesPanel {
  title: 'Memory Usage (Ovid: ' + ovid + ')',
  gridPos: gridPos,
  options+: { tooltip+: { mode: 'multi', hideZeros: false } },
  targets: [sqlTableTgt {
    refId: 'memUsage' + ovid,
    queryText: |||
      SELECT timestamp, ovid, metric_name, metric_val
      FROM orca_metrics
      WHERE $__timeFilter(timestamp)
      AND metric_name LIKE 'MEMUSE_%%_KB'
      AND ovid = ovid
    |||,
  }],
  fieldConfig+: { defaults+: { unit: 'deckbytes' } },
  transformations: [
    partitionByColXf('metric_name'),
    renameByRegexXf('metric_val MEMUSE_(.*)_KB', '$1'),
  ],
};

// Per-ovid CPU and MEM usage panels
local cpuUsagePanelCTL = cpuUsagePanelTemplate(
  'CTL', metrics_utils.basicGridPos(8, 12, 0, 16)
);
local cpuUsagePanelAGG0 = cpuUsagePanelTemplate(
  'AGG0', metrics_utils.basicGridPos(8, 12, 12, 16)
);
local memUsagePanelCTL = memUsagePanelTemplate(
  'CTL',
  metrics_utils.basicGridPos(8, 12, 0, 24)
);
local memUsagePanelAGG0 = memUsagePanelTemplate(
  'AGG0',
  metrics_utils.basicGridPos(8, 12, 12, 24)
);


// Templating variables variable (if needed)
local templatingVars = { list: [
  {
    name: 'ovid',
    label: 'ORCA Overlay OVID',
    type: 'custom',
    query: 'CTL, AGG0',
    current: { text: 'CTL', value: 'CTL', selected: true },
    options: [
      { text: 'CTL', value: 'CTL', selected: true },
      { text: 'AGG0', value: 'AGG0', selected: false },
    ],
    multi: false,
    includeAll: false,
  },
] };

// Table panel: useful for debugging
local tablePanel = {
  type: 'table',
  title: 'Table Panel',
  gridPos: metrics_utils.basicGridPos(8, 12, 12, 0),
  targets: [sqlTableTgt {
    refId: 'tablePanel',
    queryText: |||
      SELECT * FROM orca_flowexec_stats
      WHERE ovid != 'CTL'
      ORDER BY ts DESC
      LIMIT 5
    |||,
  }],
};

local queryText = |||
  SELECT DISTINCT metric_name FROM orca_metrics
|||;

local queryText = |||
  SELECT * FROM orca_metrics
  WHERE metric_name = 'HGRPC_RATE_BYTES'
  AND ovid == 'CTL'
  ORDER BY timestamp DESC
  LIMIT 20
|||;

local anotherTablePanel = {
  type: 'table',
  title: 'Another Table Panel',
  gridPos: metrics_utils.basicGridPos(8, 12, 0, 16),
  targets: [sqlTableTgt {
    refId: 'anotherTablePanel',
    queryText: queryText,
  }],
};
// Combine all into a dashboard spec variable
local dashboardSpec = {
  title: dashboardTitle,
  uid: dashboardUid,
  schemaVersion: 40,
  timezone: 'browser',
  tags: [],
  time: { from: 'now-5m', to: 'now' },
  refresh: '5s',
  timepicker: {},
  templating: templatingVars,
  panels: [
    // logsPanel,
    // jobStatsPanel,
    rpcBytesPanel,
    rpcCountsPanel,
    // tablePanel,
    // anotherTablePanel,
    cpuUsagePanelCTL,
    cpuUsagePanelAGG0,
    memUsagePanelCTL,
    memUsagePanelAGG0,
  ],
};


// Final dashboard object using the spec variable
{
  apiVersion: 'grizzly.grafana.com/v1alpha1',
  kind: 'Dashboard',
  metadata: { name: dashboardUid, uid: dashboardUid },
  spec: dashboardSpec,
}
