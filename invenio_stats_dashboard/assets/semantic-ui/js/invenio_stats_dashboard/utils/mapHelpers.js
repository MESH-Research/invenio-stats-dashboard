// Part of the Invenio-Stats-Dashboard extension for InvenioRDM
// Copyright (C) 2025 Mesh Research
//
// Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
// it under the terms of the MIT License; see LICENSE file for more details.

import { filterSeriesArrayByDate } from './filters';
import countriesGeoJson from '../components/maps/data/countries.json';
import { i18next } from "@translations/invenio_stats_dashboard/i18next";

/**
 * Create a lookup map from country codes to internationalized country names
 * Only processes countries that actually have data points for efficiency
 * @param {Array} countryCodes - Array of country codes that have data points
 * @returns {Map} Map with country codes as keys and internationalized names as values
 */
const createCountryNameLookup = (countryCodes) => {
  const lookup = new Map();

  const currentLocale = i18next.language || 'en';
  const displayNames = new Intl.DisplayNames([currentLocale], { type: 'region' });

  if (countryCodes && countryCodes.length > 0) {
    const countryCodeSet = new Set(countryCodes);

    const geoJsonCountryMap = new Map();
    if (countriesGeoJson && countriesGeoJson.features) {
      countriesGeoJson.features.forEach(feature => {
        if (feature.properties && feature.properties['ISO3166-1-Alpha-2'] && feature.properties.name) {
          const countryCode = feature.properties['ISO3166-1-Alpha-2'];
          // Only store countries that have data points
          if (countryCodeSet.has(countryCode)) {
            geoJsonCountryMap.set(countryCode, feature.properties.name);
          }
        }
      });
    }

    countryCodes.forEach(countryCode => {
      try {
        const internationalizedName = displayNames.of(countryCode);
        const geoJsonName = geoJsonCountryMap.get(countryCode);
        lookup.set(countryCode, internationalizedName || geoJsonName || countryCode);
      } catch (error) {
        // Fallback to GeoJSON name if Intl.DisplayNames fails
        console.warn(`Failed to get internationalized name for country code ${countryCode}:`, error);
        const geoJsonName = geoJsonCountryMap.get(countryCode);
        lookup.set(countryCode, geoJsonName || countryCode);
      }
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
            const readableName = countryNameLookup.get(countryCode) || countryCode;

            const numericValue = parseInt(value, 10) || 0;

            if (useSnapshot) {
              // For snapshot data, we only want the latest value per country
              // Since we filtered with latest=true, each country should have only one data point
              countryDataMap.set(countryCode, {
                name: readableName, // Use readable name for ECharts matching (matches GeoJSON name field)
                value: numericValue,
                originalName: countryCode,
                readableName: readableName // Add readable name for display
              });
            } else {
              // For delta data, we sum all values for each country
              const existing = countryDataMap.get(countryCode);
              if (existing) {
                existing.value += numericValue;
              } else {
                countryDataMap.set(countryCode, {
                  name: readableName, // Use readable name for ECharts matching (matches GeoJSON name field)
                  value: numericValue,
                  originalName: countryCode,
                  readableName: readableName // Add readable name for display
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