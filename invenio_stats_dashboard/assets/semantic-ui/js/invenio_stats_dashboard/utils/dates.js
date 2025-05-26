import { i18next } from "@translations/invenio_stats_dashboard/i18next";

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

/**
 * Format a date string or Date object into a localized, human-readable format
 * @param {string|Date} date - The date to format (string or Date object)
 * @param {boolean} useShortMonth - Whether to use short month names (default: false)
 * @param {boolean} isStartDate - Whether this is the start date in a range (default: false)
 * @param {string|Date} endDate - The end date to compare with (required if isStartDate is true)
 * @returns {string} The formatted date string
 */
export const formatDate = (date, useShortMonth = false, isStartDate = false, endDate = null) => {
  // If date is null or undefined, return empty string
  if (!date) {
    return '';
  }

  // If date is already a Date object, use it directly
  let dateObj = date instanceof Date ? date : new Date(date);

  // Handle quarter format (only for string inputs)
  if (typeof date === 'string' && date.includes('Q')) {
    const [year, quarter] = date.split('-Q');
    return `${i18next.t('Q')}${quarter} ${year}`;
  }

  // Handle month format (only for string inputs)
  if (typeof date === 'string' && date.match(/^\d{4}-\d{2}$/)) {
    const [year, month] = date.split('-');
    return new Intl.DateTimeFormat(i18next.language, {
      year: 'numeric',
      month: useShortMonth ? 'short' : 'long'
    }).format(new Date(year, parseInt(month) - 1));
  }

  // Handle year format (only for string inputs)
  if (typeof date === 'string' && date.match(/^\d{4}$/)) {
    return date;
  }

  // For start dates in a range, check if we need to show the year
  if (isStartDate && endDate) {
    const endDateObj = endDate instanceof Date ? endDate : new Date(endDate);
    if (dateObj.getFullYear() === endDateObj.getFullYear()) {
      // If years are the same, only show month and day
      return new Intl.DateTimeFormat(i18next.language, {
        month: useShortMonth ? 'short' : 'long',
        day: 'numeric'
      }).format(dateObj);
    }
  }

  // Handle day format (for both string and Date objects)
  return new Intl.DateTimeFormat(i18next.language, {
    year: 'numeric',
    month: useShortMonth ? 'short' : 'long',
    day: 'numeric'
  }).format(dateObj);
};

export const formatDateRange = (dateRange, useShortMonth = false) => {
  if (!dateRange || !dateRange.start || !dateRange.end) {
    return '';
  }

  return `${formatDate(dateRange.start, useShortMonth, true)} - ${formatDate(dateRange.end, useShortMonth, false)}`;
};