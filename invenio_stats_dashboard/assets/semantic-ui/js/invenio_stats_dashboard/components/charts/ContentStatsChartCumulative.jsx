import React from 'react';
import PropTypes from 'prop-types';
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { StatsChart } from '../shared_components/StatsChart';
import { filterByDateRange } from '../../utils';
import { useStatsDashboard } from '../../context/StatsDashboardContext';

const ContentStatsChartCumulative = ({ title = undefined, height = 300, ...otherProps }) => {
  const { stats, dateRange } = useStatsDashboard();

  // Transform the data into the format expected by StatsChart
  const transformedData = [
    {
      name: i18next.t('Records'),
      data: filterByDateRange(stats.cumulativeRecordCount, dateRange).map(point => [point.date, point.value]),
      type: 'bar'
    },
    {
      name: i18next.t('Data Volume'),
      data: filterByDateRange(stats.cumulativeDataVolume, dateRange).map(point => [point.date, point.value]),
      type: 'bar'
    },
    {
      name: i18next.t('Uploaders'),
      data: filterByDateRange(stats.cumulativeUploaders, dateRange).map(point => [point.date, point.value]),
      type: 'bar'
    },
  ];

  return (
    <StatsChart
      title={title || i18next.t('Cumulative Growth')}
      data={transformedData}
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