local mpi_utils = import 'mpi_utils.libsonnet';

// Datasource we pull data from
// (preconfigured)
local fsql_datasource = {
  type: 'influxdata-flightsql-datasource',
  uid: 'datasource-flightsql',
};

// Field config for the panel
// 1. Axis label and limits
// 2. Make timestep appear only in tooltip
// 3. Set unit of probe_val to ns
// 4. Rename timestep to "Sim Timestep" (just to flex)
// 5. Rename probe_val fields
local field_config = mpi_utils.basicFieldConfig {
  defaults+: {
    custom+: { 
      axisLabel: 'Collective Time',
      axisSoftMin: 1e6,
      axisSoftMax: 10e6,
    },
  },
  overrides: [
    mpi_utils.makeFieldTooltipOnly('/timestep/'),
    mpi_utils.overrideUnitByRegex('/.*_probe_val/', 'ns'),
    mpi_utils.renameOverride('timestep', 'Sim Timestep'),
    mpi_utils.renameOverride('max_probe_val', 'Max Probe Val'),
    mpi_utils.renameOverride('min_probe_val', 'Min Probe Val'),
  ],
};

// mode: 'single' or 'multi'
local tooltip = { hideZeros: false, mode: 'multi', sort: 'none' };

// Template variable: all collectives
// Currently set from probe_map, maybe a better source exists
local template_var = mpi_utils.addTemplateVar(
  'collective',
  'Collective',
  'SELECT * FROM probe_map;',
) + {
  current: { text: ['MPI_Barrier'], value: ['MPI_Barrier'] },
  datasource: fsql_datasource,
};

// Panel config
// 1. Basic timeseries panel, with title, datasource, pos, desc
// 2. Field config (rename, hide, units etc.)
// 3. Repeats for each value of the template var 'collective'
// 4. Target is a table 'mpi_collectives'
// 5. We filter by ${collective} and group by timestep to get min/max
// 6. No transformations (may need some for a different view)
local mpi_panel = {
  type: 'timeseries',
  title: 'MPI Collective: $collective', // panel repeats per template var
  datasource: fsql_datasource, // panel data source
  gridPos: mpi_utils.basicGridPos(6, 24, 0, 0),  // hwxy
  description: 'MPI Collective Operations',
  fieldConfig: field_config,
  options: { legend: mpi_utils.basic_legend, tooltip: tooltip },
  repeat: 'collective', // repeat panel for each template var
  repeatDirection: 'v', // repeat vertically
  targets: [
    {
      refId: 'mpi_collectives',
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
  transformations: [],
};


// Dashboard config
// 1. Title and uid (grafana complains if uid != title??)
// 2. Tags, panels, template vars
local dashboardTitle = 'MPI Monitoring Dashboard';
local dashboardUid = 'mpi-dashboard';

mpi_utils.basicDashboard(dashboardUid, dashboardUid) + {
  spec+: {
    tags: ['orca', 'orca-mpi'],
    title: dashboardTitle,
    panels: [mpi_panel],
    templating: { list: [template_var] },
  },
}
