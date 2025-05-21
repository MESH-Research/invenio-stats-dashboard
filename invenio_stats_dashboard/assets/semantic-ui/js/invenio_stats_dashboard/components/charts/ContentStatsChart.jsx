import React from 'react';
import PropTypes from 'prop-types';
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { StatsChart } from '../shared_components/StatsChart';
import { filterByDateRange } from '../../utils';
import { useStatsDashboard } from '../../context/StatsDashboardContext';

const ContentStatsChart = ({ title = undefined, height = 300, ...otherProps }) => {
  const { stats, dateRange } = useStatsDashboard();

  // Transform the data into the format expected by StatsChart
  const transformedData = [
    {
      name: i18next.t('New Data Volume'),
      data: filterByDateRange(stats.dataVolume, dateRange)?.map(point => [point.date, point.value]) || []
    },
    {
      name: i18next.t('Active Uploaders'),
      data: filterByDateRange(stats.uploaders, dateRange)?.map(point => [point.date, point.value]) || []
    },
    {
      name: i18next.t('New Records'),
      data: filterByDateRange(stats.recordCount, dateRange)?.map(point => [point.date, point.value]) || []
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

ContentStatsChart.propTypes = {
  title: PropTypes.string,
};

export { ContentStatsChart };