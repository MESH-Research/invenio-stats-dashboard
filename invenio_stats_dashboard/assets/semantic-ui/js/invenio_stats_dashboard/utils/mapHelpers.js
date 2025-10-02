// Part of the Invenio-Stats-Dashboard extension for InvenioRDM
// Copyright (C) 2025 Mesh Research
//
// Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
// it under the terms of the MIT License; see LICENSE file for more details.

import { filterSeriesArrayByDate } from './filters';

/**
 * Extract country data from stats for map visualization
 *
 * @param {Array} stats - Array of yearly stats objects
 * @param {string} metric - Metric name ('views', 'downloads', 'visitors', 'dataVolume')
 * @param {Object} dateRange - Date range object
 * @param {Object} countryNameMap - Mapping object for country name normalization
 * @param {boolean} useSnapshot - Whether to use snapshot data (latest value) or delta data (sum all values)
 * @returns {Array} Array of map data objects with name, value, and originalName
 */
const extractCountryMapData = (stats, metric = 'views', dateRange = null, countryNameMap = {}, useSnapshot = true) => {
  if (!stats || !Array.isArray(stats)) {
    return [];
  }

  // Filter out yearly chunks that don't overlap with the date range
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
    return [];
  }

  // Flatten all country data from relevant years
  const allCountriesData = relevantYearlyStats.flatMap(yearlyStats => {
    if (useSnapshot) {
      if (metric === 'views' && yearlyStats.usageSnapshotData?.countriesByView?.views) {
        return yearlyStats.usageSnapshotData.countriesByView.views;
      } else if (metric === 'downloads' && yearlyStats.usageSnapshotData?.countriesByDownload?.downloads) {
        return yearlyStats.usageSnapshotData.countriesByDownload.downloads;
      } else if (yearlyStats.usageSnapshotData?.countries?.[metric]) {
        return yearlyStats.usageSnapshotData.countries[metric];
      }
    } else {
      return yearlyStats.usageDeltaData?.countries?.[metric] || [];
    }
    return [];
  });

  if (allCountriesData.length === 0) {
    return [];
  }

  // Filter data by date range if provided
  // For snapshot data, we want the latest value (latestOnly=true)
  // For delta data, we want all values to sum (latestOnly=false)
  const filteredData = filterSeriesArrayByDate(allCountriesData, dateRange, useSnapshot);

  // Extract country data from the filtered series
  const countryDataMap = new Map();

  filteredData.forEach(series => {
    if (series.data && Array.isArray(series.data)) {
      series.data.forEach(dataPoint => {
        if (dataPoint && dataPoint.value && Array.isArray(dataPoint.value) && dataPoint.value.length >= 2) {
          // Data structure: [date, value] - country name comes from series.name
          const value = dataPoint.value[1];
          const countryName = series.name || series.id;

          if (value > 0 && countryName) {
            const mappedName = countryNameMap[countryName] || countryName;
            const numericValue = parseInt(value, 10) || 0;

            if (useSnapshot) {
              // For snapshot data, we only want the latest value per country
              // Since we filtered with latest=true, each country should have only one data point
              countryDataMap.set(mappedName, {
                name: mappedName,
                value: numericValue,
                originalName: countryName
              });
            } else {
              // For delta data, we sum all values for each country
              const existing = countryDataMap.get(mappedName);
              if (existing) {
                existing.value += numericValue;
              } else {
                countryDataMap.set(mappedName, {
                  name: mappedName,
                  value: numericValue,
                  originalName: countryName
                });
              }
            }
          }
        }
      });
    }
  });

  return Array.from(countryDataMap.values());
};

export { extractCountryMapData };