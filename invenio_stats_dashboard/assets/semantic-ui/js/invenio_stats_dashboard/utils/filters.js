/**
 * Filter data in an array of DataSeries objects by date range
 *
 * @typedef {Object} DataSeries
 * @property {string} id - Unique identifier for the series
 * @property {string} name - Series name (display name, can be label or id)
 * @property {DataPoint[]} data - Array of chart data points
 * @property {string} [type='line'] - Chart type ('line', 'bar', etc.)
 * @property {string} [valueType='number'] - Type of value ('number', 'filesize', etc.)
 *
 * @typedef {Object} DataPoint
 * @property {[Date, number]} value - [date, value] array for chart
 * @property {string} readableDate - Formatted date string
 * @property {string} valueType - Type of value ('number', 'filesize', etc.)
 *
 * @param {DataSeries[]} seriesArray - Array of DataSeries objects
 * @param {Object} dateRange - Date range object with start and end properties
 * @param {boolean} latestOnly - Whether to return only the latest data point for each series
 * @returns {DataSeries[]} Filtered series data in the expected format for aggregation
 */
const filterSeriesArrayByDate = (seriesArray, dateRange, latestOnly = false) => {
  if (!seriesArray || seriesArray.length === 0) {
    return [];
  }

  // If no date range is provided, we still need to handle latestOnly
  if (
    !dateRange ||
    (!dateRange.start && !dateRange.end) ||
    Object.keys(dateRange).length === 0
  ) {
    if (latestOnly) {
      // Return only the latest data point for each series
      return seriesArray.map((series) => {
        if (series.data.length === 0) {
          return { ...series, data: [] };
        }
        // Get the latest data point (last in the array)
        const latestData = series.data[series.data.length - 1];
        return {
          ...series,
          data: [latestData],
        };
      });
    } else {
      // Return all data
      return seriesArray;
    }
  }

  const endDayBeginning = dateRange.end
    ? new Date(dateRange.end).setHours(0, 0, 0, 0)
    : null;
  const endDayEnd = dateRange.end
    ? new Date(dateRange.end).setHours(23, 59, 59, 999)
    : new Date().setHours(23, 59, 59, 999); // Use end of current day if no end date
  const startDayBeginning = dateRange.start
    ? new Date(dateRange.start).setHours(0, 0, 0, 0)
    : null;

  const filteredSeriesArray = seriesArray.map((series) => {
    let filteredData;

    // Handle missing or invalid data property
    if (!series.data || !Array.isArray(series.data)) {
      return {
        ...series,
        data: [],
      };
    }

    if (latestOnly) {
      let latestData = null;
      let latestMs = null;

      // Traverse backwards for efficiency
      for (let i = series.data.length - 1; i >= 0; i--) {
        const current = series.data[i];

        // Skip invalid data points
        if (!current || !current.value || !Array.isArray(current.value) || current.value.length < 2) {
          continue;
        }

        // Skip if first element is not a valid Date
        if (!(current.value[0] instanceof Date) || isNaN(current.value[0].getTime())) {
          continue;
        }

        const dateMs = current.value[0].getTime();
        if (endDayBeginning && dateMs === endDayBeginning) {
          latestData = current;
          break;
        } else if (
          dateMs > latestMs &&
          dateMs <= endDayEnd &&
          dateMs >= startDayBeginning
        ) {
          latestData = current;
          latestMs = dateMs;
        }
      }
      filteredData = latestData ? [latestData] : [];
    } else {
      filteredData = series.data.filter((point) => {
        // Skip invalid data points
        if (!point || !point.value || !Array.isArray(point.value) || point.value.length < 2) {
          return false;
        }

        // Skip if first element is not a valid Date
        if (!(point.value[0] instanceof Date) || isNaN(point.value[0].getTime())) {
          return false;
        }

        const dateMs = point.value[0].getTime();
        return (
          (!dateRange.start || dateMs >= startDayBeginning) &&
          (!dateRange.end || dateMs <= endDayEnd)
        );
      });
    }

    return {
      ...series,
      data: filteredData,
    };
  });
  return filteredSeriesArray;
};

export { filterSeriesArrayByDate };
