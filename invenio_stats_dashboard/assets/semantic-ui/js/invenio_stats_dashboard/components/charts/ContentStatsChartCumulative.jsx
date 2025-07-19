import React from 'react';
import PropTypes from 'prop-types';
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { StatsChart } from '../shared_components/StatsChart';
import { useStatsDashboard } from '../../context/StatsDashboardContext';

/**
 * Cumulative content stats chart.
 *
 * This chart shows the cumulative growth of the community or whole repository
 * over time. It renders a bar chart with cumulative statistics for records,
 * data volume, and uploaders. The chart is interactive and allows users to
 * select which metric to display. It also allows users to view the data
 * subdivided based on each record's metadata properties such as access
 * status, creator's affiliation, file type, and visitor country.
 *
 * @param {Object} props - The component props.
 * @param {string} [props.title] - The chart title.
 * @param {number} [props.height] - The chart height.
 */
const ContentStatsChartCumulative = ({ title = undefined, height = 300, ...otherProps }) => {
  const { stats } = useStatsDashboard();

  const seriesSelectorOptions = [
    { value: 'records', text: i18next.t('Records') },
    { value: 'files', text: i18next.t('Files') },
    { value: 'dataVolume', text: i18next.t('Data Volume'), valueType: 'filesize' },
    { value: 'uploaders', text: i18next.t('Uploaders') }
  ];

  return (
    <StatsChart
      title={title || i18next.t('Cumulative Growth')}
      data={stats.recordSnapshotDataAdded}
      seriesSelectorOptions={seriesSelectorOptions}
      height={height}
      {...otherProps}
    />
  );
};

ContentStatsChartCumulative.propTypes = {
  title: PropTypes.string,
  height: PropTypes.number,
};

export { ContentStatsChartCumulative };