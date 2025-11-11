// Part of the Invenio-Stats-Dashboard extension for InvenioRDM
// Copyright (C) 2025 Mesh Research
//
// Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
// it under the terms of the MIT License; see LICENSE file for more details.

import { createUTCDate, reconstructDateFromMMDD } from "./dates";

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

  // Use UTC methods to avoid timezone issues
  const endDayBeginning = dateRange.end
    ? new Date(Date.UTC(
        dateRange.end.getUTCFullYear(),
        dateRange.end.getUTCMonth(),
        dateRange.end.getUTCDate(),
        0, 0, 0, 0
      )).getTime()
    : null;
  const endDayEnd = dateRange.end
    ? new Date(Date.UTC(
        dateRange.end.getUTCFullYear(),
        dateRange.end.getUTCMonth(),
        dateRange.end.getUTCDate(),
        23, 59, 59, 999
      )).getTime()
    : new Date(Date.UTC(
        new Date().getUTCFullYear(),
        new Date().getUTCMonth(),
        new Date().getUTCDate(),
        23, 59, 59, 999
      )).getTime(); // Use end of current day if no end date
  const startDayBeginning = dateRange.start
    ? new Date(Date.UTC(
        dateRange.start.getUTCFullYear(),
        dateRange.start.getUTCMonth(),
        dateRange.start.getUTCDate(),
        0, 0, 0, 0
      )).getTime()
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
        if (!current || !Array.isArray(current) || current.length < 2) continue;
        if (!current[0]) continue;
        // Convert first element to Date if it's a string, or skip if invalid
        let dateObj;
        if (current[0] instanceof Date) {
          dateObj = current[0];
        } else if (typeof current[0] === 'string') {
          // Handle YYYY-MM-DD or MM-DD format date strings
          // If series has a year property, reconstruct full date from MM-DD
          const dateString = series.year
            ? reconstructDateFromMMDD(current[0], series.year)
            : current[0];
          dateObj = createUTCDate(dateString);
        } else {
          continue;
        }

        if (isNaN(dateObj.getTime())) {
          continue;
        }

        const dateMs = dateObj.getTime();
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
        if (!point || !Array.isArray(point) || point.length < 2) return false;
        const [date] = point;
        if (!date) return false;

        // Convert first element to Date if it's a string, or skip if invalid
        let dateObj;
        if (date instanceof Date) {
          dateObj = date;
        } else if (typeof date === 'string') {
          // Handle YYYY-MM-DD or MM-DD format date strings
          // If series has a year property, reconstruct full date from MM-DD
          const dateString = series.year
            ? reconstructDateFromMMDD(date, series.year)
            : date;
          dateObj = createUTCDate(dateString);
        } else {
          return false;
        }

        if (isNaN(dateObj.getTime())) {
          return false;
        }

        const dateMs = dateObj.getTime();
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
