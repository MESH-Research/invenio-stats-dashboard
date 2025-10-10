// Part of the Invenio-Stats-Dashboard extension for InvenioRDM
// Copyright (C) 2025 Mesh Research
//
// Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
// it under the terms of the MIT License; see LICENSE file for more details.

import { filterSeriesArrayByDate } from './filters';
import countriesGeoJson from '../components/maps/data/countries.json';
import { i18next } from "@translations/invenio_stats_dashboard/i18next";

/**
 * Convert a single country code to both GeoJSON name and display name
 * @param {string} countryCode - ISO 3166-1 alpha-2 country code
 * @returns {Object} Object with geoJsonName and displayName properties
 */
const getCountryNames = (countryCode) => {
  if (!countryCode || typeof countryCode !== 'string') {
    return { geoJsonName: countryCode || '', displayName: countryCode || '' };
  }

  const currentLocale = i18next.language || 'en';

  // Get display name using Intl.DisplayNames
  let displayName = countryCode;
  try {
    const displayNames = new Intl.DisplayNames([currentLocale], { type: 'region' });
    displayName = displayNames.of(countryCode) || countryCode;
  } catch (error) {
    console.warn(`Failed to get internationalized name for country code ${countryCode}:`, error);
  }

  // Get GeoJSON name
  let geoJsonName = countryCode;
  if (countriesGeoJson && countriesGeoJson.features) {
    const feature = countriesGeoJson.features.find(f =>
      f.properties && f.properties['ISO3166-1-Alpha-2'] === countryCode
    );
    if (feature && feature.properties && feature.properties.name) {
      geoJsonName = feature.properties.name;
    }
  }

  return {
    geoJsonName: geoJsonName,
    displayName: displayName
  };
};

/**
 * Create a lookup map from country codes to both GeoJSON names and display names
 * Only processes countries that actually have data points for efficiency
 * @param {Array} countryCodes - Array of country codes that have data points
 * @returns {Map} Map with country codes as keys and objects with geoJsonName and displayName as values
 */
const createCountryNameLookup = (countryCodes) => {
  const lookup = new Map();

  if (countryCodes && countryCodes.length > 0) {
    countryCodes.forEach(countryCode => {
      const countryNames = getCountryNames(countryCode);
      lookup.set(countryCode, countryNames);
    });
  }

  return lookup;
};

/**
 * Extract country data from stats for map visualization
 *
 * @param {Array} stats - Array of yearly stats objects
 * @param {string} metric - Metric name ('views', 'downloads', 'visitors', 'dataVolume')
 * @param {Object} dateRange - Date range object
 * @param {Object} useSnapshot - Whether to use snapshot data (latest value) or delta data (sum all values)
 * @param {boolean} useSnapshot - Whether to use snapshot data (latest value) or delta data (sum all values)
 * @returns {Array} Array of map data objects with name (country code), value, originalName, and readableName
 */
const extractCountryMapData = (stats, metric = 'views', dateRange = null, useSnapshot = true) => {
  if (!stats || !Array.isArray(stats)) {
    return [];
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
    return [];
  }

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

  const countryCodesWithData = new Set();
  filteredData.forEach(series => {
    if (series.data && Array.isArray(series.data)) {
      series.data.forEach(dataPoint => {
        if (dataPoint && dataPoint.value && Array.isArray(dataPoint.value) && dataPoint.value.length >= 2) {
          const value = dataPoint.value[1];
          const countryName = series.name || series.id;
          if (value > 0 && countryName) {
            countryCodesWithData.add(countryName);
          }
        }
      });
    }
  });
  const countryNameLookup = createCountryNameLookup(Array.from(countryCodesWithData));

  const countryDataMap = new Map();

  filteredData.forEach(series => {
    if (series.data && Array.isArray(series.data)) {
      series.data.forEach(dataPoint => {
        if (dataPoint && dataPoint.value && Array.isArray(dataPoint.value) && dataPoint.value.length >= 2) {
          // Data structure: [date, value] - country name comes from series.name
          const value = dataPoint.value[1];
          const countryName = series.name || series.id;

          if (value > 0 && countryName) {
            // Data starts with country ISO3166-1-Alpha-2 codes
            const countryCode = countryName;

            // Use the lookup we created
            const countryInfo = countryNameLookup.get(countryCode);
            const geoJsonName = countryInfo?.geoJsonName || countryCode;
            const displayName = countryInfo?.displayName || countryCode;

            const numericValue = parseInt(value, 10) || 0;

            if (useSnapshot) {
              // For snapshot data, we only want the latest value per country
              // Since we filtered with latest=true, each country should have only one data point
              countryDataMap.set(countryCode, {
                name: geoJsonName, // Use GeoJSON name for ECharts matching (matches GeoJSON name field)
                value: numericValue,
                originalName: countryCode,
                readableName: displayName // Add display name for user interface
              });
            } else {
              // For delta data, we sum all values for each country
              const existing = countryDataMap.get(countryCode);
              if (existing) {
                existing.value += numericValue;
              } else {
                countryDataMap.set(countryCode, {
                  name: geoJsonName, // Use GeoJSON name for ECharts matching (matches GeoJSON name field)
                  value: numericValue,
                  originalName: countryCode,
                  readableName: displayName // Add display name for user interface
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

export { extractCountryMapData, getCountryNames };