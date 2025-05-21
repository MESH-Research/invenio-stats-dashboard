/**
 * Filter data points by date range
 * @param {Array} data - Array of data points with date property
 * @param {Object} dateRange - Object containing start and end dates
 * @returns {Array} Filtered data points
 */
export const filterByDateRange = (data, dateRange) => {
  if (!data || !dateRange || !dateRange.start || !dateRange.end) {
    return data;
  }

  const startDate = new Date(dateRange.start);
  const endDate = new Date(dateRange.end);

  return data.filter(point => {
    const pointDate = new Date(point.date);
    return pointDate >= startDate && pointDate <= endDate;
  });
};