import React from 'react';
import PropTypes from 'prop-types';
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { StatsChart } from '../shared_components/StatsChart';
import { filterByDateRange } from '../../utils';
import { useStatsDashboard } from '../../context/StatsDashboardContext';

const TrafficStatsChartCumulative = ({ title = undefined, height = 300, ...otherProps }) => {
  const { stats, dateRange } = useStatsDashboard();

  // Helper function to extract data from the new usage snapshot structure
  const extractDataFromUsageSnapshot = (usageSnapshotData, metric) => {
    if (!usageSnapshotData || !usageSnapshotData.global || !usageSnapshotData.global[metric]) {
      return [];
    }

    // Handle both single data point and array of data points
    if (Array.isArray(usageSnapshotData.global[metric])) {
      // Single data point format: [date, value]
      const [date, value] = usageSnapshotData.global[metric];
      return [{
        date: date,
        value: value,
        resourceTypes: [],
        subjectHeadings: [],
      }];
    } else if (Array.isArray(usageSnapshotData.global[metric][0])) {
      // Array of data points format: [[date, value], [date, value], ...]
      return usageSnapshotData.global[metric].map(([date, value]) => ({
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
      data: filterByDateRange(extractDataFromUsageSnapshot(stats.usageSnapshotData, 'views'), dateRange)?.map(point => [point.date, point.value, point.resourceTypes, point.subjectHeadings]) || [],
      type: 'bar'
    },
    {
      name: i18next.t('Unique Downloads'),
      data: filterByDateRange(extractDataFromUsageSnapshot(stats.usageSnapshotData, 'downloads'), dateRange)?.map(point => [point.date, point.value, point.resourceTypes, point.subjectHeadings]) || [],
      type: 'bar'
    },
    {
      name: i18next.t('Downloaded Data'),
      data: filterByDateRange(extractDataFromUsageSnapshot(stats.usageSnapshotData, 'dataVolume'), dateRange)?.map(point => [point.date, point.value, point.resourceTypes, point.subjectHeadings]) || [],
      type: 'bar',
      valueType: 'filesize'
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