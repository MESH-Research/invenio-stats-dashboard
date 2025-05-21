/**
 * Part of Invenio-Stats-Dashboard
 * Copyright (C) 2025 Mesh Research
 *
 * Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
 * it under the terms of the MIT License; see LICENSE file for more details.
 */

import React, { useState } from "react";
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import {
  Container,
  Grid,
  Icon,
  Menu,
  Transition,
} from "semantic-ui-react";
import { StatsDashboardPage } from "./StatsDashboardPage";
import { DateRangeSelector } from "./components/controls/DateRangeSelector";
import { GranularitySelector } from "./components/controls/GranularitySelector";
import { ReportSelector } from "./components/controls/ReportSelector";
import { StatsDashboardProvider } from "./context/StatsDashboardContext";
import PropTypes from "prop-types";

/**
 * Global stats dashboard layout
 */
const GlobalStatsDashboardLayout = ({ dashboardConfig, stats }) => {
  const availableTabs = dashboardConfig?.layout?.tabs?.map(tab => ({
    name: tab.name,
    label: i18next.t(tab.label),
    icon: tab.icon,
  }));
  const [selectedTab, setSelectedTab] = useState(availableTabs[0].name);
  const showTitle = ["true", "True", "TRUE", "1", true].includes(
    dashboardConfig?.show_title
  );
  const showDescription = ["true", "True", "TRUE", "1", true].includes(
    dashboardConfig?.show_description
  );
  const maxHistoryYears = dashboardConfig?.max_history_years || 15;
  const binary_sizes = dashboardConfig?.display_binary_sizes || false;
  const [dateRange, setDateRange] = useState();
  const [granularity, setGranularity] = useState(
    dashboardConfig?.default_granularity || "day"
  );

  const handleTabChange = (e, { name }) => {
    setSelectedTab(name);
  };

  const contextValue = {
    dateRange,
    setDateRange,
    stats,
    maxHistoryYears,
    binary_sizes,
    granularity,
    setGranularity,
  };

  return (
    <StatsDashboardProvider value={contextValue}>
        <>
      {showTitle && (
        <div class="ui container fluid page-subheader-outer compact stats-dashboard-header ml-0-mobile mr-0-mobile">
          <div class="ui container stats-dashboard page-subheader flex align-items-center justify-space-between">
            <h1 class="ui header">
              {dashboardConfig?.title || i18next.t("Statistics")}
            </h1>
            {showDescription && (
              <p class="ui description">{dashboardConfig?.description || ""}</p>
            )}
          </div>
        </div>
      )}
      <Container
        className="grid global-stats-dashboard rel-m-2"
        id="global-stats-dashboard"
      >
        <Grid.Row>
          <Grid.Column computer={3} tablet={16} mobile={16} className="global-stats-left-sidebar stats-dashboard-sidebar rel-mt-2">
            <Menu
              fluid
              vertical
              className="stats-dashboard-sidebar-menu rel-mt-2 rel-mb-2 theme-primary-menu horizontal tablet horizontal mobile"
            >
              {availableTabs.map(tab => (
                <Menu.Item
                  key={tab.name}
                  name={tab.name}
                  onClick={handleTabChange}
                  active={selectedTab === tab.name}
                >
                  <Icon name={tab.icon} />
                  {tab.label}
                </Menu.Item>
              ))}
            </Menu>
            {showDescription && (
              <p className="ui description">{dashboardConfig?.description || ""}</p>
            )}
            <DateRangeSelector
              dateRange={dateRange}
              defaultRangeOptions={dashboardConfig?.default_range_options}
              granularity={granularity}
              maxHistoryYears={maxHistoryYears}
              setDateRange={setDateRange}
            />
            <GranularitySelector
              defaultGranularity={dashboardConfig?.default_granularity}
              granularity={granularity}
              setGranularity={setGranularity}
            />
            <ReportSelector />
          </Grid.Column>
          <Grid.Column
            width={13}
            className="global-stats-body stats-dashboard-body"
          >
            <Transition.Group animation="fade" duration={{ show: 1000, hide: 20 }}>
              {selectedTab && (
                <StatsDashboardPage
                  dashboardConfig={dashboardConfig}
                  stats={stats}
                  variant={selectedTab}
                  key={selectedTab}
                />
              )}
            </Transition.Group>
          </Grid.Column>
        </Grid.Row>
      </Container>
      </>
    </StatsDashboardProvider>
  );
};

GlobalStatsDashboardLayout.propTypes = {
  dashboardConfig: PropTypes.object.isRequired,
  stats: PropTypes.object.isRequired,
};

export { GlobalStatsDashboardLayout };
