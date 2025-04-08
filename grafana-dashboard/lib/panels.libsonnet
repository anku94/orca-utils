// lib/panels.libsonnet
local common = import 'common.libsonnet';

{
  // Function to create a simple row panel
  row(title, y_pos):: {
    type: 'row',
    title: title,
    gridPos: common.basicGridPos(h=1, w=24, x=0, y=y_pos),
    collapsed: false, // Rows start expanded
    panels: [], // Rows contain other panels (though not used this way in original YAML)
  },

  // Function for the ORCA Logs panel
  logsPanel(title, gridPos, ovidVarName='ovid', logLevelVarName='log_level'):: {
    type: 'logs',
    title: title,
    datasource: { type: common.datasourceType, uid: common.datasourceUid },
    gridPos: gridPos,
    options: { // Simplified common log panel options
      enableLogDetails: true,
      sortOrder: 'Descending',
      wrapLogMessage: false,
      prettifyLogMessage: false, // Usually false for structured logs
      showTime: true, // Default to showing time
      showLabels: false,
      showCommonLabels: false,
      dedupStrategy: 'none',
      enableInfiniteScrolling: false, // Better for defined time ranges
    },
    targets: [
      {
        refId: 'A',
        datasource: { type: common.datasourceType, uid: common.datasourceUid },
        format: 'table', // Logs often work best with table format
        rawQuery: true, // Assuming SQL backend handles variables well
        queryText: |||
          SELECT timestamp, ovid, level, message
          FROM orca_logs
          WHERE $__timeFilter(timestamp)
        |||
      },
    ],
    //  AND level >= ${%s:value} // use :value for safety
    // Apply the standard OVID filter transformation
    transformations: [
      common.filterByOvidTransformation(ovidVarName),
    ],
  },

  // Generic function for basic timeseries panels querying metrics
  // We pass the full query text and optional transformations/fieldConfig overrides
  basicMetricsTimeseries(title, queryText, gridPos, extraFieldConfig={}, extraTransforms=[]):: {
    type: 'timeseries',
    title: title,
    datasource: { type: common.datasourceType, uid: common.datasourceUid },
    gridPos: gridPos,
    // Start with common defaults and deep merge extras
    fieldConfig: std.mergePatch(common.defaultTimeseriesFieldConfig, extraFieldConfig),
    options: { // Common timeseries options
      legend: { calcs: [], displayMode: 'list', placement: 'bottom', showLegend: true },
      tooltip: { mode: 'multi', sort: 'none' }, // Changed default to multi tooltip
    },
    targets: [
      {
        refId: 'A',
        datasource: { type: common.datasourceType, uid: common.datasourceUid },
        format: 'table', // Assuming FlightSQL returns tables
        rawQuery: true,
        queryText: queryText,
      },
    ],
    transformations: extraTransforms, // Add specific transforms
  },

  // Specific panel function for ORCA Job Stats (using the generic timeseries)
  jobStatsPanel(title, gridPos)::
    self.basicMetricsTimeseries(
      title,
      queryText=|||
        SELECT timestamp, ovid, job_id, sql, name, enter_time, end_time, status, error
        FROM orca_job_stats
        WHERE $__timeFilter(timestamp)
      |||,
      gridPos=gridPos,
      // Example: Customize field config for this specific panel
      extraFieldConfig={
        defaults+: { unit: 'short' }, // Example override: use short duration unit
        overrides: [ // Example override: color 'status' based on value
          {
            matcher: { id: 'byName', options: 'status' },
            properties: [
              { id: 'color', value: { mode: 'thresholds' } }, // Use thresholds for color
              {
                id: 'thresholds',
                value: {
                  mode: 'absolute',
                  steps: [
                    { color: 'red', value: 0 },     // Assuming 0 is error
                    { color: 'green', value: 1 },   // Assuming 1 is success
                    { color: 'orange', value: 2 }, // Assuming 2 is running
                  ],
                },
              },
              { id: 'custom.width', value: 150 }, // Example: Set column width
            ],
          },
        ],
      }
    ),

  // Specific panel for CPU Usage
  cpuUsagePanel(title, gridPos, ovidVarName='ovid', cpuLevelVarName='cpu_level')::
    self.basicMetricsTimeseries(
      title,
      // Using $variables directly in SQL (ensure your backend handles this)
      queryText=|||
        SELECT timestamp, ovid, metric_name, metric_val
        FROM orca_metrics
        WHERE $__timeFilter(timestamp) AND metric_name LIKE 'CPU%%_USAGE_PCT'
          AND ('${%s:value}' = 'system' AND metric_name = 'CPU_USAGE_PCT'
            OR '${%s:value}' = 'core' AND metric_name ~ 'CPU[0-9]+_USAGE_PCT'
          )
      ||| % [cpuLevelVarName, cpuLevelVarName], // Inject variable names
      gridPos=gridPos,
      extraFieldConfig={ defaults+: { unit: 'percent' } }, // Set unit to percent
      // Combine standard OVID filter with standard timeseries transforms and specific rename
      extraTransforms=[common.filterByOvidTransformation(ovidVarName)] +
                      common.standardTimeseriesTransformations +
                      [
                        { // Add the specific rename for CPU cores
                          id: 'renameByRegex',
                          options: { regex: 'metric_val CPU([0-9]+)_USAGE_PCT', renamePattern: 'core-$1' },
                        },
                        { // Example: Adding another transformation - series override color
                          id: 'seriesOverrides',
                          options: {
                            overrides: [
                              { matcher: { id: 'byName', options: 'CPU_USAGE_PCT' }, properties: [{ id: 'color', value: 'blue' }] },
                              { matcher: { id: 'byRegexp', options: '/core-.*/' }, properties: [{ id: 'color', value: 'semi-dark-orange' }] },
                            ],
                          },
                        },
                      ]
    ),

  // Specific panel for Memory Usage
  memoryUsagePanel(title, gridPos, ovidVarName='ovid')::
    self.basicMetricsTimeseries(
      title,
      queryText=|||
        SELECT timestamp, ovid, metric_name, metric_val
        FROM orca_metrics
        WHERE $__timeFilter(timestamp) AND metric_name LIKE 'MEMUSE_%%'
      |||,
      gridPos=gridPos,
      // Specific Field Config Overrides for Memory units
      extraFieldConfig={
        overrides: [
          { matcher: { id: 'byName', options: 'MEMUSE_TOTAL_KB' }, properties: [{ id: 'unit', value: 'deckbytes' }] }, // Kilobytes
          { matcher: { id: 'byName', options: 'MEMUSE_TOTAL_PCT' }, properties: [{ id: 'unit', value: 'percent' }] }, // Percent (0-100)
          { matcher: { id: 'byName', options: 'MEMUSE_AVAIL_KB' }, properties: [{ id: 'unit', value: 'deckbytes' }] },
          { matcher: { id: 'byName', options: 'MEMUSE_FREE_KB' }, properties: [{ id: 'unit', value: 'deckbytes' }] },
        ],
      },
      // Standard OVID filter, standard transforms, and specific rename
      extraTransforms=[common.filterByOvidTransformation(ovidVarName)] +
                      common.standardTimeseriesTransformations +
                      [{ id: 'renameByRegex', options: { regex: 'metric_val (MEMUSE_.*)', renamePattern: '$1' } }]
    ),

  // Specific panel for RPC Rates
  rpcRatesPanel(title, gridPos, ovidVarName='ovid')::
    self.basicMetricsTimeseries(
      title,
      queryText=|||
        SELECT timestamp, ovid, metric_name, metric_val
        FROM orca_metrics
        WHERE $__timeFilter(timestamp) AND metric_name LIKE 'HGRPC_RATE_%%'
      |||,
      gridPos=gridPos,
      // Specific Field Config Overrides for RPC units
      extraFieldConfig={
        overrides: [
          // Example: Requests per second (assuming that's what HGRPC_RATE means)
          { matcher: { id: 'byRegexp', options: '/HGRPC_RATE_REQ/' }, properties: [{ id: 'unit', value: 'reqps' }] },
          // Example: Bytes per second
          { matcher: { id: 'byRegexp', options: '/HGRPC_RATE_BYTES/' }, properties: [{ id: 'unit', value: 'binBps' }] }, // Using binary bytes/sec
        ],
      },
      // Standard OVID filter, standard transforms, and specific rename
      extraTransforms=[common.filterByOvidTransformation(ovidVarName)] +
                      common.standardTimeseriesTransformations +
                      [{ id: 'renameByRegex', options: { regex: 'metric_val (.*)', renamePattern: '$1' } }]
    ),
}