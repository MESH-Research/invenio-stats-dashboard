import { filterSeriesArrayByDate } from './filters';

/**
 * Extract a value from record delta data
 *
 * @param {Object} stats - The transformed stats object
 * @param {string} recordBasis - Record basis ('added', 'created', 'published')
 * @param {string} metric - Metric name ('records', 'uploaders', 'dataVolume', etc.)
 * @param {string} category - Data category ('global', 'resourceTypes', etc.)
 * @param {Object} dateRange - Date range object
 * @returns {number} The total value across the date range
 */
export const extractRecordDeltaValue = (stats, recordBasis, metric, category = 'global', dateRange = null) => {
  if (!stats) {
    return 0;
  }

  let dataSource = null;

  switch (recordBasis) {
    case 'added':
      dataSource = stats.recordDeltaDataAdded?.[category]?.[metric];
      break;
    case 'created':
      dataSource = stats.recordDeltaDataCreated?.[category]?.[metric];
      break;
    case 'published':
      dataSource = stats.recordDeltaDataPublished?.[category]?.[metric];
      break;
    default:
      dataSource = stats.recordDeltaDataAdded?.[category]?.[metric];
  }

  if (!dataSource || !Array.isArray(dataSource)) {
    return 0;
  }

  const filteredData = filterSeriesArrayByDate(dataSource, dateRange);

  // Calculate total from filtered data
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
 * Extract a value from record snapshot data
 *
 * @param {Object} stats - The transformed stats object
 * @param {string} recordBasis - Record basis ('added', 'created', 'published')
 * @param {string} metric - Metric name ('records', 'uploaders', 'dataVolume', etc.)
 * @param {string} category - Data category ('global', 'resourceTypes', etc.)
 * @param {Object} dateRange - Date range object
 * @returns {number} The latest value within the date range
 */
export const extractRecordSnapshotValue = (stats, recordBasis, metric, category = 'global', dateRange = null) => {
  if (!stats) {
    return 0;
  }

  let dataSource = null;

  switch (recordBasis) {
    case 'added':
      dataSource = stats.recordSnapshotDataAdded?.[category]?.[metric];
      break;
    case 'created':
      dataSource = stats.recordSnapshotDataCreated?.[category]?.[metric];
      break;
    case 'published':
      dataSource = stats.recordSnapshotDataPublished?.[category]?.[metric];
      break;
    default:
      dataSource = stats.recordSnapshotDataAdded?.[category]?.[metric];
  }

  if (!dataSource || !Array.isArray(dataSource)) {
    return 0;
  }

  const filteredData = filterSeriesArrayByDate(dataSource, dateRange, true);

  // Get the latest value from filtered data
  // Since we filtered with latest=true, each series should have exactly one data point
  // For single stat components, we typically only have one series
  if (filteredData.length === 0) {
    return 0;
  }

  // The "global" category will have only one DataSeries
  const series = filteredData[0];
  if (!series.data || series.data.length === 0) {
    return 0;
  }

  // Each series has exactly one data point when filtered with latest=true
  const dataPoint = series.data[0];
  const value = dataPoint.value[1];

  return value;
};

/**
 * Extract a value from usage delta data
 *
 * @param {Object} stats - The transformed stats object
 * @param {string} metric - Metric name ('views', 'downloads', 'visitors', 'dataVolume')
 * @param {string} category - Data category ('global', 'byAccessRights', etc.)
 * @param {Object} dateRange - Date range object
 * @returns {number} The total value across the date range
 */
export const extractUsageDeltaValue = (stats, metric, category = 'global', dateRange = null) => {
  if (!stats) {
    return 0;
  }

  const dataSource = stats.usageDeltaData?.[category]?.[metric];

  if (!dataSource || !Array.isArray(dataSource)) {
    return 0;
  }

  const filteredData = filterSeriesArrayByDate(dataSource, dateRange);

  // Calculate total from filtered data
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
 * Extract a value from usage snapshot data
 *
 * @param {Object} stats - The transformed stats object
 * @param {string} metric - Metric name ('views', 'downloads', 'visitors', 'dataVolume')
 * @param {string} category - Data category ('global', 'byAccessRights', etc.)
 * @param {Object} dateRange - Date range object
 * @returns {number} The latest value within the date range
 */
export const extractUsageSnapshotValue = (stats, metric, category = 'global', dateRange = null) => {
  if (!stats) {
    return 0;
  }

  const dataSource = stats.usageSnapshotData?.[category]?.[metric];

  if (!dataSource || !Array.isArray(dataSource)) {
    return 0;
  }

  const filteredData = filterSeriesArrayByDate(dataSource, dateRange, true);

  // Get the latest value from filtered data
  // Since we filtered with latest=true, each series should have exactly one data point
  // For single stat components, we typically only have one series
  if (filteredData.length === 0) {
    return 0;
  }

  // The "global" category will have only one DataSeries
  const series = filteredData[0];
  if (!series.data || series.data.length === 0) {
    return 0;
  }

  // Each series has exactly one data point when filtered with latest=true
  const dataPoint = series.data[0];
  const value = dataPoint.value[1];

  return value;
};