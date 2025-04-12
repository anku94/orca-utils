// orca-dashboard.jsonnet
local common = import 'common.libsonnet';
local dashboard = import 'dashboard.libsonnet';
local panels = import 'panels.libsonnet';

// Define dashboard constants
local dashboardTitle = 'ORCA Monitoring Dashboard';
local dashboardUid = 'orca-dashboard';  // Keep consistent with metadata.name

local allPanelPos = {
  logsPanel: common.basicGridPos(h=16, w=12, x=0, y=0),
  jobStatsPanel: common.basicGridPos(h=8, w=12, x=12, y=0),
  rpcRatesPanel: common.basicGridPos(h=8, w=12, x=12, y=8),
  cpuUsagePanel: common.basicGridPos(h=8, w=12, x=0, y=8),
  memoryUsagePanel: common.basicGridPos(h=8, w=12, x=0, y=16),
};

// Create the base dashboard structure
dashboard.new(dashboardTitle, dashboardUid)

// Merge in specific configurations
// Some fields may be overridden
+ {
  spec+: {  // Use spec+ to merge into the existing spec from dashboard.new()
    // -- Dashboard Refresh and Time --
    refresh: '5s',  // Set a faster refresh rate
    time: { from: 'now-5m', to: 'now' },  // Shorter default time range

    // -- Templating Variables --
    templating+: {  // Use templating+ to merge into existing list (if any)
      list: [
        // OVID Selector
        {
          name: 'ovid',  // Variable name used in queries/transforms: ${ovid} or $ovid
          label: 'ORCA overlay ovid',  // Display label in UI
          type: 'custom',  // Dropdown with custom values
          query: 'CTL, AGG0',  // Comma-separated values
          current: { selected: true, text: 'CTL', value: 'CTL' },  // Default value
          options: [  // Explicit options list for UI
            { selected: true, text: 'CTL', value: 'CTL' },
            { selected: false, text: 'AGG0', value: 'AGG0' },
          ],
          multi: false,  // Allow selecting only one instance
          includeAll: false,
        },
        // Log Level Selector
        {
          name: 'log_level',
          label: 'Minimum Log Level',
          type: 'custom',
          query: 'ERR : 4194304, INFO : 1048576, DBUG : 262144',  // Value : Text pairs
          current: { selected: true, text: 'DBUG', value: '262144' },  // Default to Debug
          options: [  // Explicit options are good practice
            { selected: false, text: 'ERR', value: '4194304' },
            { selected: false, text: 'INFO', value: '1048576' },
            { selected: true, text: 'DBUG', value: '262144' },
          ],
          multi: false,  // Select only one level
          includeAll: false,
          allowCustomValue: false,
        },
        // CPU Level Selector
        {
          name: 'cpu_level',
          label: 'CPU Level',
          type: 'custom',
          query: 'system, core',
          current: { selected: true, text: 'core', value: 'core' },  // Default to core view
          options: [
            { selected: false, text: 'system', value: 'system' },
            { selected: true, text: 'core', value: 'core' },
          ],
          multi: false,
          includeAll: false,
          allowCustomValue: false,
        },
        // CPU core range specified in a textbox
        // Format is start-end
        // Currently unused
        {
          name: 'core_range',
          label: 'CPU Core Range',
          type: 'textbox',
          current: { text: '', value: '' },
          query: '',  // Textbox query is usually empty
          options: [],
        },
      ],
    },

    // -- Panel Definitions --
    // Use the panel functions, specifying grid positions
    panels+: [  // Use panels+ to merge into existing list (if any)
      // -- Row 1: Status & Logs --
      panels.row(title='ORCA Status & Logs', y_pos=0),
      panels.logsPanel(
        title='ORCA Logs',
        gridPos=allPanelPos.logsPanel,  // Made wider
        ovidVarName='ovid',
        logLevelVarName='log_level'
      ),
      panels.jobStatsPanel(
        title='ORCA Job Stats',
        gridPos=allPanelPos.jobStatsPanel  // Adjusted position
      ),

      // // -- Row 2: Core Metrics --
      // panels.row(title='ORCA Core Metrics', y_pos=7),  // Adjusted y_pos
      panels.ovidCpuUsagePanel(
        gridPos=common.basicGridPos(h=8, w=12, x=0, y=16),
        targetOvid='CTL'
      ),
      panels.ovidMemoryUsagePanel(
        gridPos=common.basicGridPos(h=8, w=12, x=0, y=24),
        targetOvid='CTL'
      ),
      panels.ovidCpuUsagePanel(
        gridPos=common.basicGridPos(h=8, w=12, x=12, y=16),
        targetOvid='AGG0'
      ),
      panels.ovidMemoryUsagePanel(
        gridPos=common.basicGridPos(h=8, w=12, x=12, y=24),
        targetOvid='AGG0'
      ),
      // panels.memoryUsagePanel(
      //   title='Memory Usage',
      //   gridPos=allPanelPos.memoryUsagePanel,  // Adjusted position
      //   ovidVarName='ovid'
      // ),
      panels.rpcRatesPanel(
        title='RPC Rates',
        gridPos=allPanelPos.rpcRatesPanel,  // Adjusted position
        ovidVarName='ovid'
      ),
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
