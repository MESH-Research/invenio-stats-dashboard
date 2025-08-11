/**
 * Part of Invenio-Stats-Dashboard
 * Copyright (C) 2025 Mesh Research
 *
 * Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
 * it under the terms of the MIT License; see LICENSE file for more details.
 */

import React from "react";
import { StatsDashboardLayout } from "./StatsDashboardLayout";
import { DASHBOARD_TYPES } from "./constants";
import PropTypes from "prop-types";

/**
 * Global stats dashboard layout
 */
const GlobalStatsDashboardLayout = ({ dashboardConfig, stats }) => {
  const dashboardType = DASHBOARD_TYPES.GLOBAL;

  // Global-specific configuration
  const containerClassNames = `${dashboardType}-stats-dashboard`;
  const sidebarClassNames = "global-stats-left-sidebar";
  const bodyClassNames = "global-stats-body";

  // Global uses default getStats behavior (no custom params needed)
  const getStatsParams = null;

  return (
    <StatsDashboardLayout
      dashboardConfig={dashboardConfig}
      dashboardType={dashboardType}
      showSubheader={true}
      containerClassNames={containerClassNames}
      sidebarClassNames={sidebarClassNames}
      bodyClassNames={bodyClassNames}
      getStatsParams={getStatsParams}
      stats={stats}
    />
  );
};

GlobalStatsDashboardLayout.propTypes = {
  dashboardConfig: PropTypes.object.isRequired,
  stats: PropTypes.object,
};

export { GlobalStatsDashboardLayout };
