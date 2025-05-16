import React from 'react';
import PropTypes from 'prop-types';
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { StatsChart } from '../shared_components/StatsChart';
import { useStatsDashboard } from '../../context/StatsDashboardContext';

const TrafficStatsChart = ({ title = undefined }) => {
  const { stats } = useStatsDashboard();

  // Transform the data into the format expected by StatsChart
  const transformedData = [
    {
      name: i18next.t('Views'),
      data: stats.views?.map(point => [point.date, point.value]) || []
    },
    {
      name: i18next.t('Downloads'),
      data: stats.downloads?.map(point => [point.date, point.value]) || []
    },
    {
      name: i18next.t('Traffic'),
      data: stats.traffic?.map(point => [point.date, point.value]) || []
    }
  ];

  return (
    <StatsChart
      title={title}
      data={transformedData}
    />
  );
}

TrafficStatsChart.propTypes = {
  title: PropTypes.string,
};

export { TrafficStatsChart };