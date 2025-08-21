import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import React from "react";

// Cache the dates array to avoid regenerating it hundreds of times
let cachedDates = null;

// Generate dates for multiple years
const generateDates = () => {
  if (cachedDates === null) {
    const dates = [];
    const today = new Date();
    // Use UTC dates to match the dashboard's date handling
    const startDate = new Date(Date.UTC(today.getFullYear() - 3, 0, 1)); // Start from 3 years ago
    const endDate = new Date(Date.UTC(today.getFullYear(), today.getMonth(), today.getDate()));

    let currentDate = new Date(startDate);
    while (currentDate <= endDate) {
      dates.push(currentDate.toISOString().split('T')[0]);
      currentDate.setDate(currentDate.getDate() + 1);
    }
    cachedDates = dates;
  }
  return cachedDates;
};

// Cache data point templates to avoid repeated object creation
const createDataPointTemplate = (date) => ({
  value: [new Date(date), 0],
  readableDate: new Date(date).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  }),
  valueType: 'number'
});

// Pre-generate data point templates for all dates
let cachedDataPointTemplates = null;
const getDataPointTemplates = () => {
  if (cachedDataPointTemplates === null) {
    const dates = generateDates();
    cachedDataPointTemplates = dates.map(date => createDataPointTemplate(date));
  }
  return cachedDataPointTemplates;
};

// Create a DataPoint object matching the dataTransformer format
const createDataPoint = (date, value, valueType = 'number') => {
  const templates = getDataPointTemplates();
  const dateIndex = generateDates().indexOf(date);
  if (dateIndex !== -1) {
    // Clone the template and update the value
    const dataPoint = { ...templates[dateIndex] };
    // DataPoint.value should be [date, value] array as expected by dataTransformer.js
    dataPoint.value = [dataPoint.value[0], value];
    dataPoint.valueType = valueType;
    return dataPoint;
  }

  // Fallback for dates not in cache
  const dateObj = new Date(date);
  return {
    value: [dateObj, value],
    readableDate: dateObj.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    }),
    valueType
  };
};

// Create a DataSeries object matching the dataTransformer format
const createDataSeries = (id, name, dataPoints, type = 'line', valueType = 'number') => ({
  id,
  name,
  data: dataPoints,
  type,
  valueType
});

// Create a global series with cumulative data
const createGlobalSeries = (dataPoints, type = 'line', valueType = 'number') => ({
  id: "global",
  name: "Global",
  data: dataPoints,
  type,
  valueType
});

// Unified data generation function to reduce code duplication
const generateDataPoints = (baseValue, variance, startValue = 0, isCumulative = false, valueType = 'number') => {
  const dates = generateDates();
  let cumulative = startValue;
  const templates = getDataPointTemplates();

  return dates.map((date, index) => {
    const dailyValue = Math.max(0, Math.floor(baseValue + (Math.random() * variance)));
    const finalValue = isCumulative ? (cumulative += dailyValue) : dailyValue;

    // Use cached template for better performance
    const dataPoint = { ...templates[index] };
    dataPoint.value = [dataPoint.value[0], finalValue];
    dataPoint.valueType = valueType;
    return dataPoint;
  });
};

// Generate sample data points for a metric
const generateMetricDataPoints = (baseValue, variance, startValue = 0) => {
  return generateDataPoints(baseValue, variance, startValue, false, 'number');
};

// Generate cumulative data points for a metric
const generateCumulativeDataPoints = (startValue, dailyBaseValue, dailyVariance) => {
  return generateDataPoints(dailyBaseValue, dailyVariance, startValue, true, 'number');
};

// Generate data volume data points (filesize type)
const generateDataVolumeDataPoints = (baseValue, variance, startValue = 0) => {
  return generateDataPoints(baseValue, variance, startValue, false, 'filesize');
};

// Generate cumulative data volume data points
const generateCumulativeDataVolumeDataPoints = (startValue, dailyBaseValue, dailyVariance) => {
  return generateDataPoints(dailyBaseValue, dailyVariance, startValue, true, 'filesize');
};

// Create record metrics structure
const createRecordMetrics = (isSnapshot = false) => {
  const dataType = isSnapshot ? generateCumulativeDataPoints : generateMetricDataPoints;
  const dataVolumeType = isSnapshot ? generateCumulativeDataVolumeDataPoints : generateDataVolumeDataPoints;

  return {
    records: [createGlobalSeries(dataType(12500, 25, 10), 'bar', 'number')],
    parents: [createGlobalSeries(dataType(12500, 25, 10), 'bar', 'number')],
    uploaders: [createGlobalSeries(dataType(2500, 12, 6), 'bar', 'number')],
    fileCount: [createGlobalSeries(dataType(25000, 50, 20), 'bar', 'number')],
    dataVolume: [createGlobalSeries(dataVolumeType(2500000000000, 50000000, 20000000), 'bar', 'filesize')]
  };
};

// Create file presence metrics structure (only records and parents)
const createFilePresenceMetrics = (isSnapshot = false) => {
  const dataType = isSnapshot ? generateCumulativeDataPoints : generateMetricDataPoints;

  return {
    records: [createGlobalSeries(dataType(12500, 25, 10), 'bar', 'number')],
    parents: [createGlobalSeries(dataType(12500, 25, 10), 'bar', 'number')]
  };
};

// Create usage metrics structure
const createUsageMetrics = (isSnapshot = false) => {
  const dataType = isSnapshot ? generateCumulativeDataPoints : generateMetricDataPoints;
  const dataVolumeType = isSnapshot ? generateCumulativeDataVolumeDataPoints : generateDataVolumeDataPoints;

  return {
    views: [createGlobalSeries(dataType(250000, 100, 50), 'bar', 'number')],
    downloads: [createGlobalSeries(dataType(75000, 40, 20), 'bar', 'number')],
    visitors: [createGlobalSeries(dataType(200000, 80, 40), 'bar', 'number')],
    dataVolume: [createGlobalSeries(dataVolumeType(5000000000000, 200000000, 100000000), 'bar', 'filesize')]
  };
};

// Create subcount series for categories that sums to global totals
const createSubcountSeries = (categoryName, items, isSnapshot = false, globalMetrics = null) => {
  const dataType = isSnapshot ? generateCumulativeDataPoints : generateMetricDataPoints;
  const dataVolumeType = isSnapshot ? generateCumulativeDataVolumeDataPoints : generateDataVolumeDataPoints;

  // If no global metrics provided, fall back to random data
  if (!globalMetrics || items.length === 0) {
          return {
        records: items.map(item => createDataSeries(
          item.id,
          item.name,
          dataType(12500, 25, 10),
          'line',
          'number'
        )),
        parents: items.map(item => createDataSeries(
          item.id,
          item.name,
          dataType(12500, 25, 10),
          'line',
          'number'
        )),
        uploaders: items.map(item => createDataSeries(
          item.id,
          item.name,
          dataType(2500, 12, 6),
          'line',
          'number'
        )),
        fileCount: items.map(item => createDataSeries(
          item.id,
          item.name,
          dataType(25000, 50, 20),
          'line',
          'number'
        )),
        dataVolume: items.map(item => createDataSeries(
          item.id,
          item.name,
          dataVolumeType(2500000000000, 50000000, 20000000),
          'line',
          'filesize'
        ))
      };
  }

  // Generate breakdown data that sums to global totals
  const generateBreakdownData = (globalDataPoints, itemCount) => {
    const dates = generateDates();
    return dates.map((date, dateIndex) => {
      const globalValue = globalDataPoints[dateIndex]?.value?.[1] || 0;

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
  const globalRecords = globalMetrics.records[0]?.data || [];
  const globalParents = globalMetrics.parents[0]?.data || [];
  const globalUploaders = globalMetrics.uploaders[0]?.data || [];
  const globalFileCount = globalMetrics.fileCount[0]?.data || [];
  const globalDataVolume = globalMetrics.dataVolume[0]?.data || [];

  // Generate breakdown distributions
  const recordsDistribution = generateBreakdownData(globalRecords, items.length);
  const parentsDistribution = generateBreakdownData(globalParents, items.length);
  const uploadersDistribution = generateBreakdownData(globalUploaders, items.length);
  const fileCountDistribution = generateBreakdownData(globalFileCount, items.length);
  const dataVolumeDistribution = generateBreakdownData(globalDataVolume, items.length);

  return {
    records: items.map((item, itemIndex) => {
      const dataPoints = recordsDistribution.map((distribution, dateIndex) => {
        const date = generateDates()[dateIndex];
        const value = distribution[itemIndex] || 0;
        return createDataPoint(date, value, 'number');
      });
      return createDataSeries(item.id, item.name, dataPoints, 'line', 'number');
    }),
    parents: items.map((item, itemIndex) => {
      const dataPoints = parentsDistribution.map((distribution, dateIndex) => {
        const date = generateDates()[dateIndex];
        const value = distribution[itemIndex] || 0;
        return createDataPoint(date, value, 'number');
      });
      return createDataSeries(item.id, item.name, dataPoints, 'line', 'number');
    }),
    uploaders: items.map((item, itemIndex) => {
      const dataPoints = uploadersDistribution.map((distribution, dateIndex) => {
        const date = generateDates()[dateIndex];
        const value = distribution[itemIndex] || 0;
        return createDataPoint(date, value, 'number');
      });
      return createDataSeries(item.id, item.name, dataPoints, 'line', 'number');
    }),
    fileCount: items.map((item, itemIndex) => {
      const dataPoints = fileCountDistribution.map((distribution, dateIndex) => {
        const date = generateDates()[dateIndex];
        const value = distribution[itemIndex] || 0;
        return createDataPoint(date, value, 'number');
      });
      return createDataSeries(item.id, item.name, dataPoints, 'line', 'number');
    }),
    dataVolume: items.map((item, itemIndex) => {
      const dataPoints = dataVolumeDistribution.map((distribution, dateIndex) => {
        const date = generateDates()[dateIndex];
        const value = distribution[itemIndex] || 0;
        return createDataPoint(date, value, 'filesize');
      });
      return createDataSeries(item.id, item.name, dataPoints, 'line', 'filesize');
    })
  };
};

// Create usage subcount series for categories that sums to global totals
const createUsageSubcountSeries = (categoryName, items, isSnapshot = false, globalMetrics = null) => {
  const dataType = isSnapshot ? generateCumulativeDataPoints : generateMetricDataPoints;
  const dataVolumeType = isSnapshot ? generateCumulativeDataVolumeDataPoints : generateDataVolumeDataPoints;

  // If no global metrics provided, fall back to random data
  if (!globalMetrics || items.length === 0) {
          return {
        views: items.map(item => createDataSeries(
          item.id,
          item.name,
          dataType(250000, 100, 50).map((dataPoint, index) => {
            const date = generateDates()[index];
            return createDataPoint(date, dataPoint.value[1], 'number');
          }),
          'line',
          'number'
        )),
        downloads: items.map(item => createDataSeries(
          item.id,
          item.name,
          dataType(75000, 40, 20).map((dataPoint, index) => {
            const date = generateDates()[index];
            return createDataPoint(date, dataPoint.value[1], 'number');
          }),
          'line',
          'number'
        )),
        visitors: items.map(item => createDataSeries(
          item.id,
          item.name,
          dataType(200000, 80, 40).map((dataPoint, index) => {
            const date = generateDates()[index];
            return createDataPoint(date, dataPoint.value[1], 'number');
          }),
          'line',
          'number'
        )),
        dataVolume: items.map(item => createDataSeries(
          item.id,
          item.name,
          dataVolumeType(5000000000000, 200000000, 100000000).map((dataPoint, index) => {
            const date = generateDates()[index];
            return createDataPoint(date, dataPoint.value[1], 'filesize');
          }),
          'line',
          'filesize'
        ))
      };
  }

  // Generate breakdown data that sums to global totals
  const generateBreakdownData = (globalDataPoints, itemCount) => {
    const dates = generateDates();
    return dates.map((date, dateIndex) => {
      const globalValue = globalDataPoints[dateIndex]?.value?.[1] || 0;

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
  const viewsDistribution = generateBreakdownData(globalViews, items.length);
  const downloadsDistribution = generateBreakdownData(globalDownloads, items.length);
  const visitorsDistribution = generateBreakdownData(globalVisitors, items.length);
  const dataVolumeDistribution = generateBreakdownData(globalDataVolume, items.length);

  return {
    views: items.map((item, itemIndex) => {
      const dataPoints = viewsDistribution.map((distribution, dateIndex) => {
        const date = generateDates()[dateIndex];
        const value = distribution[itemIndex] || 0;
        return createDataPoint(date, value, 'number');
      });
      return createDataSeries(item.id, item.name, dataPoints, 'line', 'number');
    }),
    downloads: items.map((item, itemIndex) => {
      const dataPoints = downloadsDistribution.map((distribution, dateIndex) => {
        const date = generateDates()[dateIndex];
        const value = distribution[itemIndex] || 0;
        return createDataPoint(date, value, 'number');
      });
      return createDataSeries(item.id, item.name, dataPoints, 'line', 'number');
    }),
    visitors: items.map((item, itemIndex) => {
      const dataPoints = visitorsDistribution.map((distribution, dateIndex) => {
        const date = generateDates()[dateIndex];
        const value = distribution[itemIndex] || 0;
        return createDataPoint(date, value, 'number');
      });
      return createDataSeries(item.id, item.name, dataPoints, 'line', 'number');
    }),
    dataVolume: items.map((item, itemIndex) => {
      const dataPoints = dataVolumeDistribution.map((distribution, dateIndex) => {
        const date = generateDates()[dateIndex];
        const value = distribution[itemIndex] || 0;
        return createDataPoint(date, value, 'filesize');
      });
      return createDataSeries(item.id, item.name, dataPoints, 'line', 'filesize');
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
const testStatsData = {
  // Record Delta Data
  recordDeltaDataCreated: (() => {
    const globalMetrics = createRecordMetrics(false);
    return {
      global: globalMetrics,
      byFilePresence: createFilePresenceMetrics(false),
      resourceTypes: createSubcountSeries('resourceTypes', resourceTypesItems, false, globalMetrics),
      accessStatuses: createSubcountSeries('accessStatuses', accessStatusesItems, false, globalMetrics),
      languages: createSubcountSeries('languages', languagesItems, false, globalMetrics),
      affiliations: createSubcountSeries('affiliations', affiliationsItems, false, globalMetrics),
      funders: createSubcountSeries('funders', fundersItems, false, globalMetrics),
      subjects: createSubcountSeries('subjects', subjectsItems, false, globalMetrics),
      publishers: createSubcountSeries('publishers', publishersItems, false, globalMetrics),
      periodicals: createSubcountSeries('periodicals', [], false, globalMetrics),
      rights: createSubcountSeries('rights', rightsItems, false, globalMetrics),
      fileTypes: createSubcountSeries('fileTypes', fileTypesItems, false, globalMetrics)
    };
  })(),

  recordDeltaDataAdded: (() => {
    const globalMetrics = createRecordMetrics(false);
    return {
      global: globalMetrics,
      byFilePresence: createFilePresenceMetrics(false),
      resourceTypes: createSubcountSeries('resourceTypes', resourceTypesItems, false, globalMetrics),
      accessStatuses: createSubcountSeries('accessStatuses', accessStatusesItems, false, globalMetrics),
      languages: createSubcountSeries('languages', languagesItems, false, globalMetrics),
      affiliations: createSubcountSeries('affiliations', affiliationsItems, false, globalMetrics),
      funders: createSubcountSeries('funders', fundersItems, false, globalMetrics),
      subjects: createSubcountSeries('subjects', subjectsItems, false, globalMetrics),
      publishers: createSubcountSeries('publishers', publishersItems, false, globalMetrics),
      periodicals: createSubcountSeries('periodicals', [], false, globalMetrics),
      rights: createSubcountSeries('rights', rightsItems, false, globalMetrics),
      fileTypes: createSubcountSeries('fileTypes', fileTypesItems, false, globalMetrics)
    };
  })(),

  recordDeltaDataPublished: (() => {
    const globalMetrics = createRecordMetrics(false);
    return {
      global: globalMetrics,
      byFilePresence: createFilePresenceMetrics(false),
      resourceTypes: createSubcountSeries('resourceTypes', resourceTypesItems, false, globalMetrics),
      accessStatuses: createSubcountSeries('accessStatuses', accessStatusesItems, false, globalMetrics),
      languages: createSubcountSeries('languages', languagesItems, false, globalMetrics),
      affiliations: createSubcountSeries('affiliations', affiliationsItems, false, globalMetrics),
      funders: createSubcountSeries('funders', fundersItems, false, globalMetrics),
      subjects: createSubcountSeries('subjects', subjectsItems, false, globalMetrics),
      publishers: createSubcountSeries('publishers', publishersItems, false, globalMetrics),
      periodicals: createSubcountSeries('periodicals', [], false, globalMetrics),
      rights: createSubcountSeries('rights', rightsItems, false, globalMetrics),
      fileTypes: createSubcountSeries('fileTypes', fileTypesItems, false, globalMetrics)
    };
  })(),

  // Record Snapshot Data
  recordSnapshotDataCreated: (() => {
    const globalMetrics = createRecordMetrics(true);
    return {
      global: globalMetrics,
      byFilePresence: createFilePresenceMetrics(true),
      resourceTypes: createSubcountSeries('resourceTypes', resourceTypesItems, true, globalMetrics),
      accessStatuses: createSubcountSeries('accessStatuses', accessStatusesItems, true, globalMetrics),
      languages: createSubcountSeries('languages', languagesItems, true, globalMetrics),
      affiliations: createSubcountSeries('affiliations', affiliationsItems, true, globalMetrics),
      funders: createSubcountSeries('funders', fundersItems, true, globalMetrics),
      subjects: createSubcountSeries('subjects', subjectsItems, true, globalMetrics),
      publishers: createSubcountSeries('publishers', publishersItems, true, globalMetrics),
      periodicals: createSubcountSeries('periodicals', [], true, globalMetrics),
      rights: createSubcountSeries('rights', rightsItems, true, globalMetrics),
      fileTypes: createSubcountSeries('fileTypes', fileTypesItems, true, globalMetrics)
    };
  })(),

  recordSnapshotDataAdded: (() => {
    const globalMetrics = createRecordMetrics(true);
    return {
      global: globalMetrics,
      byFilePresence: createFilePresenceMetrics(true),
      resourceTypes: createSubcountSeries('resourceTypes', resourceTypesItems, true, globalMetrics),
      accessStatuses: createSubcountSeries('accessStatuses', accessStatusesItems, true, globalMetrics),
      languages: createSubcountSeries('languages', languagesItems, true, globalMetrics),
      affiliations: createSubcountSeries('affiliations', affiliationsItems, true, globalMetrics),
      funders: createSubcountSeries('funders', fundersItems, true, globalMetrics),
      subjects: createSubcountSeries('subjects', subjectsItems, true, globalMetrics),
      publishers: createSubcountSeries('publishers', publishersItems, true, globalMetrics),
      periodicals: createSubcountSeries('periodicals', [], true, globalMetrics),
      rights: createSubcountSeries('rights', rightsItems, true, globalMetrics),
      fileTypes: createSubcountSeries('fileTypes', fileTypesItems, true, globalMetrics)
    };
  })(),

  recordSnapshotDataPublished: (() => {
    const globalMetrics = createRecordMetrics(true);
    return {
      global: globalMetrics,
      byFilePresence: createFilePresenceMetrics(true),
      resourceTypes: createSubcountSeries('resourceTypes', resourceTypesItems, true, globalMetrics),
      accessStatuses: createSubcountSeries('accessStatuses', accessStatusesItems, true, globalMetrics),
      languages: createSubcountSeries('languages', languagesItems, true, globalMetrics),
      affiliations: createSubcountSeries('affiliations', affiliationsItems, true, globalMetrics),
      funders: createSubcountSeries('funders', fundersItems, true, globalMetrics),
      subjects: createSubcountSeries('subjects', subjectsItems, true, globalMetrics),
      publishers: createSubcountSeries('publishers', publishersItems, true, globalMetrics),
      periodicals: createSubcountSeries('periodicals', [], true, globalMetrics),
      rights: createSubcountSeries('rights', rightsItems, true, globalMetrics),
      fileTypes: createSubcountSeries('fileTypes', fileTypesItems, true, globalMetrics)
    };
  })(),

  // Usage Delta Data
  usageDeltaData: (() => {
    const globalMetrics = createUsageMetrics(false);
    return {
      global: globalMetrics,
      byAccessStatus: createUsageSubcountSeries('byAccessStatus', accessStatusesItems, false, globalMetrics),
      byFileTypes: createUsageSubcountSeries('byFileTypes', fileTypesItems, false, globalMetrics),
      byLanguages: createUsageSubcountSeries('byLanguages', languagesItems, false, globalMetrics),
      byResourceTypes: createUsageSubcountSeries('byResourceTypes', resourceTypesItems, false, globalMetrics),
      bySubjects: createUsageSubcountSeries('bySubjects', subjectsItems, false, globalMetrics),
      byPublishers: createUsageSubcountSeries('byPublishers', publishersItems, false, globalMetrics),
      byRights: createUsageSubcountSeries('byRights', rightsItems, false, globalMetrics),
      byCountries: createUsageSubcountSeries('byCountries', countriesItems, false, globalMetrics),
      byReferrers: createUsageSubcountSeries('byReferrers', referrersItems, false, globalMetrics),
      byAffiliations: createUsageSubcountSeries('byAffiliations', affiliationsItems, false, globalMetrics)
    };
  })(),

  // Usage Snapshot Data
  usageSnapshotData: (() => {
    const globalMetrics = createUsageMetrics(true);
    return {
      global: globalMetrics,
      byAccessStatus: createUsageSubcountSeries('byAccessStatus', accessStatusesItems, true, globalMetrics),
      byFileTypes: createUsageSubcountSeries('byFileTypes', fileTypesItems, true, globalMetrics),
      byLanguages: createUsageSubcountSeries('byLanguages', languagesItems, true, globalMetrics),
      byResourceTypes: createUsageSubcountSeries('byResourceTypes', resourceTypesItems, true, globalMetrics),
      bySubjects: createUsageSubcountSeries('bySubjects', subjectsItems, true, globalMetrics),
      byPublishers: createUsageSubcountSeries('byPublishers', publishersItems, true, globalMetrics),
      byRights: createUsageSubcountSeries('byRights', rightsItems, true, globalMetrics),
      byCountries: createUsageSubcountSeries('byCountries', countriesItems, true, globalMetrics),
      byReferrers: createUsageSubcountSeries('byReferrers', referrersItems, true, globalMetrics),
      byAffiliations: createUsageSubcountSeries('byAffiliations', affiliationsItems, true, globalMetrics),
      topCountriesByView: createUsageSubcountSeries('topCountriesByView', countriesItems, true, globalMetrics),
      topCountriesByDownload: createUsageSubcountSeries('topCountriesByDownload', countriesItems, true, globalMetrics),
      topSubjectsByView: createUsageSubcountSeries('topSubjectsByView', subjectsItems, true, globalMetrics),
      topSubjectsByDownload: createUsageSubcountSeries('topSubjectsByDownload', subjectsItems, true, globalMetrics),
      topPublishersByView: createUsageSubcountSeries('topPublishersByView', publishersItems, true, globalMetrics),
      topPublishersByDownload: createUsageSubcountSeries('topPublishersByDownload', publishersItems, true, globalMetrics),
      topRightsByView: createUsageSubcountSeries('topRightsByView', rightsItems, true, globalMetrics),
      topRightsByDownload: createUsageSubcountSeries('topRightsByDownload', rightsItems, true, globalMetrics),
      topReferrersByView: createUsageSubcountSeries('topReferrersByView', referrersItems, true, globalMetrics)
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
};

export { testStatsData, createDataPoint, createDataSeries, createGlobalSeries, sampleRecords };