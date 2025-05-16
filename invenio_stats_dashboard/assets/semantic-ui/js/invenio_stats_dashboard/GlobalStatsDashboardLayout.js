/**
 * Part of Invenio-Stats-Dashboard
 * Copyright (C) 2025 Mesh Research
 *
 * Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
 * it under the terms of the MIT License; see LICENSE file for more details.
 */

import React from "react";
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { Grid, Header } from "semantic-ui-react";
import { StatsDashboard } from "./StatsDashboard";
import PropTypes from "prop-types";

/**
 * Global stats dashboard layout
 *
 */
const GlobalDashboardLayout = ({ dashboardConfig, stats }) => {
  return (
    <Grid id="global-stats-dashboard" class={`rel-m-2 global-stats-dashboard`}>
      <Grid.Row>
        <Grid.Column width={3} className="global-stats-dashboard-left-sidebar">
          <Header as="h2" className="stats-dashboard-header">
            {dashboardConfig.title || i18next.t("Community Statistics")}
          </Header>
        </Grid.Column>
        <Grid.Column width={13} className="global-stats-dashboard-body global-stats-dashboard-stats">
          <StatsDashboard
            dashboardConfig={dashboardConfig}
            stats={stats}
          />
        </Grid.Column>
      </Grid.Row>
    </Grid>
  );
};

GlobalDashboardLayout.propTypes = {
  dashboardConfig: PropTypes.object.isRequired,
  stats: PropTypes.object.isRequired,
};

export { GlobalDashboardLayout };
