// lib/dashboard.libsonnet
local common = import 'common.libsonnet';

{
  // Creates the basic dashboard structure
  new(title, uid, folder='general'):: {
    apiVersion: 'grizzly.grafana.com/v1alpha1',
    kind: 'Dashboard',
    metadata: {
      name: uid, // Match metadata.name and spec.uid for simplicity
      folder: folder,
    },
    spec: {
      // Add some default dashboard settings
      editable: true,
      fiscalYearStartMonth: 0,
      graphTooltip: 0, // 0 means default shared tooltip
      schemaVersion: 38, // Use a reasonably current schema version
      tags: ['orca', 'grizzly-managed'], // Add some default tags
      timezone: 'browser',
      title: title,
      uid: uid,

      // Default time range
      time: { from: 'now-1h', to: 'now' },
      timepicker: {
        refresh_intervals: ['5s', '10s', '30s', '1m', '5m', '15m', '30m', '1h', '2h', '1d'],
      },

      // Default Annotations (can be overridden)
      annotations: {
        list: [
          {
            builtIn: 1, // Standard Grafana annotations
            datasource: { type: 'grafana', uid: '-- Grafana --' },
            enable: true,
            hide: true,
            iconColor: 'rgba(0, 211, 255, 1)',
            name: 'Annotations & Alerts',
            type: 'dashboard',
          },
          // Example: Adding a custom annotation query (Disabled by default)
          // {
          //   name: 'Deployments',
          //   datasource: { type: common.datasourceType, uid: common.datasourceUid },
          //   enable: false, // Disabled by default
          //   iconColor: '#FF9830', // Orange
          //   showIn: 0, // Show in graph and table
          //   tags: ['deploy', '$environment'], // Example using a variable
          //   queryText: |||
          //     SELECT timestamp, text, tags FROM events
          //     WHERE $__timeFilter(timestamp) AND event_type = 'deployment'
          //   |||,
          //   type: 'tags', // Or 'dashboard' if tags are not used
          // },
        ],
      },

      // Placeholder for templating and panels - to be filled by the main file
      templating: { list: [] },
      panels: [],
    },
  },
}