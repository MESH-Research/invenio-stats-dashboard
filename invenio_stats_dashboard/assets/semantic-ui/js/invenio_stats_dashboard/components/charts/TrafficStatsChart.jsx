import React from 'react';
import PropTypes from 'prop-types';
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { StatsChart } from '../shared_components/StatsChart';
import { filterByDateRange } from '../../utils';
import { useStatsDashboard } from '../../context/StatsDashboardContext';

const TrafficStatsChart = ({ title = undefined, height = 300, ...otherProps }) => {
  const { stats, dateRange } = useStatsDashboard();

  // Transform the data into the format expected by StatsChart
  const transformedData = [
    {
      name: i18next.t('Unique Views'),
      data: filterByDateRange(stats.views, dateRange)?.map(point => [point.date, point.value]) || []
    },
    {
      name: i18next.t('Unique Downloads'),
      data: filterByDateRange(stats.downloads, dateRange)?.map(point => [point.date, point.value]) || []
    },
    {
      name: i18next.t('Downloaded Data'),
      data: filterByDateRange(stats.traffic, dateRange)?.map(point => [point.date, point.value]) || []
    }
  ];

  return (
    <StatsChart
      title={title}
      data={transformedData}
      height={height}
      {...otherProps}
    />
  );
}

TrafficStatsChart.propTypes = {
  title: PropTypes.string,
};

export { TrafficStatsChart };