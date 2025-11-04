// Part of the Invenio-Stats-Dashboard extension for InvenioRDM
// Copyright (C) 2025 Mesh Research
//
// Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
// it under the terms of the MIT License; see LICENSE file for more details.

/**
 * Get available breakdown options from yearly data blocks.
 * Filters out empty subcounts and only includes breakdowns from yearly blocks
 * that overlap with the selected date range.
 *
 * @param {Array} data - Array of yearly data objects, each containing global and breakdown metrics
 * @param {Object|null} dateRange - Date range object with start and end properties, or null for all blocks
 * @returns {Array} Array of breakdown keys (e.g., ['resourceTypes', 'subjects', ...])
 */
export const getAvailableBreakdowns = (data, dateRange = null) => {
  if (!data || !Array.isArray(data) || data.length === 0) {
    return [];
  }

  // Filter yearly blocks to only those that overlap with the date range
  const relevantYearlyBlocks = dateRange
    ? data.filter((yearlyData) => {
        // If yearlyData has a year property, use it
        if (yearlyData?.year) {
          const rangeStartYear = new Date(dateRange.start).getUTCFullYear();
          const rangeEndYear = dateRange.end
            ? new Date(dateRange.end).getUTCFullYear()
            : new Date().getUTCFullYear();
          return (
            yearlyData.year >= rangeStartYear &&
            yearlyData.year <= rangeEndYear
          );
        }
        // Fallback: if no year property, include all blocks
        // (This shouldn't happen with proper data structure)
        return true;
      })
    : data;

  // Collect unique breakdown keys that have non-empty data in relevant yearly blocks
  const validKeys = new Set();
  relevantYearlyBlocks.forEach((yearlyData) => {
    if (yearlyData && typeof yearlyData === "object") {
      Object.keys(yearlyData).forEach((key) => {
        if (key !== "global" && !validKeys.has(key)) {
          const subcount = yearlyData[key];
          if (
            subcount &&
            typeof subcount === "object" &&
            Object.values(subcount).some(
              (arr) =>
                Array.isArray(arr) &&
                arr.some((series) => series?.data?.length > 0)
            )
          ) {
            validKeys.add(key);
          }
        }
      });
    }
  });

  return Array.from(validKeys);
};

