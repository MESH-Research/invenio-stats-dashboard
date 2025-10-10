// Part of the Invenio-Stats-Dashboard extension for InvenioRDM
// Copyright (C) 2025 Mesh Research
//
// Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
// it under the terms of the MIT License; see LICENSE file for more details.

import { i18next } from "@translations/invenio_stats_dashboard/i18next";

/**
 * Create a Date object with proper UTC handling for date strings
 * @param {string|Date} date - The date to parse (string or Date object)
 * @returns {Date} Date object with proper UTC handling
 */
const createUTCDate = (date) => {
  if (date instanceof Date) {
    return date;
  } else if (typeof date === "string") {
    // If the string doesn't have time components, assume UTC midnight
    if (!date.includes("T") && !date.includes(":")) {
      // Parse YYYY-MM-DD or YYYY-MM format and create UTC date
      const parts = date.split("-");
      if (parts.length === 3) {
        const year = parseInt(parts[0], 10);
        const month = parseInt(parts[1], 10);
        const day = parseInt(parts[2], 10);
        return new Date(Date.UTC(year, month - 1, day));
      } else if (parts.length === 2) {
        const year = parseInt(parts[0], 10);
        const month = parseInt(parts[1], 10);
        // For YYYY-MM format, use the first day of the month
        return new Date(Date.UTC(year, month - 1, 1));
      } else if (parts.length === 1) {
        const year = parseInt(parts[0], 10);
        // For YYYY format, use January 1st of the year
        return new Date(Date.UTC(year, 0, 1));
      }
      return new Date(date + "T00:00:00.000Z");
    } else {
      return new Date(date);
    }
  } else {
    return new Date(date);
  }
};

/**
 * Create a UTC date from year, month, day components
 * @param {number} year - The year
 * @param {number} month - The month (1-12)
 * @param {number} day - The day (1-31)
 * @returns {Date} UTC Date object
 */
const createUTCDateFromParts = (year, month, day) => {
  return new Date(Date.UTC(year, month - 1, day)); // month is 0-indexed in Date constructor
};

/**
 * Get current UTC date (midnight UTC)
 * @returns {Date} Current UTC date
 */
const getCurrentUTCDate = () => {
  const today = new Date().toISOString().split("T")[0]; // Get YYYY-MM-DD
  return new Date(today + "T00:00:00.000Z");
};

/**
 * Add days to a date
 * @param {Date} date - The date to add days to
 * @param {number} days - Number of days to add (can be negative)
 * @returns {Date} New date with days added
 */
const addDays = (date, days) => {
  const result = new Date(date);
  result.setUTCDate(result.getUTCDate() + days);
  return result;
};

/**
 * Add months to a date
 * @param {Date} date - The date to add months to
 * @param {number} months - Number of months to add (can be negative)
 * @returns {Date} New date with months added
 */
const addMonths = (date, months) => {
  const result = new Date(date);
  result.setUTCMonth(result.getUTCMonth() + months);
  return result;
};

/**
 * Add years to a date
 * @param {Date} date - The date to add years to
 * @param {number} years - Number of years to add (can be negative)
 * @returns {Date} New date with years added
 */
const addYears = (date, years) => {
  const result = new Date(date);
  result.setUTCFullYear(result.getUTCFullYear() + years);
  return result;
};

/**
 * Set specific date parts on a date
 * @param {Date} date - The date to modify
 * @param {Object} parts - Object with year, month, day properties
 * @returns {Date} New date with specified parts set
 */
const setDateParts = (date, { year, month, day }) => {
  const result = new Date(date);
  if (year !== undefined) result.setUTCFullYear(year);
  if (month !== undefined) result.setUTCMonth(month - 1); // month is 0-indexed
  if (day !== undefined) result.setUTCDate(day);
  return result;
};

/**
 * Get the locale-appropriate date range separator using Intl.DateTimeFormat
 * @param {string} locale - The locale to use (e.g., 'en', 'fr', 'ja')
 * @returns {string} The locale-appropriate range separator
 */
const getLocaleDateSeparator = (locale) => {
  const yearFormatter = new Intl.DateTimeFormat(locale, { year: "numeric" });
  const startDate = new Date("2024-01-01");
  const endDate = new Date("2025-01-01");
  const yearRange = yearFormatter.formatRange(startDate, endDate);
  const startYear = yearFormatter.format(startDate);
  const endYear = yearFormatter.format(endDate);

  // Extract the separator by removing the start and end years from the range
  return yearRange.slice(startYear.length, -endYear.length);
};

/**
 * Format a quarter string or date into a localized quarter format
 * @param {string|Date} quarterInput - Quarter string (e.g., "2024-Q1") or Date object
 * @returns {string} Formatted quarter string (e.g., "Q1 2024")
 */
const formatQuarter = (quarterInput) => {
  let year, quarter;

  if (typeof quarterInput === "string" && quarterInput.includes("Q")) {
    // Handle quarter string format (e.g., "2024-Q1")
    [year, quarter] = quarterInput.split("-Q");
  } else if (quarterInput instanceof Date) {
    // Handle Date object - calculate quarter from month
    year = quarterInput.getUTCFullYear();
    quarter = Math.floor(quarterInput.getUTCMonth() / 3) + 1;
  } else {
    return "";
  }

  return `${i18next.t("Q")}${quarter} ${year}`;
};

/**
 * Create a human-readable date string at a given granularity for a given date
 *
 * For example, if the date is 2024-01-01 the following granularities will give the following results:
 * - 'month': "January 2024"
 * - 'year': "2024"
 * - 'quarter': "Q1 2024"
 * - 'week': "Jan 1 - 7, 2024"
 * - 'day': "January 1, 2024"
 *
 * @param {string|Date} date - The date to format (date string or Date object)
 * @param {string} granularity - The time granularity (day, week, month, quarter, year)
 * @returns {string} Human-readable date string
 */
const readableGranularDate = (date, granularity) => {
  const dateObj = date instanceof Date ? date : createUTCDate(date);

  switch (granularity) {
    case "quarter":
      return formatDate(dateObj, "quarter");

    case "week":
      // Find the Monday of the week containing the provided date
      const dayOfWeek = dateObj.getUTCDay();
      let monday;
      if (dayOfWeek !== 1) {
        // 1 = Monday
        const daysFromMonday = dayOfWeek === 0 ? 6 : dayOfWeek - 1; // Sunday = 0, so it's 6 days from Monday
        monday = new Date(
          Date.UTC(
            dateObj.getUTCFullYear(),
            dateObj.getUTCMonth(),
            dateObj.getUTCDate() - daysFromMonday,
          ),
        );
      } else {
        monday = dateObj;
      }

      const sunday = new Date(
        Date.UTC(
          monday.getUTCFullYear(),
          monday.getUTCMonth(),
          monday.getUTCDate() + 6,
        ),
      );
      return formatDateRange({ start: monday, end: sunday }, "day", true);

    case "month":
      return formatDate(dateObj, "month");

    case "year":
      return formatDate(dateObj, "year");

    default:
      return formatDate(dateObj, "day", true);
  }
};

/**
 * Format a date string or Date object into a localized, human-readable format
 * @param {string|Date} date - The date to format (string or Date object)
 * @param {string} granularity - The granularity to format ('day', 'month', 'year') or undefined for full date
 * @param {boolean} useShortMonth - Whether to use short month names (default: false)
 * @param {string|Date} endDate - The end date for a range. If present, the date is formatted as a range.
 * @returns {string} The formatted date string
 */
const formatDate = (
  date,
  granularity = "day",
  useShortMonth = false,
  endDate = null,
) => {
  if (!date) {
    return "";
  }

  // Handle quarter strings that can't be converted to a Date object
  if (typeof date === "string" && date.includes("Q")) {
    return formatQuarter(date);
  }

  // If we have an endDate, delegate to formatDateRange
  if (endDate) {
    return formatDateRange(
      { start: date, end: endDate },
      granularity,
      useShortMonth,
    );
  }

  const dateObj = createUTCDate(date);

  switch (granularity) {
    case "year":
      return new Intl.DateTimeFormat(i18next.language, {
        year: "numeric",
        timeZone: "UTC",
      }).format(dateObj);

    case "quarter":
      return formatQuarter(dateObj);

    case "month":
      return new Intl.DateTimeFormat(i18next.language, {
        year: "numeric",
        month: useShortMonth ? "short" : "long",
        timeZone: "UTC",
      }).format(dateObj);

    case "day":
    default:
      const dateStyle = useShortMonth ? "medium" : "long";
      return new Intl.DateTimeFormat(i18next.language, {
        dateStyle: dateStyle,
        timeZone: "UTC",
      }).format(dateObj);
  }
};

const formatDateRange = (
  dateRange,
  granularity = "day",
  useShortMonth = false,
) => {
  if (!dateRange || !dateRange.start || !dateRange.end) {
    return "";
  }

  // Convert date strings to Date objects
  const startDate = createUTCDate(dateRange.start);
  const endDate = createUTCDate(dateRange.end);

  switch (granularity) {
    case "year":
      return new Intl.DateTimeFormat(i18next.language, {
        year: "numeric",
        timeZone: "UTC",
      }).formatRange(startDate, endDate);

    case "month":
      return new Intl.DateTimeFormat(i18next.language, {
        year: "numeric",
        month: useShortMonth ? "short" : "long",
        timeZone: "UTC",
      }).formatRange(startDate, endDate);

    case "quarter":
      // Use built-in Intl to get locale-appropriate separator
      const separator = getLocaleDateSeparator(i18next.language);

      const startQuarter = formatQuarter(startDate);
      const endQuarter = formatQuarter(endDate);

      return startQuarter + separator + endQuarter;

    case "day":
    default:
      const dateStyle = useShortMonth ? "medium" : "long";
      return new Intl.DateTimeFormat(i18next.language, {
        dateStyle: dateStyle,
        timeZone: "UTC",
      }).formatRange(startDate, endDate);
  }
};

/**
 * Format a timestamp as a concise relative date
 * - Same day: "9:56 AM" (time only)
 * - Same week: "Mon 9:56 AM" (day + time)
 * - Same year: "Jan 5, 9:56 AM" (month + day + time)
 * - Different year: "Jan 5, 2024, 9:56 AM" (full date + time)
 * @param {number} timestamp - Timestamp in milliseconds
 * @returns {string} Concise relative date string
 */
const formatRelativeTimestamp = (timestamp) => {
  if (!timestamp) {
    return "Unknown";
  }

  const date = new Date(timestamp);
  const now = new Date();

  // Get UTC dates for comparison
  const dateUTC = new Date(date.getTime() + date.getTimezoneOffset() * 60000);
  const nowUTC = new Date(now.getTime() + now.getTimezoneOffset() * 60000);

  // Check if same day
  const isSameDay =
    dateUTC.getUTCDate() === nowUTC.getUTCDate() &&
    dateUTC.getUTCMonth() === nowUTC.getUTCMonth() &&
    dateUTC.getUTCFullYear() === nowUTC.getUTCFullYear();

  // Check if same week (Monday to Sunday)
  const getWeekStart = (d) => {
    const day = d.getUTCDay();
    const diff = d.getUTCDate() - day + (day === 0 ? -6 : 1); // Adjust when day is Sunday
    return new Date(d.setUTCDate(diff));
  };

  const dateWeekStart = getWeekStart(new Date(dateUTC));
  const nowWeekStart = getWeekStart(new Date(nowUTC));
  const isSameWeek = dateWeekStart.getTime() === nowWeekStart.getTime();

  // Check if same year
  const isSameYear = dateUTC.getUTCFullYear() === nowUTC.getUTCFullYear();

  if (isSameDay) {
    // Same day: show time only
    return new Intl.DateTimeFormat(i18next.language, {
      hour: "numeric",
      minute: "2-digit",
      hour12: true,
      timeZone: "UTC",
    }).format(date);
  } else if (isSameWeek) {
    // Same week: show day + time
    return new Intl.DateTimeFormat(i18next.language, {
      weekday: "short",
      hour: "numeric",
      minute: "2-digit",
      hour12: true,
      timeZone: "UTC",
    }).format(date);
  } else if (isSameYear) {
    // Same year: show month + day + time
    return new Intl.DateTimeFormat(i18next.language, {
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
      hour12: true,
      timeZone: "UTC",
    }).format(date);
  } else {
    // Different year: show full date + time
    return new Intl.DateTimeFormat(i18next.language, {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
      hour12: true,
      timeZone: "UTC",
    }).format(date);
  }
};

// Exports
export {
  createUTCDate,
  createUTCDateFromParts,
  getCurrentUTCDate,
  addDays,
  addMonths,
  addYears,
  setDateParts,
  readableGranularDate,
  formatDate,
  formatDateRange,
  formatRelativeTimestamp,
};
