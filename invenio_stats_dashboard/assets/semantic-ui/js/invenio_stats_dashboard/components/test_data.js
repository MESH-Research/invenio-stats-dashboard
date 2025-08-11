import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import React from "react";

// Cache the dates array to avoid regenerating it hundreds of times
let cachedDates = null;

// Generate dates for multiple years
const generateDates = () => {
  if (cachedDates === null) {
    const dates = [];
    const today = new Date();
    const startDate = new Date(today.getFullYear() - 3, 0, 1); // Start from 3 years ago
    const endDate = today;

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
    const dailyValue = Math.floor(baseValue + (Math.random() * variance));
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
const generateCumulativeDataPoints = (baseValue, dailyBaseValue, dailyVariance) => {
  return generateDataPoints(dailyBaseValue, dailyVariance, baseValue, true, 'number');
};

// Generate data volume data points (filesize type)
const generateDataVolumeDataPoints = (baseValue, variance, startValue = 0) => {
  return generateDataPoints(baseValue, variance, startValue, false, 'filesize');
};

// Generate cumulative data volume data points
const generateCumulativeDataVolumeDataPoints = (baseValue, dailyBaseValue, dailyVariance) => {
  return generateDataPoints(dailyBaseValue, dailyVariance, baseValue, true, 'filesize');
};

// Create record metrics structure
const createRecordMetrics = (isSnapshot = false) => {
  const dataType = isSnapshot ? generateCumulativeDataPoints : generateMetricDataPoints;
  const dataVolumeType = isSnapshot ? generateCumulativeDataVolumeDataPoints : generateDataVolumeDataPoints;

  return {
    records: [createGlobalSeries(dataType(25, 20, 12500), 'bar', 'number')],
    parents: [createGlobalSeries(dataType(25, 20, 12500), 'bar', 'number')],
    uploaders: [createGlobalSeries(dataType(12, 13, 2500), 'bar', 'number')],
    fileCount: [createGlobalSeries(dataType(50, 40, 25000), 'bar', 'number')],
    dataVolume: [createGlobalSeries(dataVolumeType(50000000, 100000000, 2500000000000), 'bar', 'filesize')]
  };
};

// Create usage metrics structure
const createUsageMetrics = (isSnapshot = false) => {
  const dataType = isSnapshot ? generateCumulativeDataPoints : generateMetricDataPoints;
  const dataVolumeType = isSnapshot ? generateCumulativeDataVolumeDataPoints : generateDataVolumeDataPoints;

  return {
    views: [createGlobalSeries(dataType(100, 200, 250000), 'bar', 'number')],
    downloads: [createGlobalSeries(dataType(40, 50, 75000), 'bar', 'number')],
    visitors: [createGlobalSeries(dataType(80, 150, 200000), 'bar', 'number')],
    dataVolume: [createGlobalSeries(dataVolumeType(200000000, 300000000, 5000000000000), 'bar', 'filesize')]
  };
};

// Create subcount series for categories
const createSubcountSeries = (categoryName, items, isSnapshot = false) => {
  const dataType = isSnapshot ? generateCumulativeDataPoints : generateMetricDataPoints;
  const dataVolumeType = isSnapshot ? generateCumulativeDataVolumeDataPoints : generateDataVolumeDataPoints;

  return {
    records: items.map(item => createDataSeries(
      item.id,
      item.name,
      dataType(25, 20, 12500),
      'line',
      'number'
    )),
    parents: items.map(item => createDataSeries(
      item.id,
      item.name,
      dataType(25, 20, 12500),
      'line',
      'number'
    )),
    uploaders: items.map(item => createDataSeries(
      item.id,
      item.name,
      dataType(12, 13, 2500),
      'line',
      'number'
    )),
    fileCount: items.map(item => createDataSeries(
      item.id,
      item.name,
      dataType(50, 40, 25000),
      'line',
      'number'
    )),
    dataVolume: items.map(item => createDataSeries(
      item.id,
      item.name,
      dataVolumeType(50000000, 100000000, 2500000000000),
      'line',
      'filesize'
    ))
  };
};

// Create usage subcount series for categories
const createUsageSubcountSeries = (categoryName, items, isSnapshot = false) => {
  const dataType = isSnapshot ? generateCumulativeDataPoints : generateMetricDataPoints;
  const dataVolumeType = isSnapshot ? generateCumulativeDataVolumeDataPoints : generateDataVolumeDataPoints;

  return {
    views: items.map(item => createDataSeries(
      item.id,
      item.name,
      dataType(100, 200, 250000),
      'line',
      'number'
    )),
    downloads: items.map(item => createDataSeries(
      item.id,
      item.name,
      dataType(40, 50, 75000),
      'line',
      'number'
    )),
    visitors: items.map(item => createDataSeries(
      item.id,
      item.name,
      dataType(80, 150, 200000),
      'line',
      'number'
    )),
    dataVolume: items.map(item => createDataSeries(
      item.id,
      item.name,
      dataVolumeType(200000000, 300000000, 5000000000000),
      'line',
      'filesize'
    ))
  };
};

// Sample items for different categories
const resourceTypeItems = [
  { id: 'dataset', name: 'Dataset' },
  { id: 'software', name: 'Software' },
  { id: 'research_paper', name: 'Research Paper' },
  { id: 'other', name: 'Other' }
];

const accessStatusItems = [
  { id: 'open', name: 'Open Access' },
  { id: 'embargoed', name: 'Embargoed' },
  { id: 'restricted', name: 'Restricted' },
  { id: 'metadata-only', name: 'Metadata Only' }
];

const languageItems = [
  { id: 'eng', name: 'English' },
  { id: 'spa', name: 'Spanish' },
  { id: 'fra', name: 'French' },
  { id: 'deu', name: 'German' }
];

const affiliationItems = [
  { id: 'uc-berkeley', name: 'University of California, Berkeley' },
  { id: 'mit', name: 'Massachusetts Institute of Technology' },
  { id: 'stanford', name: 'Stanford University' },
  { id: 'harvard', name: 'Harvard University' }
];

const funderItems = [
  { id: 'nsf', name: 'National Science Foundation' },
  { id: 'nih', name: 'National Institutes of Health' },
  { id: 'erc', name: 'European Research Council' },
  { id: 'wellcome', name: 'Wellcome Trust' }
];

const subjectItems = [
  { id: 'computer_science', name: 'Computer Science' },
  { id: 'environmental_science', name: 'Environmental Science' },
  { id: 'biology', name: 'Biology' },
  { id: 'physics', name: 'Physics' }
];

const publisherItems = [
  { id: 'springer', name: 'Springer' },
  { id: 'elsevier', name: 'Elsevier' },
  { id: 'wiley', name: 'Wiley' },
  { id: 'nature', name: 'Nature' }
];

const licenseItems = [
  { id: 'cc-by-4.0', name: 'Creative Commons Attribution 4.0 International' },
  { id: 'cc-by-sa-4.0', name: 'Creative Commons Attribution-ShareAlike 4.0 International' },
  { id: 'cc-by-nc-4.0', name: 'Creative Commons Attribution-NonCommercial 4.0 International' },
  { id: 'cc0-1.0', name: 'Creative Commons Zero 1.0 Universal' }
];

const fileTypeItems = [
  { id: 'pdf', name: 'PDF' },
  { id: 'csv', name: 'CSV' },
  { id: 'json', name: 'JSON' },
  { id: 'zip', name: 'ZIP' }
];

const countryItems = [
  { id: 'us', name: 'United States' },
  { id: 'gb', name: 'United Kingdom' },
  { id: 'de', name: 'Germany' },
  { id: 'fr', name: 'France' }
];

const referrerItems = [
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
  recordDeltaDataCreated: {
    global: createRecordMetrics(false),
    byFilePresence: createRecordMetrics(false),
    resourceTypes: createSubcountSeries('resourceTypes', resourceTypeItems, false),
    accessStatus: createSubcountSeries('accessStatus', accessStatusItems, false),
    languages: createSubcountSeries('languages', languageItems, false),
    affiliations: createSubcountSeries('affiliations', affiliationItems, false),
    funders: createSubcountSeries('funders', funderItems, false),
    subjects: createSubcountSeries('subjects', subjectItems, false),
    publishers: createSubcountSeries('publishers', publisherItems, false),
    periodicals: createSubcountSeries('periodicals', []),
    licenses: createSubcountSeries('licenses', licenseItems, false),
    fileTypes: createSubcountSeries('fileTypes', fileTypeItems, false)
  },

  recordDeltaDataAdded: {
    global: createRecordMetrics(false),
    byFilePresence: createRecordMetrics(false),
    resourceTypes: createSubcountSeries('resourceTypes', resourceTypeItems, false),
    accessStatus: createSubcountSeries('accessStatus', accessStatusItems, false),
    languages: createSubcountSeries('languages', languageItems, false),
    affiliations: createSubcountSeries('affiliations', affiliationItems, false),
    funders: createSubcountSeries('funders', funderItems, false),
    subjects: createSubcountSeries('subjects', subjectItems, false),
    publishers: createSubcountSeries('publishers', publisherItems, false),
    periodicals: createSubcountSeries('periodicals', []),
    licenses: createSubcountSeries('licenses', licenseItems, false),
    fileTypes: createSubcountSeries('fileTypes', fileTypeItems, false)
  },

  recordDeltaDataPublished: {
    global: createRecordMetrics(false),
    byFilePresence: createRecordMetrics(false),
    resourceTypes: createSubcountSeries('resourceTypes', resourceTypeItems, false),
    accessStatus: createSubcountSeries('accessStatus', accessStatusItems, false),
    languages: createSubcountSeries('languages', languageItems, false),
    affiliations: createSubcountSeries('affiliations', affiliationItems, false),
    funders: createSubcountSeries('funders', funderItems, false),
    subjects: createSubcountSeries('subjects', subjectItems, false),
    publishers: createSubcountSeries('publishers', publisherItems, false),
    periodicals: createSubcountSeries('periodicals', []),
    licenses: createSubcountSeries('licenses', licenseItems, false),
    fileTypes: createSubcountSeries('fileTypes', fileTypeItems, false)
  },

  // Record Snapshot Data
  recordSnapshotDataCreated: {
    global: createRecordMetrics(true),
    byFilePresence: createRecordMetrics(true),
    resourceTypes: createSubcountSeries('resourceTypes', resourceTypeItems, true),
    accessStatus: createSubcountSeries('accessStatus', accessStatusItems, true),
    languages: createSubcountSeries('languages', languageItems, true),
    affiliations: createSubcountSeries('affiliations', affiliationItems, true),
    funders: createSubcountSeries('funders', funderItems, true),
    subjects: createSubcountSeries('subjects', subjectItems, true),
    publishers: createSubcountSeries('publishers', publisherItems, true),
    periodicals: createSubcountSeries('periodicals', []),
    licenses: createSubcountSeries('licenses', licenseItems, true),
    fileTypes: createSubcountSeries('fileTypes', fileTypeItems, true)
  },

  recordSnapshotDataAdded: {
    global: createRecordMetrics(true),
    byFilePresence: createRecordMetrics(true),
    resourceTypes: createSubcountSeries('resourceTypes', resourceTypeItems, true),
    accessStatus: createSubcountSeries('accessStatus', accessStatusItems, true),
    languages: createSubcountSeries('languages', languageItems, true),
    affiliations: createSubcountSeries('affiliations', affiliationItems, true),
    funders: createSubcountSeries('funders', funderItems, true),
    subjects: createSubcountSeries('subjects', subjectItems, true),
    publishers: createSubcountSeries('publishers', publisherItems, true),
    periodicals: createSubcountSeries('periodicals', []),
    licenses: createSubcountSeries('licenses', licenseItems, true),
    fileTypes: createSubcountSeries('fileTypes', fileTypeItems, true)
  },

  recordSnapshotDataPublished: {
    global: createRecordMetrics(true),
    byFilePresence: createRecordMetrics(true),
    resourceTypes: createSubcountSeries('resourceTypes', resourceTypeItems, true),
    accessStatus: createSubcountSeries('accessStatus', accessStatusItems, true),
    languages: createSubcountSeries('languages', languageItems, true),
    affiliations: createSubcountSeries('affiliations', affiliationItems, true),
    funders: createSubcountSeries('funders', funderItems, true),
    subjects: createSubcountSeries('subjects', subjectItems, true),
    publishers: createSubcountSeries('publishers', publisherItems, true),
    periodicals: createSubcountSeries('periodicals', []),
    licenses: createSubcountSeries('licenses', licenseItems, true),
    fileTypes: createSubcountSeries('fileTypes', fileTypeItems, true)
  },

  // Usage Delta Data
  usageDeltaData: {
    global: createUsageMetrics(false),
    byFilePresence: createUsageMetrics(false),
    byAccessStatus: createUsageSubcountSeries('byAccessStatus', accessStatusItems, false),
    byFileTypes: createUsageSubcountSeries('byFileTypes', fileTypeItems, false),
    byLanguages: createUsageSubcountSeries('byLanguages', languageItems, false),
    byResourceTypes: createUsageSubcountSeries('byResourceTypes', resourceTypeItems, false),
    bySubjects: createUsageSubcountSeries('bySubjects', subjectItems, false),
    byPublishers: createUsageSubcountSeries('byPublishers', publisherItems, false),
    byLicenses: createUsageSubcountSeries('byLicenses', licenseItems, false),
    byCountries: createUsageSubcountSeries('byCountries', countryItems, false),
    byReferrers: createUsageSubcountSeries('byReferrers', referrerItems, false),
    byAffiliations: createUsageSubcountSeries('byAffiliations', affiliationItems, false)
  },

  // Usage Snapshot Data
  usageSnapshotData: {
    global: createUsageMetrics(true),
    byFilePresence: createUsageMetrics(true),
    byAccessStatus: createUsageSubcountSeries('byAccessStatus', accessStatusItems, true),
    byFileTypes: createUsageSubcountSeries('byFileTypes', fileTypeItems, true),
    byLanguages: createUsageSubcountSeries('byLanguages', languageItems, true),
    byResourceTypes: createUsageSubcountSeries('byResourceTypes', resourceTypeItems, true),
    bySubjects: createUsageSubcountSeries('bySubjects', subjectItems, true),
    byPublishers: createUsageSubcountSeries('byPublishers', publisherItems, true),
    byLicenses: createUsageSubcountSeries('byLicenses', licenseItems, true),
    byCountries: createUsageSubcountSeries('byCountries', countryItems, true),
    byReferrers: createUsageSubcountSeries('byReferrers', referrerItems, true),
    byAffiliations: createUsageSubcountSeries('byAffiliations', affiliationItems, true),
    topCountriesByView: createUsageSubcountSeries('topCountriesByView', countryItems, true),
    topCountriesByDownload: createUsageSubcountSeries('topCountriesByDownload', countryItems, true),
    topSubjectsByView: createUsageSubcountSeries('topSubjectsByView', subjectItems, true),
    topSubjectsByDownload: createUsageSubcountSeries('topSubjectsByDownload', subjectItems, true),
    topPublishersByView: createUsageSubcountSeries('topPublishersByView', publisherItems, true),
    topPublishersByDownload: createUsageSubcountSeries('topPublishersByDownload', publisherItems, true),
    topLicensesByView: createUsageSubcountSeries('topLicensesByView', licenseItems, true),
    topLicensesByDownload: createUsageSubcountSeries('topLicensesByDownload', licenseItems, true),
    topReferrersByView: createUsageSubcountSeries('topReferrersByView', referrerItems, true)
  },

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