/**
 * Part of Invenio-Stats-Dashboard
 * Copyright (C) 2025 Mesh Research
 *
 * Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
 * it under the terms of the MIT License; see LICENSE file for more details.
 */

import React, { useState, useEffect } from "react";
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
import { fetchStats } from "./api/api";
import { DASHBOARD_TYPES } from "./constants";
import { UpdateStatusMessage } from "./components/shared_components/UpdateStatusMessage";
import PropTypes from "prop-types";

/**
 * Unified stats dashboard layout component
 *
 * This component extracts all common functionality from GlobalStatsDashboardLayout
 * and CommunityStatsDashboardLayout, allowing both to use this shared implementation
 * while preserving their distinctive configurations.
 */
const StatsDashboardLayout = ({
  dashboardConfig,
  dashboardType,
  community = null,
  showSubheader = false,
  containerClassNames,
  sidebarClassNames,
  bodyClassNames,
  getStatsParams = null
}) => {
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
  const [recordStartBasis, setRecordStartBasis] = useState(
    dashboardConfig?.default_record_start_basis || "added"
  );
  const [displaySeparately, setDisplaySeparately] = useState(null);
  const [stats, setStats] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isUpdating, setIsUpdating] = useState(false);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);

  const handleTabChange = (e, { name }) => {
    setSelectedTab(name);
  };

  useEffect(() => {
    let isMounted = true;

    const useTestData = dashboardConfig?.use_test_data !== false;

    fetchStats({
      communityId: community?.id,
      dashboardType,
      getStatsParams,
      community,
      isMounted: () => isMounted,
      useTestData,
      onStateChange: (state) => {
        setStats(state.stats);
        setIsLoading(state.isLoading);
        setIsUpdating(state.isUpdating);
        setError(state.error);

        // Only set lastUpdated if it's provided
        if (state.lastUpdated !== undefined) {
          setLastUpdated(state.lastUpdated);
        }
      }
    });

    // Cleanup function to prevent state updates on unmounted component
    return () => {
      isMounted = false;
    };
  }, [selectedTab, dateRange, community, dashboardType, getStatsParams]);

  const contextValue = {
    binary_sizes,
    community,
    dateRange,
    displaySeparately,
    granularity,
    maxHistoryYears,
    recordStartBasis,
    setRecordStartBasis,
    setDateRange,
    setDisplaySeparately,
    setGranularity,
    stats,
    isLoading,
    isUpdating,
    error,
    lastUpdated,
    ui_subcounts: dashboardConfig?.ui_subcounts,
  };

  return (
    <StatsDashboardProvider value={contextValue}>
      <>
        {showSubheader && (
          <div className="ui container fluid page-subheader-outer compact stats-dashboard-header ml-0-mobile mr-0-mobile">
            <div className="ui container stats-dashboard page-subheader flex align-items-center justify-space-between">
              <h1 className="ui header">
                {dashboardConfig?.title || i18next.t("Statistics")}
              </h1>
              {showDescription && (
                <p className="ui description">{dashboardConfig?.description || ""}</p>
              )}
            </div>
          </div>
        )}
        <Container
          className={`grid ${containerClassNames} rel-m-2 stats-dashboard-container`}
          id={`${dashboardType}-stats-dashboard`}
        >
          <Grid.Row>
            <Grid.Column computer={3} tablet={16} mobile={16} className={`${sidebarClassNames} stats-dashboard-sidebar rel-mt-0`}>
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
              <UpdateStatusMessage
                isUpdating={isUpdating}
                lastUpdated={lastUpdated}
                className="rel-mt-2"
              />
            </Grid.Column>
            <Grid.Column
              computer={13}
              tablet={16}
              mobile={16}
              className={`${bodyClassNames} stats-dashboard-body`}
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
      </>
    </StatsDashboardProvider>
  );
};

StatsDashboardLayout.propTypes = {
  dashboardConfig: PropTypes.object.isRequired,
  dashboardType: PropTypes.string.isRequired,
  community: PropTypes.object,
  showSubheader: PropTypes.bool,
  containerClassNames: PropTypes.string.isRequired,
  sidebarClassNames: PropTypes.string.isRequired,
  bodyClassNames: PropTypes.string.isRequired,
  getStatsParams: PropTypes.func,
};

export { StatsDashboardLayout };
