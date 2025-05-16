import React from 'react';
import PropTypes from 'prop-types';
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { StatsChart } from '../shared_components/StatsChart';
import { useStatsDashboard } from '../../context/StatsDashboardContext';

const ContentStatsChart = ({ title = undefined }) => {
  const { stats } = useStatsDashboard();

  // Transform the data into the format expected by StatsChart
  const transformedData = [
    {
      name: i18next.t('Data Volume'),
      data: stats.dataVolume?.map(point => [point.date, point.value]) || []
    },
    {
      name: i18next.t('Uploaders'),
      data: stats.uploaders?.map(point => [point.date, point.value]) || []
    },
    {
      name: i18next.t('Records'),
      data: stats.recordCount?.map(point => [point.date, point.value]) || []
    }
  ];

  return (
    <StatsChart
      title={title}
      data={transformedData}
    />
  );
}

ContentStatsChart.propTypes = {
  title: PropTypes.string,
};

export { ContentStatsChart };