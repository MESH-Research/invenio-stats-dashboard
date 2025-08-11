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
 * Community stats dashboard layout
 */
const CommunityStatsDashboardLayout = ({ community, dashboardConfig, stats }) => {
  const dashboardType = DASHBOARD_TYPES.COMMUNITY;

  // Community-specific configuration
  const containerClassNames = `${dashboardType}-stats-dashboard communities-stats ${community.slug}`;
  const sidebarClassNames = "communities-detail-left-sidebar";
  const bodyClassNames = "communities-detail-body communities-detail-stats";

  // Community needs custom getStats params (community.id, dashboardType)
  const getStatsParams = (community, dashboardType) => [community.id, dashboardType];

  return (
    <StatsDashboardLayout
      dashboardConfig={dashboardConfig}
      dashboardType={dashboardType}
      community={community}
      showSubheader={false}
      containerClassNames={containerClassNames}
      sidebarClassNames={sidebarClassNames}
      bodyClassNames={bodyClassNames}
      getStatsParams={getStatsParams}
      stats={stats}
    />
  );
};

CommunityStatsDashboardLayout.propTypes = {
  community: PropTypes.object.isRequired,
  dashboardConfig: PropTypes.object.isRequired,
  stats: PropTypes.object,
};

export { CommunityStatsDashboardLayout };
