import React from 'react';
import PropTypes from 'prop-types';
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { StatsChart } from '../shared_components/StatsChart';
import { filterByDateRange } from '../../utils';
import { useStatsDashboard } from '../../context/StatsDashboardContext';

const ContentStatsChartCumulative = ({ title = undefined, height = 300, ...otherProps }) => {
  const { stats, dateRange } = useStatsDashboard();

  // Helper function to extract data from the new snapshot structure
  const extractDataFromSnapshot = (snapshotData, metric) => {
    if (!snapshotData || !snapshotData.global || !snapshotData.global[metric]) {
      return [];
    }

    // Handle both single data point and array of data points
    if (Array.isArray(snapshotData.global[metric])) {
      // Single data point format: [date, value]
      const [date, value] = snapshotData.global[metric];
      return [{
        date: date,
        value: value,
        resourceTypes: [],
        subjectHeadings: [],
      }];
    } else if (Array.isArray(snapshotData.global[metric][0])) {
      // Array of data points format: [[date, value], [date, value], ...]
      return snapshotData.global[metric].map(([date, value]) => ({
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
      name: i18next.t('Records'),
      data: filterByDateRange(extractDataFromSnapshot(stats.recordSnapshotDataAdded, 'records'), dateRange).map(point => [point.date, point.value, point.resourceTypes, point.subjectHeadings]),
      type: 'bar'
    },
    {
      name: i18next.t('Data Volume'),
      data: filterByDateRange(extractDataFromSnapshot(stats.recordSnapshotDataAdded, 'dataVolume'), dateRange).map(point => [point.date, point.value, point.resourceTypes, point.subjectHeadings]),
      type: 'bar',
      valueType: 'filesize'
    },
    {
      name: i18next.t('Uploaders'),
      data: filterByDateRange(extractDataFromSnapshot(stats.recordSnapshotDataAdded, 'uploaders'), dateRange).map(point => [point.date, point.value, point.resourceTypes, point.subjectHeadings]),
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