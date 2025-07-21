import { filterSeriesArrayByDate } from './filters';

/**
 * Extract country data from stats for map visualization
 *
 * @param {Object} stats - The transformed stats object
 * @param {string} metric - Metric name ('views', 'downloads', 'visitors', 'dataVolume')
 * @param {Object} dateRange - Date range object
 * @param {Object} countryNameMap - Mapping object for country name normalization
 * @param {boolean} useSnapshot - Whether to use snapshot data (latest value) or delta data (sum all values)
 * @returns {Array} Array of map data objects with name, value, and originalName
 */
const extractCountryMapData = (stats, metric = 'views', dateRange = null, countryNameMap = {}, useSnapshot = true) => {
  if (!stats) {
    return [];
  }

  let countriesData = null;

  if (useSnapshot) {
    // Try to get country data from usage snapshot data
    if (metric === 'views' && stats.usageSnapshotData?.topCountriesByView?.views) {
      countriesData = stats.usageSnapshotData.topCountriesByView.views;
    } else if (metric === 'downloads' && stats.usageSnapshotData?.topCountriesByDownload?.downloads) {
      countriesData = stats.usageSnapshotData.topCountriesByDownload.downloads;
    } else if (stats.usageSnapshotData?.byCountries?.[metric]) {
      countriesData = stats.usageSnapshotData.byCountries[metric];
    }
  } else {
    // Get country data from usage delta data
    countriesData = stats.usageDeltaData?.byCountries?.[metric];
  }

  if (!countriesData || !Array.isArray(countriesData)) {
    return [];
  }

  // Filter data by date range if provided
  // For snapshot data, we want the latest value (latest=true)
  // For delta data, we want all values to sum (latest=false)
  const filteredData = filterSeriesArrayByDate(countriesData, dateRange, useSnapshot);

  // Extract country data from the filtered series
  const countryDataMap = new Map();

  filteredData.forEach(series => {
    if (series.data && Array.isArray(series.data)) {
      series.data.forEach(dataPoint => {
        if (dataPoint && dataPoint.value && Array.isArray(dataPoint.value) && dataPoint.value.length >= 3) {
          // Data structure: [date, value, label, id]
          const value = dataPoint.value[1];
          const label = dataPoint.value[2];
          const id = dataPoint.value[3] || series.id;

          if (value > 0) {
            const countryName = label?.trim() || id;
            if (countryName) {
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
        }
      });
    }
  });

  return Array.from(countryDataMap.values());
};

export { extractCountryMapData };