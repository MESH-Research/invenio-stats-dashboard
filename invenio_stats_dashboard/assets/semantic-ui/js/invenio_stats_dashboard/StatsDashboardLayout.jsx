import React from "react";
import { StatsDashboardPage } from "./StatsDashboardPage";
import PropTypes from "prop-types";

/**
 * A component that displays a stats dashboard.
 *
 * Intended as a generic layout component to be customized via props for
 * specific use cases.
 *
 * @param {Object} props - The props for the StatsDashboard component.
 * @param {Object} props.dashboardConfig - The dashboard configuration.
 * @param {Object} props.stats - The stats object.
 */
const StatsDashboardLayout = (props) => {
  return <StatsDashboardPage {...props} />;
};

StatsDashboardLayout.propTypes = {
  dashboardConfig: PropTypes.object.isRequired,
  stats: PropTypes.object.isRequired,
};

export { StatsDashboardLayout };
