// Part of the Invenio-Stats-Dashboard extension for InvenioRDM
// Copyright (C) 2025 Mesh Research
//
// Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
// it under the terms of the MIT License; see LICENSE file for more details.

import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import React from "react";

// Cache the dates array to avoid regenerating it hundreds of times
let cachedDates = null;

// Generate dates for the specific date range
const generateDates = (startDate, endDate) => {
  const dates = [];
  let currentDate = new Date(startDate);
  while (currentDate <= endDate) {
    dates.push(currentDate.toISOString().split('T')[0]);
    currentDate.setDate(currentDate.getDate() + 1);
  }
  return dates;
};

// Create a DataPoint array matching the backend format [date, value]
// Dates are stored as MM-DD strings when all points are in the same year
const createDataPoint = (date, value, valueType = 'number', year = null) => {
  const dateStr = typeof date === 'string' ? date : date.toISOString().split('T')[0];

  // If year is provided, use MM-DD format (optimized format)
  if (year !== null) {
    const dateObj = new Date(dateStr);
    const month = String(dateObj.getMonth() + 1).padStart(2, '0');
    const day = String(dateObj.getDate()).padStart(2, '0');
    return [`${month}-${day}`, value];
  }

  // Otherwise use full YYYY-MM-DD format
  return [dateStr, value];
};

// Create a DataSeries object matching the backend format
// Adds year property when provided (indicating MM-DD format is used)
const createDataSeries = (id, name, dataPoints, type = 'line', valueType = 'number', year = null) => {
  const result = {
    id,
    name,
    data: dataPoints,
    type,
    valueType
  };

  // Add year property if year is provided
  if (year !== null) {
    result.year = year;
  }

  return result;
};

// Create a global series with cumulative data
const createGlobalSeries = (dataPoints, type = 'line', valueType = 'number', year = null) => {
  return createDataSeries("global", "Global", dataPoints, type, valueType, year);
};

// Unified data generation function to reduce code duplication
// Assumes all dates are in the same year (from the date range)
const generateDataPoints = (baseValue, variance, startValue = 0, isCumulative = false, valueType = 'number', dates, year) => {
  let cumulative = startValue;

  return dates.map((date, index) => {
    const dailyValue = Math.max(0, Math.floor(baseValue + (Math.random() * variance)));
    const finalValue = isCumulative ? (cumulative += dailyValue) : dailyValue;

    return createDataPoint(date, finalValue, valueType, year);
  });
};

// Generate sample data points for a metric
const generateMetricDataPoints = (baseValue, variance, startValue = 0, dates, year) => {
  return generateDataPoints(baseValue, variance, startValue, false, 'number', dates, year);
};

// Generate cumulative data points for a metric
const generateCumulativeDataPoints = (startValue, dailyBaseValue, dailyVariance, dates, year) => {
  return generateDataPoints(dailyBaseValue, dailyVariance, startValue, true, 'number', dates, year);
};

// Generate data volume data points (filesize type)
const generateDataVolumeDataPoints = (baseValue, variance, startValue = 0, dates, year) => {
  return generateDataPoints(baseValue, variance, startValue, false, 'filesize', dates, year);
};

// Generate cumulative data volume data points
const generateCumulativeDataVolumeDataPoints = (startValue, dailyBaseValue, dailyVariance, dates, year) => {
  return generateDataPoints(dailyBaseValue, dailyVariance, startValue, true, 'filesize', dates, year);
};

// Create record metrics structure
const createRecordMetrics = (isSnapshot = false, dates, year) => {
  const dataType = isSnapshot ? generateCumulativeDataPoints : generateMetricDataPoints;
  const dataVolumeType = isSnapshot ? generateCumulativeDataVolumeDataPoints : generateDataVolumeDataPoints;

  return {
    records: [createGlobalSeries(dataType(12500, 25, 10, dates, year), 'bar', 'number', year)],
    parents: [createGlobalSeries(dataType(12500, 25, 10, dates, year), 'bar', 'number', year)],
    uploaders: [createGlobalSeries(dataType(2500, 12, 6, dates, year), 'bar', 'number', year)],
    fileCount: [createGlobalSeries(dataType(25000, 50, 20, dates, year), 'bar', 'number', year)],
    dataVolume: [createGlobalSeries(dataVolumeType(2500000000000, 50000000, 20000000, dates, year), 'bar', 'filesize', year)]
  };
};

// Create file presence metrics structure (only records and parents)
const createFilePresenceMetrics = (isSnapshot = false, dates, year) => {
  const dataType = isSnapshot ? generateCumulativeDataPoints : generateMetricDataPoints;

  return {
    records: [createGlobalSeries(dataType(12500, 25, 10, dates, year), 'bar', 'number', year)],
    parents: [createGlobalSeries(dataType(12500, 25, 10, dates, year), 'bar', 'number', year)]
  };
};

// Create usage metrics structure
const createUsageMetrics = (isSnapshot = false, dates, year) => {
  const dataType = isSnapshot ? generateCumulativeDataPoints : generateMetricDataPoints;
  const dataVolumeType = isSnapshot ? generateCumulativeDataVolumeDataPoints : generateDataVolumeDataPoints;

  return {
    views: [createGlobalSeries(dataType(250000, 100, 50, dates, year), 'bar', 'number', year)],
    downloads: [createGlobalSeries(dataType(75000, 40, 20, dates, year), 'bar', 'number', year)],
    visitors: [createGlobalSeries(dataType(200000, 80, 40, dates, year), 'bar', 'number', year)],
    dataVolume: [createGlobalSeries(dataVolumeType(5000000000000, 200000000, 100000000, dates, year), 'bar', 'filesize', year)]
  };
};

// Create subcount series for categories that sums to global totals
const createSubcountSeries = (categoryName, items, isSnapshot = false, globalMetrics = null, dates, year) => {
  const dataType = isSnapshot ? generateCumulativeDataPoints : generateMetricDataPoints;
  const dataVolumeType = isSnapshot ? generateCumulativeDataVolumeDataPoints : generateDataVolumeDataPoints;

  // If no global metrics provided, fall back to random data
  if (!globalMetrics || items.length === 0) {
          return {
        records: items.map(item => createDataSeries(
          item.id,
          item.name,
          dataType(12500, 25, 10, dates, year),
          'line',
          'number',
          year
        )),
        parents: items.map(item => createDataSeries(
          item.id,
          item.name,
          dataType(12500, 25, 10, dates, year),
          'line',
          'number',
          year
        )),
        fileCount: items.map(item => createDataSeries(
          item.id,
          item.name,
          dataType(25000, 50, 20, dates, year),
          'line',
          'number',
          year
        )),
        dataVolume: items.map(item => createDataSeries(
          item.id,
          item.name,
          dataVolumeType(2500000000000, 50000000, 20000000, dates, year),
          'line',
          'filesize',
          year
        ))
      };
    }

  // Generate breakdown data that sums to global totals
  const generateBreakdownData = (globalDataPoints, itemCount, dates) => {
    return dates.map((date, dateIndex) => {
      // Data points are now arrays [date, value], not objects { value: [date, value] }
      const globalValue = globalDataPoints[dateIndex]?.[1] || 0;

      // Distribute the global value across breakdown items
      const distribution = [];

      if (globalValue <= 0) {
        // If no global value, give each item a small random value
        for (let i = 0; i < itemCount; i++) {
          distribution.push(Math.floor(Math.random() * 100) + 1);
        }
      } else if (itemCount === 0) {
        // No items to distribute to
        return distribution;
      } else if (itemCount === 1) {
        // Single item gets all the value
        distribution.push(globalValue);
      } else {
        // Distribute across multiple items
        let remainingValue = globalValue;

        for (let i = 0; i < itemCount; i++) {
          if (i === itemCount - 1) {
            // Last item gets the remaining value
            distribution.push(Math.max(1, remainingValue));
          } else {
            // Ensure each item gets at least 1, and distribute the rest fairly
            const minValue = 1;
            const maxPortion = Math.max(minValue, Math.floor((remainingValue - (itemCount - i - 1)) / (itemCount - i)));
            const portion = Math.floor(Math.random() * maxPortion) + minValue;
            distribution.push(portion);
            remainingValue -= portion;
          }
        }
      }

      return distribution;
    });
  };

  // Get global data points for each metric (subcounts don't include uploaders)
  const globalRecords = globalMetrics.records[0]?.data || [];
  const globalParents = globalMetrics.parents[0]?.data || [];
  const globalFileCount = globalMetrics.fileCount[0]?.data || [];
  const globalDataVolume = globalMetrics.dataVolume[0]?.data || [];

  // Generate breakdown distributions
  const recordsDistribution = generateBreakdownData(globalRecords, items.length, dates);
  const parentsDistribution = generateBreakdownData(globalParents, items.length, dates);
  const fileCountDistribution = generateBreakdownData(globalFileCount, items.length, dates);
  const dataVolumeDistribution = generateBreakdownData(globalDataVolume, items.length, dates);

  return {
    records: items.map((item, itemIndex) => {
      const dataPoints = recordsDistribution.map((distribution, dateIndex) => {
        const date = dates[dateIndex];
        const value = distribution[itemIndex] || 0;
        return createDataPoint(date, value, 'number', year);
      });
      return createDataSeries(item.id, item.name, dataPoints, 'line', 'number', year);
    }),
    parents: items.map((item, itemIndex) => {
      const dataPoints = parentsDistribution.map((distribution, dateIndex) => {
        const date = dates[dateIndex];
        const value = distribution[itemIndex] || 0;
        return createDataPoint(date, value, 'number', year);
      });
      return createDataSeries(item.id, item.name, dataPoints, 'line', 'number', year);
    }),
    fileCount: items.map((item, itemIndex) => {
      const dataPoints = fileCountDistribution.map((distribution, dateIndex) => {
        const date = dates[dateIndex];
        const value = distribution[itemIndex] || 0;
        return createDataPoint(date, value, 'number', year);
      });
      return createDataSeries(item.id, item.name, dataPoints, 'line', 'number', year);
    }),
    dataVolume: items.map((item, itemIndex) => {
      const dataPoints = dataVolumeDistribution.map((distribution, dateIndex) => {
        const date = dates[dateIndex];
        const value = distribution[itemIndex] || 0;
        return createDataPoint(date, value, 'filesize', year);
      });
      return createDataSeries(item.id, item.name, dataPoints, 'line', 'filesize', year);
    })
  };
};

// Create usage subcount series for categories that sums to global totals
const createUsageSubcountSeries = (categoryName, items, isSnapshot = false, globalMetrics = null, dates, year) => {
  const dataType = isSnapshot ? generateCumulativeDataPoints : generateMetricDataPoints;
  const dataVolumeType = isSnapshot ? generateCumulativeDataVolumeDataPoints : generateDataVolumeDataPoints;

  // If no global metrics provided, fall back to random data
  if (!globalMetrics || items.length === 0) {
          return {
        views: items.map(item => {
          return createDataSeries(
            item.id,
            item.name,
            dataType(250000, 100, 50, dates, year),
            'line',
            'number',
            year
          );
        }),
        downloads: items.map(item => {
          return createDataSeries(
            item.id,
            item.name,
            dataType(75000, 40, 20, dates, year),
            'line',
            'number',
            year
          );
        }),
        visitors: items.map(item => {
          return createDataSeries(
            item.id,
            item.name,
            dataType(200000, 80, 40, dates, year),
            'line',
            'number',
            year
          );
        }),
        dataVolume: items.map(item => {
          return createDataSeries(
            item.id,
            item.name,
            dataVolumeType(5000000000000, 200000000, 100000000, dates, year),
            'line',
            'filesize',
            year
          );
        })
      };
  }

  // Generate breakdown data that sums to global totals
  const generateBreakdownData = (globalDataPoints, itemCount, dates) => {
    return dates.map((date, dateIndex) => {
      // Data points are now arrays [date, value], not objects { value: [date, value] }
      const globalValue = globalDataPoints[dateIndex]?.[1] || 0;

      // Distribute the global value across breakdown items
      const distribution = [];

      if (globalValue <= 0) {
        // If no global value, give each item a small random value
        for (let i = 0; i < itemCount; i++) {
          distribution.push(Math.floor(Math.random() * 100) + 1);
        }
      } else if (itemCount === 0) {
        // No items to distribute to
        return distribution;
      } else if (itemCount === 1) {
        // Single item gets all the value
        distribution.push(globalValue);
      } else {
        // Distribute across multiple items
        let remainingValue = globalValue;

        for (let i = 0; i < itemCount; i++) {
          if (i === itemCount - 1) {
            // Last item gets the remaining value
            distribution.push(Math.max(1, remainingValue));
          } else {
            // Ensure each item gets at least 1, and distribute the rest fairly
            const minValue = 1;
            const maxPortion = Math.max(minValue, Math.floor((remainingValue - (itemCount - i - 1)) / (itemCount - i)));
            const portion = Math.floor(Math.random() * maxPortion) + minValue;
            distribution.push(portion);
            remainingValue -= portion;
          }
        }
      }

      return distribution;
    });
  };

  // Get global data points for each metric
  const globalViews = globalMetrics.views[0]?.data || [];
  const globalDownloads = globalMetrics.downloads[0]?.data || [];
  const globalVisitors = globalMetrics.visitors[0]?.data || [];
  const globalDataVolume = globalMetrics.dataVolume[0]?.data || [];

  // Generate breakdown distributions
  const viewsDistribution = generateBreakdownData(globalViews, items.length, dates);
  const downloadsDistribution = generateBreakdownData(globalDownloads, items.length, dates);
  const visitorsDistribution = generateBreakdownData(globalVisitors, items.length, dates);
  const dataVolumeDistribution = generateBreakdownData(globalDataVolume, items.length, dates);

  return {
    views: items.map((item, itemIndex) => {
      const dataPoints = viewsDistribution.map((distribution, dateIndex) => {
        const date = dates[dateIndex];
        const value = distribution[itemIndex] || 0;
        return createDataPoint(date, value, 'number', year);
      });
      return createDataSeries(item.id, item.name, dataPoints, 'line', 'number', year);
    }),
    downloads: items.map((item, itemIndex) => {
      const dataPoints = downloadsDistribution.map((distribution, dateIndex) => {
        const date = dates[dateIndex];
        const value = distribution[itemIndex] || 0;
        return createDataPoint(date, value, 'number', year);
      });
      return createDataSeries(item.id, item.name, dataPoints, 'line', 'number', year);
    }),
    visitors: items.map((item, itemIndex) => {
      const dataPoints = visitorsDistribution.map((distribution, dateIndex) => {
        const date = dates[dateIndex];
        const value = distribution[itemIndex] || 0;
        return createDataPoint(date, value, 'number', year);
      });
      return createDataSeries(item.id, item.name, dataPoints, 'line', 'number', year);
    }),
    dataVolume: items.map((item, itemIndex) => {
      const dataPoints = dataVolumeDistribution.map((distribution, dateIndex) => {
        const date = dates[dateIndex];
        const value = distribution[itemIndex] || 0;
        return createDataPoint(date, value, 'filesize', year);
      });
      return createDataSeries(item.id, item.name, dataPoints, 'line', 'filesize', year);
    })
  };
};

// Sample items for different categories
const resourceTypesItems = [
  { id: 'dataset', name: 'Dataset' },
  { id: 'software', name: 'Software' },
  { id: 'research_paper', name: 'Research Paper' },
  { id: 'other', name: 'Other' }
];

const accessStatusesItems = [
  { id: 'open', name: 'Open Access' },
  { id: 'embargoed', name: 'Embargoed' },
  { id: 'restricted', name: 'Restricted' },
  { id: 'metadata-only', name: 'Metadata Only' }
];

const languagesItems = [
  { id: 'eng', name: 'English' },
  { id: 'spa', name: 'Spanish' },
  { id: 'fra', name: 'French' },
  { id: 'deu', name: 'German' }
];

const affiliationsItems = [
  { id: 'uc-berkeley', name: 'University of California, Berkeley' },
  { id: 'mit', name: 'Massachusetts Institute of Technology' },
  { id: 'stanford', name: 'Stanford University' },
  { id: 'harvard', name: 'Harvard University' }
];

const fundersItems = [
  { id: 'nsf', name: 'National Science Foundation' },
  { id: 'nih', name: 'National Institutes of Health' },
  { id: 'erc', name: 'European Research Council' },
  { id: 'wellcome', name: 'Wellcome Trust' }
];

const subjectsItems = [
  { id: 'computer_science', name: 'Computer Science' },
  { id: 'environmental_science', name: 'Environmental Science' },
  { id: 'biology', name: 'Biology' },
  { id: 'physics', name: 'Physics' }
];

const publishersItems = [
  { id: 'springer', name: 'Springer' },
  { id: 'elsevier', name: 'Elsevier' },
  { id: 'wiley', name: 'Wiley' },
  { id: 'nature', name: 'Nature' }
];

const periodicalsItems = [
  { id: 'nature', name: 'Nature' },
  { id: 'science', name: 'Science' },
  { id: 'cell', name: 'Cell' },
  { id: 'plos-one', name: 'PLOS ONE' }
];

const rightsItems = [
  { id: 'cc-by-4.0', name: 'Creative Commons Attribution 4.0 International' },
  { id: 'cc-by-sa-4.0', name: 'Creative Commons Attribution-ShareAlike 4.0 International' },
  { id: 'cc-by-nc-4.0', name: 'Creative Commons Attribution-NonCommercial 4.0 International' },
  { id: 'cc0-1.0', name: 'Creative Commons Zero 1.0 Universal' }
];

const fileTypesItems = [
  { id: 'pdf', name: 'PDF' },
  { id: 'csv', name: 'CSV' },
  { id: 'json', name: 'JSON' },
  { id: 'zip', name: 'ZIP' }
];

const countriesItems = [
  { id: 'us', name: 'United States' },
  { id: 'gb', name: 'United Kingdom' },
  { id: 'de', name: 'Germany' },
  { id: 'fr', name: 'France' },
  { id: 'ca', name: 'Canada' },
  { id: 'au', name: 'Australia' },
  { id: 'nl', name: 'Netherlands' },
  { id: 'se', name: 'Sweden' },
  { id: 'ch', name: 'Switzerland' },
  { id: 'no', name: 'Norway' },
  { id: 'dk', name: 'Denmark' },
  { id: 'fi', name: 'Finland' },
  { id: 'it', name: 'Italy' },
  { id: 'es', name: 'Spain' },
  { id: 'jp', name: 'Japan' },
  { id: 'cn', name: 'China' },
  { id: 'kr', name: 'South Korea' },
  { id: 'in', name: 'India' },
  { id: 'br', name: 'Brazil' },
  { id: 'mx', name: 'Mexico' }
];

const referrersItems = [
  { id: 'google.com', name: 'google.com' },
  { id: 'scholar.google.com', name: 'scholar.google.com' },
  { id: 'github.com', name: 'github.com' },
  { id: 'linkedin.com', name: 'linkedin.com' }
];

// Sample record data for most viewed/downloaded lists
const sampleRecords = [
  {
    id: "climate-change-analysis-2023",
    title: "Dataset: Climate Change Analysis 2023",
    views: 1234567,
    downloads: 234567
  },
  {
    id: "ai-ethics-research",
    title: "Research Paper: AI Ethics",
    views: 987654,
    downloads: 187654
  },
  {
    id: "global-population-trends",
    title: "Dataset: Global Population Trends",
    views: 876543,
    downloads: 176543
  },
  {
    id: "quantum-computing-paper",
    title: "Research Paper: Quantum Computing",
    views: 765432,
    downloads: 165432
  },
  {
    id: "renewable-energy-sources",
    title: "Dataset: Renewable Energy Sources",
    views: 654321,
    downloads: 154321
  }
];

// Create the test data structure that matches the dataTransformer output
const generateTestStatsData = async (startDate, endDate) => {
  // Generate dates once at the top
  const dates = generateDates(startDate, endDate);
  // Extract year once at the top (all dates should be in the same year)
  const year = dates.length > 0 ? new Date(dates[0]).getFullYear() : new Date().getFullYear();

  return {
  // Record Delta Data
  recordDeltaDataCreated: (() => {
    const globalMetrics = createRecordMetrics(false, dates, year);
    return {
      global: globalMetrics,
      filePresence: createFilePresenceMetrics(false, dates, year),
      resourceTypes: createSubcountSeries('resourceTypes', resourceTypesItems, false, globalMetrics, dates, year),
      accessStatuses: createSubcountSeries('accessStatuses', accessStatusesItems, false, globalMetrics, dates, year),
      languages: createSubcountSeries('languages', languagesItems, false, globalMetrics, dates, year),
      affiliations: createSubcountSeries('affiliations', affiliationsItems, false, globalMetrics, dates, year),
      funders: createSubcountSeries('funders', fundersItems, false, globalMetrics, dates, year),
      subjects: createSubcountSeries('subjects', subjectsItems, false, globalMetrics, dates, year),
      publishers: createSubcountSeries('publishers', publishersItems, false, globalMetrics, dates, year),
      periodicals: createSubcountSeries('periodicals', periodicalsItems, false, globalMetrics, dates, year),
      rights: createSubcountSeries('rights', rightsItems, false, globalMetrics, dates, year),
      fileTypes: createSubcountSeries('fileTypes', fileTypesItems, false, globalMetrics, dates, year)
    };
  })(),

  recordDeltaDataAdded: (() => {
    const globalMetrics = createRecordMetrics(false, dates, year);
    return {
      global: globalMetrics,
      filePresence: createFilePresenceMetrics(false, dates, year),
      resourceTypes: createSubcountSeries('resourceTypes', resourceTypesItems, false, globalMetrics, dates, year),
      accessStatuses: createSubcountSeries('accessStatuses', accessStatusesItems, false, globalMetrics, dates, year),
      languages: createSubcountSeries('languages', languagesItems, false, globalMetrics, dates, year),
      affiliations: createSubcountSeries('affiliations', affiliationsItems, false, globalMetrics, dates, year),
      funders: createSubcountSeries('funders', fundersItems, false, globalMetrics, dates, year),
      subjects: createSubcountSeries('subjects', subjectsItems, false, globalMetrics, dates, year),
      publishers: createSubcountSeries('publishers', publishersItems, false, globalMetrics, dates, year),
      periodicals: createSubcountSeries('periodicals', periodicalsItems, false, globalMetrics, dates, year),
      rights: createSubcountSeries('rights', rightsItems, false, globalMetrics, dates, year),
      fileTypes: createSubcountSeries('fileTypes', fileTypesItems, false, globalMetrics, dates, year)
    };
  })(),

  recordDeltaDataPublished: (() => {
    const globalMetrics = createRecordMetrics(false, dates, year);
    return {
      global: globalMetrics,
      filePresence: createFilePresenceMetrics(false, dates, year),
      resourceTypes: createSubcountSeries('resourceTypes', resourceTypesItems, false, globalMetrics, dates, year),
      accessStatuses: createSubcountSeries('accessStatuses', accessStatusesItems, false, globalMetrics, dates, year),
      languages: createSubcountSeries('languages', languagesItems, false, globalMetrics, dates, year),
      affiliations: createSubcountSeries('affiliations', affiliationsItems, false, globalMetrics, dates, year),
      funders: createSubcountSeries('funders', fundersItems, false, globalMetrics, dates, year),
      subjects: createSubcountSeries('subjects', subjectsItems, false, globalMetrics, dates, year),
      publishers: createSubcountSeries('publishers', publishersItems, false, globalMetrics, dates, year),
      periodicals: createSubcountSeries('periodicals', periodicalsItems, false, globalMetrics, dates, year),
      rights: createSubcountSeries('rights', rightsItems, false, globalMetrics, dates, year),
      fileTypes: createSubcountSeries('fileTypes', fileTypesItems, false, globalMetrics, dates, year)
    };
  })(),

  // Record Snapshot Data
  recordSnapshotDataCreated: (() => {
    const globalMetrics = createRecordMetrics(true, dates, year);
    return {
      global: globalMetrics,
      filePresence: createFilePresenceMetrics(true, dates, year),
      resourceTypes: createSubcountSeries('resourceTypes', resourceTypesItems, true, globalMetrics, dates, year),
      accessStatuses: createSubcountSeries('accessStatuses', accessStatusesItems, true, globalMetrics, dates, year),
      languages: createSubcountSeries('languages', languagesItems, true, globalMetrics, dates, year),
      affiliations: createSubcountSeries('affiliations', affiliationsItems, true, globalMetrics, dates, year),
      funders: createSubcountSeries('funders', fundersItems, true, globalMetrics, dates, year),
      subjects: createSubcountSeries('subjects', subjectsItems, true, globalMetrics, dates, year),
      publishers: createSubcountSeries('publishers', publishersItems, true, globalMetrics, dates, year),
      periodicals: createSubcountSeries('periodicals', periodicalsItems, true, globalMetrics, dates, year),
      rights: createSubcountSeries('rights', rightsItems, true, globalMetrics, dates, year),
      fileTypes: createSubcountSeries('fileTypes', fileTypesItems, true, globalMetrics, dates)
    };
  })(),

  recordSnapshotDataAdded: (() => {
    const globalMetrics = createRecordMetrics(true, dates, year);
    return {
      global: globalMetrics,
      filePresence: createFilePresenceMetrics(true, dates, year),
      resourceTypes: createSubcountSeries('resourceTypes', resourceTypesItems, true, globalMetrics, dates, year),
      accessStatuses: createSubcountSeries('accessStatuses', accessStatusesItems, true, globalMetrics, dates, year),
      languages: createSubcountSeries('languages', languagesItems, true, globalMetrics, dates, year),
      affiliations: createSubcountSeries('affiliations', affiliationsItems, true, globalMetrics, dates, year),
      funders: createSubcountSeries('funders', fundersItems, true, globalMetrics, dates, year),
      subjects: createSubcountSeries('subjects', subjectsItems, true, globalMetrics, dates, year),
      publishers: createSubcountSeries('publishers', publishersItems, true, globalMetrics, dates, year),
      periodicals: createSubcountSeries('periodicals', periodicalsItems, true, globalMetrics, dates, year),
      rights: createSubcountSeries('rights', rightsItems, true, globalMetrics, dates, year),
      fileTypes: createSubcountSeries('fileTypes', fileTypesItems, true, globalMetrics, dates)
    };
  })(),

  recordSnapshotDataPublished: (() => {
    const globalMetrics = createRecordMetrics(true, dates, year);
    return {
      global: globalMetrics,
      filePresence: createFilePresenceMetrics(true, dates, year),
      resourceTypes: createSubcountSeries('resourceTypes', resourceTypesItems, true, globalMetrics, dates, year),
      accessStatuses: createSubcountSeries('accessStatuses', accessStatusesItems, true, globalMetrics, dates, year),
      languages: createSubcountSeries('languages', languagesItems, true, globalMetrics, dates, year),
      affiliations: createSubcountSeries('affiliations', affiliationsItems, true, globalMetrics, dates, year),
      funders: createSubcountSeries('funders', fundersItems, true, globalMetrics, dates, year),
      subjects: createSubcountSeries('subjects', subjectsItems, true, globalMetrics, dates, year),
      publishers: createSubcountSeries('publishers', publishersItems, true, globalMetrics, dates, year),
      periodicals: createSubcountSeries('periodicals', periodicalsItems, true, globalMetrics, dates, year),
      rights: createSubcountSeries('rights', rightsItems, true, globalMetrics, dates, year),
      fileTypes: createSubcountSeries('fileTypes', fileTypesItems, true, globalMetrics, dates)
    };
  })(),

  // Usage Delta Data
  usageDeltaData: (() => {
    const globalMetrics = createUsageMetrics(false, dates, year);
    return {
      global: globalMetrics,
      accessStatuses: createUsageSubcountSeries('accessStatuses', accessStatusesItems, false, globalMetrics, dates, year),
      fileTypes: createUsageSubcountSeries('fileTypes', fileTypesItems, false, globalMetrics, dates, year),
      languages: createUsageSubcountSeries('languages', languagesItems, false, globalMetrics, dates, year),
      resourceTypes: createUsageSubcountSeries('resourceTypes', resourceTypesItems, false, globalMetrics, dates, year),
      // subjects: createUsageSubcountSeries('subjects', subjectsItems, false, globalMetrics, dates, year),
      publishers: createUsageSubcountSeries('publishers', publishersItems, false, globalMetrics, dates, year),
      rights: createUsageSubcountSeries('rights', rightsItems, false, globalMetrics, dates, year),
      countries: createUsageSubcountSeries('countries', countriesItems, false, globalMetrics, dates, year),
      // referrers: createUsageSubcountSeries('referrers', referrersItems, false, globalMetrics, dates, year),
      affiliations: createUsageSubcountSeries('affiliations', affiliationsItems, false, globalMetrics, dates, year)
    };
  })(),

  // Usage Snapshot Data
  usageSnapshotData: (() => {
    const globalMetrics = createUsageMetrics(true, dates, year);
    return {
      global: globalMetrics,
      accessStatuses: createUsageSubcountSeries('accessStatuses', accessStatusesItems, true, globalMetrics, dates, year),
      fileTypes: createUsageSubcountSeries('fileTypes', fileTypesItems, true, globalMetrics, dates, year),
      languages: createUsageSubcountSeries('languages', languagesItems, true, globalMetrics, dates, year),
      resourceTypes: createUsageSubcountSeries('resourceTypes', resourceTypesItems, true, globalMetrics, dates, year),
      // subjects: createUsageSubcountSeries('subjects', subjectsItems, true, globalMetrics, dates, year),
      publishers: createUsageSubcountSeries('publishers', publishersItems, true, globalMetrics, dates, year),
      rights: createUsageSubcountSeries('rights', rightsItems, true, globalMetrics, dates, year),
      countries: createUsageSubcountSeries('countries', countriesItems, true, globalMetrics, dates, year),
      // referrers: createUsageSubcountSeries('referrers', referrersItems, true, globalMetrics, dates, year),
      affiliations: createUsageSubcountSeries('affiliations', affiliationsItems, true, globalMetrics, dates, year),
      countriesByView: createUsageSubcountSeries('countriesByView', countriesItems, true, globalMetrics, dates, year),
      countriesByDownload: createUsageSubcountSeries('countriesByDownload', countriesItems, true, globalMetrics, dates, year),
      // subjectsByView: createUsageSubcountSeries('subjectsByView', subjectsItems, true, globalMetrics, dates, year),
      // subjectsByDownload: createUsageSubcountSeries('subjectsByDownload', subjectsItems, true, globalMetrics, dates, year),
      publishersByView: createUsageSubcountSeries('publishersByView', publishersItems, true, globalMetrics, dates, year),
      publishersByDownload: createUsageSubcountSeries('publishersByDownload', publishersItems, true, globalMetrics, dates, year),
      rightsByView: createUsageSubcountSeries('rightsByView', rightsItems, true, globalMetrics, dates, year),
      rightsByDownload: createUsageSubcountSeries('rightsByDownload', rightsItems, true, globalMetrics, dates, year),
      // referrersByView: createUsageSubcountSeries('referrersByView', referrersItems, true, globalMetrics, dates)
    };
  })(),

  // TODO: Implement these in the API data
  // Most viewed/downloaded records data (for backward compatibility)
  mostViewedRecords: sampleRecords.map(record => ({
    title: record.title,
    views: record.views,
    percentage: Math.round((record.views / 4518517) * 100), // Total of all views
    id: record.id,
  })),

  mostDownloadedRecords: sampleRecords.map(record => ({
    title: record.title,
    downloads: record.downloads,
    percentage: Math.round((record.downloads / 918517) * 100), // Total of all downloads
    id: record.id,
  }))
}};

export { createDataPoint, createDataSeries, createGlobalSeries, sampleRecords, generateTestStatsData };