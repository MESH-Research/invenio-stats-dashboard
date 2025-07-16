import React from 'react';
import PropTypes from 'prop-types';
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { StatsChart } from '../shared_components/StatsChart';
import { filterByDateRange } from '../../utils';
import { useStatsDashboard } from '../../context/StatsDashboardContext';

const TrafficStatsChart = ({ title = undefined, height = 300, ...otherProps }) => {
  const { stats, dateRange } = useStatsDashboard();

  // Helper function to extract data from the new usage delta structure
  const extractDataFromUsageDelta = (usageDeltaData, metric) => {
    if (!usageDeltaData || !usageDeltaData.global || !usageDeltaData.global[metric]) {
      return [];
    }

    // Handle both single data point and array of data points
    if (Array.isArray(usageDeltaData.global[metric])) {
      // Single data point format: [date, value]
      const [date, value] = usageDeltaData.global[metric];
      return [{
        date: date,
        value: value,
        resourceTypes: [],
        subjectHeadings: [],
      }];
    } else if (Array.isArray(usageDeltaData.global[metric][0])) {
      // Array of data points format: [[date, value], [date, value], ...]
      return usageDeltaData.global[metric].map(([date, value]) => ({
        date: date,
        value: value,
        resourceTypes: [],
        subjectHeadings: [],
      }));
    }

    return [];
  };

  // Transform the data into the format expected by StatsChart
  const transformedData = [
    {
      name: i18next.t('Unique Views'),
      data: filterByDateRange(extractDataFromUsageDelta(stats.usageDeltaData, 'views'), dateRange)?.map(point => [point.date, point.value, point.resourceTypes, point.subjectHeadings]) || []
    },
    {
      name: i18next.t('Unique Downloads'),
      data: filterByDateRange(extractDataFromUsageDelta(stats.usageDeltaData, 'downloads'), dateRange)?.map(point => [point.date, point.value, point.resourceTypes, point.subjectHeadings]) || []
    },
    {
      name: i18next.t('Downloaded Data'),
      data: filterByDateRange(extractDataFromUsageDelta(stats.usageDeltaData, 'dataVolume'), dateRange)?.map(point => [point.date, point.value, point.resourceTypes, point.subjectHeadings]) || [],
      valueType: 'filesize'
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