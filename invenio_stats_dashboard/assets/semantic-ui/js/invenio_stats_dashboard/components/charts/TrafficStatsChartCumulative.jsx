import React from 'react';
import PropTypes from 'prop-types';
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { StatsChart } from '../shared_components/StatsChart';
import { filterByDateRange } from '../../utils';
import { useStatsDashboard } from '../../context/StatsDashboardContext';

const TrafficStatsChartCumulative = ({ title = undefined, height = 300, ...otherProps }) => {
  const { stats, dateRange } = useStatsDashboard();

  // Transform the data into the format expected by StatsChart
  const transformedData = [
    {
      name: i18next.t('Cumulative Unique Views'),
      data: filterByDateRange(stats.cumulativeViews, dateRange)?.map(point => [point.date, point.value]) || [],
      type: 'bar'
    },
    {
      name: i18next.t('Cumulative Unique Downloads'),
      data: filterByDateRange(stats.cumulativeDownloads, dateRange)?.map(point => [point.date, point.value]) || [],
      type: 'bar'
    },
    {
      name: i18next.t('Cumulative Downloaded Data'),
      data: filterByDateRange(stats.cumulativeTraffic, dateRange)?.map(point => [point.date, point.value]) || [],
      type: 'bar'
    }
  ];

  return (
    <StatsChart
      title={title || i18next.t('Cumulative Usage')}
      data={transformedData}
      height={height}
      {...otherProps}
    />
  );
};

TrafficStatsChartCumulative.propTypes = {
  title: PropTypes.string,
  height: PropTypes.number,
};

export { TrafficStatsChartCumulative };