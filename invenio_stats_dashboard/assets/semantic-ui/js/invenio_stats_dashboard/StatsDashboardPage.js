import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";
import { Label, Grid } from "semantic-ui-react";
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { componentsMap } from './components/components_map';
import { useStatsDashboard } from './context/StatsDashboardContext';
import { formatDate, formatDateRange } from './utils/dates';

/**
 * StatsDashboard page layout component
 *
 * This component converts the layout configuration object into a grid layout
 * and renders the components in the grid.
 *
 * @param {Object} dashboardConfig - The dashboard configuration
 * @param {Object} stats - The stats object
 * @param {Object} community - The community object if the dashboard is for a community
 * @param {string} variant - The variant (one of "content", "traffic")
 */
const StatsDashboardPage = ({ dashboardConfig, stats, community = undefined, variant, ...otherProps }) => {
  const layout = dashboardConfig.layout;
  const pageDateRangePhrase = layout?.tabs?.find(tab => tab.name === variant)?.date_range_phrase;
  const [displayDateRange, setDisplayDateRange] = useState(null);
  const { dateRange } = useStatsDashboard();

  useEffect(() => {
    if (dateRange) {
      const newDisplayDateRange = ['content', 'traffic'].includes(variant) ? formatDate(dateRange.end, true, false) : formatDateRange(dateRange, true);
      setDisplayDateRange(newDisplayDateRange);
    }
  }, [dateRange, variant]);

  const renderComponent = (componentConfig) => {
    const Component = componentsMap[componentConfig.component];
    if (!Component) {
      return null;
    }

    return (
      <Grid.Column computer={componentConfig.width} tablet={16} mobile={16} key={componentConfig.component}
        className={`${componentConfig.component.startsWith('SingleStat') ? 'centered' : ''}`}
      >
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
  const defaultTitle = dashboardConfig?.dashboard_type === "global" ? i18next.t("Global Statistics Dashboard") : `${community.metadata.title} ${i18next.t("Statistics Dashboard")}`;

  return (
    <Grid className={`container stats-dashboard-content ${variant}`} role="main" aria-label={dashboardConfig.title || defaultTitle} {...otherProps}>
      <Grid.Row className="pb-0">
        <Grid.Column width={16} className="centered">
          <Label className="stats-dashboard-date-range-label" pointing="below">{pageDateRangePhrase} {displayDateRange}</Label>
        </Grid.Column>
      </Grid.Row>
      {currentTab.rows.map((row, index) => (
        <Grid.Row key={row.name} className="stats-dashboard-row pb-0 pt-0">
          {row.components.map(componentConfig => renderComponent(componentConfig))}
        </Grid.Row>
      ))}
    </Grid>
  );
};

StatsDashboardPage.propTypes = {
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
  community: PropTypes.object,
  variant: PropTypes.string.isRequired,
};

export { StatsDashboardPage };
