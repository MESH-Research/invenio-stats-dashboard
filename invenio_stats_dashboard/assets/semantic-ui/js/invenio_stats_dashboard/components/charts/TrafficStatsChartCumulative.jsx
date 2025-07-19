import React from 'react';
import PropTypes from 'prop-types';
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { StatsChart } from '../shared_components/StatsChart';
import { useStatsDashboard } from '../../context/StatsDashboardContext';

/**
 * Cumulative traffic stats chart.
 *
 * This chart shows the cumulative usage of the community or whole repository
 * over time. It renders a bar chart with cumulative statistics for views,
 * downloads, and data volume downloaded. The chart is interactive and allows
 * users to select which metric to display. It also allows users to view the
 * data subdivided based on each record's metadata properties such as access
 * status, creator's affiliation, file type, and visitor country.
 *
 * @param {Object} props - The component props.
 * @param {string} [props.title] - The chart title.
 * @param {number} [props.height] - The chart height.
 */
const TrafficStatsChartCumulative = ({ title = undefined, height = 300, ...otherProps }) => {
  const { stats } = useStatsDashboard();

  const seriesSelectorOptions = [
    { value: 'views', text: i18next.t('Cumulative Views') },
    { value: 'downloads', text: i18next.t('Cumulative Downloads') },
    { value: 'dataVolume', text: i18next.t('Cumulative Downloaded Data'), valueType: 'filesize' }
  ];

  return (
    <StatsChart
      title={title || i18next.t('Cumulative Usage')}
      data={stats.usageSnapshotData}
      seriesSelectorOptions={seriesSelectorOptions}
      height={height}
      {...otherProps}
    />
  );
}

TrafficStatsChartCumulative.propTypes = {
  title: PropTypes.string,
  height: PropTypes.number,
};

export { TrafficStatsChartCumulative };