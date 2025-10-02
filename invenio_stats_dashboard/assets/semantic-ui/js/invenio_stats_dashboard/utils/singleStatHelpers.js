// Part of the Invenio-Stats-Dashboard extension for InvenioRDM
// Copyright (C) 2025 Mesh Research
//
// Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
// it under the terms of the MIT License; see LICENSE file for more details.

import { filterSeriesArrayByDate } from './filters';

/**
 * Common helper for delta value extraction
 * Filters relevant yearly stats, flattens series, and calculates total
 *
 * @param {Array} stats - Array of yearly stats objects
 * @param {Function} getDataSource - Function to extract data source from yearly stats
 * @param {Object} dateRange - Date range object
 * @returns {number} The total value across the date range
 */
const extractDeltaValue = (stats, getDataSource, dateRange) => {
  if (!stats || !Array.isArray(stats)) {
    return 0;
  }

  const relevantYearlyStats = stats.filter(yearlyStats => {
    if (!yearlyStats || !yearlyStats.year) return false;

    if (dateRange) {
      const rangeStartYear = new Date(dateRange.start).getFullYear();
      const rangeEndYear = new Date(dateRange.end).getFullYear();

      return yearlyStats.year >= rangeStartYear && yearlyStats.year <= rangeEndYear;
    }

    return true; // If no date range, include all years
  });

  if (relevantYearlyStats.length === 0) {
    return 0;
  }

  const allSeries = relevantYearlyStats.flatMap(yearlyStats =>
    getDataSource(yearlyStats) || []
  );

  if (allSeries.length === 0) {
    return 0;
  }

  const filteredData = filterSeriesArrayByDate(allSeries, dateRange);

  return filteredData.reduce((total, series) => {
    if (!series.data || !Array.isArray(series.data)) {
      return total;
    }

    const seriesTotal = series.data.reduce((seriesSum, dataPoint) => {
      if (dataPoint && dataPoint.value && Array.isArray(dataPoint.value) && dataPoint.value.length >= 2) {
        return seriesSum + dataPoint.value[1];
      }
      return seriesSum;
    }, 0);

    return total + seriesTotal;
  }, 0);
};

/**
 * Common helper for snapshot value extraction
 * Sorts yearly stats by year and gets the latest value from the most recent year
 *
 * @param {Array} stats - Array of yearly stats objects
 * @param {Function} getDataSource - Function to extract data source from yearly stats
 * @param {Object} dateRange - Date range object
 * @returns {number} The latest value within the date range
 */
const extractSnapshotValue = (stats, getDataSource, dateRange) => {
  if (!stats || !Array.isArray(stats)) {
    return 0;
  }

  const sortedStats = stats
    .filter(yearlyStats => yearlyStats && yearlyStats.year)
    .sort((a, b) => b.year - a.year);

  if (sortedStats.length === 0) {
    return 0;
  }

  const mostRecentYearStats = sortedStats[0];
  const dataSource = getDataSource(mostRecentYearStats);

  if (!dataSource || !Array.isArray(dataSource)) {
    return 0;
  }

  // Each series has exactly one data point when filtered with latest=true
  const filteredData = filterSeriesArrayByDate(dataSource, dateRange, true);

  if (filteredData.length === 0) {
    return 0;
  }

  // The "global" category will have only one DataSeries
  const series = filteredData[0];
  if (!series.data || series.data.length === 0) {
    return 0;
  }

  const dataPoint = series.data[0];
  const value = dataPoint.value[1];

  return value;
};

/**
 * Helper function to get record data source based on record basis
 *
 * @param {Object} yearlyStats - Yearly stats object
 * @param {string} recordBasis - Record basis ('added', 'created', 'published')
 * @param {string} metric - Metric name ('records', 'uploaders', 'dataVolume', etc.)
 * @param {string} category - Data category ('global', 'resourceTypes', etc.)
 * @param {string} dataType - Data type ('Delta' or 'Snapshot')
 * @returns {Array|null} The data source array or null
 */
const getRecordDataSource = (yearlyStats, recordBasis, metric, category, dataType) => {
  const dataTypeKey = `record${dataType}Data`;

  switch (recordBasis) {
    case 'added':
      return yearlyStats[`${dataTypeKey}Added`]?.[category]?.[metric];
    case 'created':
      return yearlyStats[`${dataTypeKey}Created`]?.[category]?.[metric];
    case 'published':
      return yearlyStats[`${dataTypeKey}Published`]?.[category]?.[metric];
    default:
      return yearlyStats[`${dataTypeKey}Added`]?.[category]?.[metric];
  }
};

/**
 * Extract the total record delta value for a period and metric
 *
 * @param {Array} stats - Array of yearly stats objects
 * @param {string} recordBasis - Record basis ('added', 'created', 'published')
 * @param {string} metric - Metric name ('records', 'uploaders', 'dataVolume', etc.)
 * @param {string} category - Data category ('global', 'resourceTypes', etc.)
 * @param {Object} dateRange - Date range object
 * @returns {number} The total value across the date range
 */
export const extractRecordDeltaValue = (stats, recordBasis, metric, category = 'global', dateRange = null) => {
  const getDataSource = (yearlyStats) => {
    return getRecordDataSource(yearlyStats, recordBasis, metric, category, 'Delta');
  };

  return extractDeltaValue(stats, getDataSource, dateRange);
};

/**
 * Extract the final record snapshot value for a period and metric
 *
 * @param {Array} stats - Array of yearly stats objects
 * @param {string} recordBasis - Record basis ('added', 'created', 'published')
 * @param {string} metric - Metric name ('records', 'uploaders', 'dataVolume', etc.)
 * @param {string} category - Data category ('global', 'resourceTypes', etc.)
 * @param {Object} dateRange - Date range object
 * @returns {number} The latest value within the date range
 */
export const extractRecordSnapshotValue = (stats, recordBasis, metric, category = 'global', dateRange = null) => {
  const getDataSource = (yearlyStats) => {
    return getRecordDataSource(yearlyStats, recordBasis, metric, category, 'Snapshot');
  };

  return extractSnapshotValue(stats, getDataSource, dateRange);
};

/**
 * Extract the total usage delta value for a period and metric
 *
 * @param {Array} stats - Array of yearly stats objects
 * @param {string} metric - Metric name ('views', 'downloads', 'visitors', 'dataVolume')
 * @param {string} category - Data category ('global', 'accessStatuses', etc.)
 * @param {Object} dateRange - Date range object
 * @returns {number} The total value across the date range
 */
export const extractUsageDeltaValue = (stats, metric, category = 'global', dateRange = null) => {
  const getDataSource = (yearlyStats) => {
    return yearlyStats.usageDeltaData?.[category]?.[metric];
  };

  return extractDeltaValue(stats, getDataSource, dateRange);
};

/**
 * Extract the final usage snapshot value for a period and metric
 *
 * @param {Array} stats - Array of yearly stats objects
 * @param {string} metric - Metric name ('views', 'downloads', 'visitors', 'dataVolume')
 * @param {string} category - Data category ('global', 'accessStatuses', etc.)
 * @param {Object} dateRange - Date range object
 * @returns {number} The latest value within the date range
 */
export const extractUsageSnapshotValue = (stats, metric, category = 'global', dateRange = null) => {
  const getDataSource = (yearlyStats) => {
    return yearlyStats.usageSnapshotData?.[category]?.[metric];
  };

  return extractSnapshotValue(stats, getDataSource, dateRange);
};