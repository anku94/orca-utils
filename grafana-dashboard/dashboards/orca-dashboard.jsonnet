// orca-dashboard.jsonnet
// local dashboard = import 'lib/dashboard.libsonnet';
// local panels = import 'lib/panels.libsonnet';
// local common = import 'lib/common.libsonnet';

local dashboard = import 'dashboard.libsonnet';
local panels = import 'panels.libsonnet';
local common = import 'common.libsonnet';

// Define dashboard constants
local dashboardTitle = 'ORCA Monitoring Dashboard';
local dashboardUid = 'orca-dashboard'; // Keep consistent with metadata.name

// Create the base dashboard structure
dashboard.new(dashboardTitle, dashboardUid)

// Merge in specific configurations
+ {
  spec+: { // Use spec+ to merge into the existing spec from dashboard.new()
    // -- Dashboard Refresh and Time --
    refresh: '10s', // Set a faster refresh rate
    time: { from: 'now-15m', to: 'now' }, // Shorter default time range

    // -- Templating Variables --
    templating+: { // Use templating+ to merge into existing list (if any)
      list: [
        // OVID Selector
        {
          name: 'ovid', // Variable name used in queries/transforms: ${ovid} or $ovid
          label: 'ORCA Instance', // Display label in UI
          type: 'custom', // Dropdown with custom values
          query: 'CTL, AGG0', // Comma-separated values
          current: { selected: true, text: 'CTL', value: 'CTL' }, // Default value
          options: [ // Explicit options list for UI
            { selected: true, text: 'CTL', value: 'CTL' },
            { selected: false, text: 'AGG0', value: 'AGG0' },
          ],
          multi: false, // Allow selecting only one instance
          includeAll: false,
        },
        // Log Level Selector
        {
          name: 'log_level',
          label: 'Minimum Log Level',
          type: 'custom',
          query: 'ERR : 4194304, INFO : 1048576, DBUG : 262144', // Value : Text pairs
          current: { selected: true, text: 'DBUG', value: '262144' }, // Default to Debug
          options: [ // Explicit options are good practice
            { selected: false, text: 'ERR', value: '4194304' },
            { selected: false, text: 'INFO', value: '1048576' },
            { selected: true, text: 'DBUG', value: '262144' },
          ],
          multi: false, // Select only one level
          includeAll: false,
        },
        // CPU Level Selector
        {
          name: 'cpu_level',
          label: 'CPU View',
          type: 'custom',
          query: 'process, system, core',
          current: { selected: true, text: 'core', value: 'core' }, // Default to core view
          options: [
            { selected: false, text: 'process', value: 'process' },
            { selected: false, text: 'system', value: 'system' },
            { selected: true, text: 'core', value: 'core' },
          ],
          multi: false,
          includeAll: false,
        },
        // Example Textbox variable (not used in original YAML, but demonstrates type)
        // {
        //   name: 'custom_filter',
        //   label: 'Custom Text Filter',
        //   type: 'textbox',
        //   current: { text: '', value: '' },
        //   query: '', // Textbox query is usually empty
        //   options: [],
        // },
      ],
    },

    // -- Panel Definitions --
    // Use the panel functions, specifying grid positions
    panels+: [ // Use panels+ to merge into existing list (if any)
      // -- Row 1: Status & Logs --
      panels.row(title='ORCA Status & Logs', y_pos=0),
      panels.logsPanel(
        title='ORCA Logs',
        gridPos=common.basicGridPos(h=8, w=16, x=0, y=1), // Made wider
        // Pass variable names explicitly if different from defaults
        // ovidVarName='ovid_instance',
        // logLevelVarName='min_log_level'
      ),
      // panels.jobStatsPanel(
      //   title='ORCA Job Stats',
      //   gridPos=common.basicGridPos(h=8, w=8, x=16, y=1) // Adjusted position
      // ),

      // -- Row 2: Core Metrics --
      // panels.row(title='ORCA Core Metrics', y_pos=9), // Adjusted y_pos
      // panels.cpuUsagePanel(
      //   title='CPU Usage (%)',
      //   gridPos=common.basicGridPos(h=8, w=12, x=0, y=10) // Adjusted position
      // ),
      // panels.memoryUsagePanel(
      //   title='Memory Usage',
      //   gridPos=common.basicGridPos(h=8, w=12, x=12, y=10) // Adjusted position
      // ),

      // -- Row 3: RPC --
      // panels.row(title='RPC Metrics', y_pos=18), // Adjusted y_pos
      // panels.rpcRatesPanel(
      //   title='RPC Rates',
      //   gridPos=common.basicGridPos(h=8, w=12, x=0, y=19) // Adjusted position
      // ),
      // Example: Add a new simple panel using the generic function
      // panels.basicMetricsTimeseries(
      //   title='Disk IOPS',
      //   queryText='SELECT timestamp, ovid, metric_name, metric_val FROM orca_metrics WHERE $__timeFilter(timestamp) AND metric_name = "DISK_IOPS"',
      //   gridPos=common.basicGridPos(h=8, w=12, x=12, y=19), // Adjusted position
      //   extraTransforms=[common.filterByOvidTransformation('ovid')], // Use common filter
      //   extraFieldConfig={ defaults+: { unit: 'iops' } } // Set unit
      // ),
    ],
  },
}