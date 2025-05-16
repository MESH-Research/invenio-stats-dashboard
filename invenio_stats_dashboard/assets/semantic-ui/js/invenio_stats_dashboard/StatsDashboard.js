import React, { useState } from "react";
import PropTypes from "prop-types";
import { Container, Grid, Header } from "semantic-ui-react";
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { componentsMap } from './components/components_map';
import { StatsDashboardProvider } from './context/StatsDashboardContext';
import { today, getLocalTimeZone } from "@internationalized/date";

const StatsDashboard = ({ dashboardConfig, stats, community, variant, ...otherProps }) => {
  const maxHistoryYears = dashboardConfig?.max_history_years || 15;
  const binary_sizes = dashboardConfig?.display_binary_sizes || false;
  const layout = dashboardConfig.layout;

  const [dateRange, setDateRange] = useState({
    start: today(getLocalTimeZone()).subtract({ days: 30 }),
    end: today(getLocalTimeZone())
  });

  const [granularity, setGranularity] = useState(dashboardConfig?.granularity || "day");

  const contextValue = {
    dateRange,
    setDateRange,
    stats,
    maxHistoryYears,
    binary_sizes,
    community,
    granularity,
    setGranularity,
  };

  const renderComponent = (componentConfig) => {
    const Component = componentsMap[componentConfig.component];
    if (!Component) {
      console.warn(`Component ${componentConfig.component} not found`);
      return null;
    }

    return (
      <Grid.Column width={componentConfig.width} key={componentConfig.component}>
        <Component {...componentConfig.props} />
      </Grid.Column>
    );
  };

  // Find the tab that matches the variant
  const currentTab = layout.tabs.find(tab => tab.name === variant);
  if (!currentTab) {
    console.warn(`No tab found for variant: ${variant}`);
    return null;
  }

  return (
    <StatsDashboardProvider value={contextValue}>
      <Grid className={`container stats-dashboard-content ${variant}`} role="main" aria-label={dashboardConfig?.title || `${community.metadata.title} ${i18next.t("Statistics Dashboard")}`} {...otherProps}>
          <Grid.Row>
            <Grid.Column width={16}>
              <Header as="h2" className="stats-dashboard-header">
                {!!dashboardConfig?.title && dashboardConfig?.title}
              </Header>
            </Grid.Column>
          </Grid.Row>
          {!!dashboardConfig?.description && (
            <Grid.Row>
              <Grid.Column width={16}>
                <p>{dashboardConfig?.description}</p>
              </Grid.Column>
            </Grid.Row>
          )}
          {currentTab.rows.map((row, index) => (
            <Grid.Row key={row.name}>
              {row.components.map(componentConfig => renderComponent(componentConfig))}
            </Grid.Row>
          ))}
      </Grid>
    </StatsDashboardProvider>
  );
};

StatsDashboard.propTypes = {
  dashboardConfig: PropTypes.object.isRequired,
  stats: PropTypes.shape({
    views: PropTypes.arrayOf(
      PropTypes.shape({
        date: PropTypes.string.isRequired,
        value: PropTypes.number.isRequired,
      })
    ),
    downloads: PropTypes.arrayOf(
      PropTypes.shape({
        date: PropTypes.string.isRequired,
        value: PropTypes.number.isRequired,
      })
    ),
    dataVolume: PropTypes.arrayOf(
      PropTypes.shape({
        date: PropTypes.string.isRequired,
        value: PropTypes.number.isRequired,
      })
    ),
    traffic: PropTypes.arrayOf(
      PropTypes.shape({
        date: PropTypes.string.isRequired,
        value: PropTypes.number.isRequired,
      })
    ),
    uploaders: PropTypes.arrayOf(
      PropTypes.shape({
        date: PropTypes.string.isRequired,
        value: PropTypes.number.isRequired,
      })
    ),
    recordCount: PropTypes.arrayOf(
      PropTypes.shape({
        date: PropTypes.string.isRequired,
        value: PropTypes.number.isRequired,
      })
    ),
  }).isRequired,
  community: PropTypes.object.isRequired,
  variant: PropTypes.string.isRequired,
};

export { StatsDashboard };
