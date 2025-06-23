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
 * Community stats dashboard layout
 */
const CommunityStatsDashboardLayout = ({ community, dashboardConfig }) => {
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
  console.log("dateRange", dateRange);
  const [granularity, setGranularity] = useState(
    dashboardConfig?.default_granularity || "day"
  );
  const [displaySeparately, setDisplaySeparately] = useState(null);
  const [stats, setStats] = useState(null);

  const handleTabChange = (e, { name }) => {
    setSelectedTab(name);
  };

  useEffect(() => {
    statsApiClient.getStats(community.id, DASHBOARD_TYPES.COMMUNITY).then(setStats);
  }, [selectedTab, dateRange]);

  const contextValue = {
    binary_sizes,
    community,
    dateRange,
    displaySeparately,
    granularity,
    maxHistoryYears,
    setDateRange,
    setDisplaySeparately,
    setGranularity,
    stats,
  };
  return (
    <StatsDashboardProvider value={contextValue}>
      <Container
        className={`grid communities-stats ${community.slug} rel-m-2`}
        id="communities-detail-stats-dashboard"
      >
        <Grid.Row>
          <Grid.Column computer={3} tablet={16} mobile={16} className="communities-detail-left-sidebar stats-dashboard-sidebar rel-mt-0">
            {showTitle && (
              <h2 className="stats-dashboard-header tablet computer widescreen large-monitor only">
                {dashboardConfig.title || i18next.t("Statistics")}
              </h2>
            )}
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
              <p class="ui description">{dashboardConfig?.description || ""}</p>
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
            computer={13}
            tablet={16}
            mobile={16}
            className="communities-detail-body communities-detail-stats"
          >
            <Transition.Group animation="fade" duration={{ show: 1000, hide: 20 }}>
              {selectedTab && (
                <StatsDashboardPage
                  community={community}
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
    </StatsDashboardProvider>
  );
};

CommunityStatsDashboardLayout.propTypes = {
  community: PropTypes.object.isRequired,
  dashboardConfig: PropTypes.object.isRequired,
  stats: PropTypes.object.isRequired,
};

export { CommunityStatsDashboardLayout };
