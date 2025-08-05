import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { readableGranularDate, createUTCDate } from "../utils/dates";

/**
 * Create a data point object for charting.
 *
 * @param {Date|string} date - Date value
 * @param {number} value - Numeric value
 * @param {string} [valueType='number'] - Type of value ('number', 'filesize', etc.)
 * @returns {DataPoint} Chart data point object
 */
const createDataPoint = (date, value, valueType = 'number') => {
  const dateObj = createUTCDate(date);

  return {
    value: [dateObj, value],
    readableDate: readableGranularDate(dateObj, 'day'),
    valueType
  };
};

/**
 * Create an array of DataSeries objects for byFilePresence data, optionally populating with data points.
 *
 * @param {string[]} seriesNames - Array of series names (e.g., ['withFiles', 'withoutFiles'])
 * @param {Object[]} [dataPointsArray] - Array of objects mapping series name to value for each date, e.g.:
 *    [{date: '2024-01-01', withFiles: 5, withoutFiles: 2}, ...]
 * @param {string} [type='line'] - Chart type for all series
 * @param {string} [valueType='number'] - Value type for all series
 * @returns {DataSeries[]} Array of DataSeries objects
 */
const createDataSeriesArray = (seriesNames, dataPointsArray = [], type = 'line', valueType = 'number') => {
  const seriesArray = seriesNames.map(name => ({
    id: name,
    name,
    data: [],
    type,
    valueType
  }));

  if (dataPointsArray.length > 0) {
    dataPointsArray.forEach(pointObj => {
      const { date, ...values } = pointObj;
      for (const name of seriesNames) {
        if (name in values) {
          const series = seriesArray.find(s => s.name === name);
          if (series) {
            series.data.push(createDataPoint(date, values[name], valueType));
          }
        }
      }
    });
  }

  return seriesArray;
};

/**
 * Create an array of DataSeries objects from raw subcount data.
 *
 * @param {Array} subcountItems - Array of subcount items with id and optional label
 * @param {Object[]} [dataPointsArray] - Array of objects mapping subcount id to value for each date
 * @param {string} [type='line'] - Chart type for all series
 * @param {string} [valueType='number'] - Value type for all series
 * @returns {DataSeries[]} Array of DataSeries objects
 */
const createDataSeriesFromItems = (subcountItems, dataPointsArray = [], type = 'line', valueType = 'number') => {
  const seriesArray = subcountItems.map(item => ({
    id: item.id,
    name: item.label || item.id,
    data: [],
    type,
    valueType
  }));

  if (dataPointsArray.length > 0) {
    dataPointsArray.forEach(pointObj => {
      const { date, ...values } = pointObj;
      for (const series of seriesArray) {
        if (series.id in values) {
          series.data.push(createDataPoint(date, values[series.id], valueType));
        }
      }
    });
  }

  return seriesArray;
};

/**
 * Create a DataSeries object from a DataPoint array for global data.
 *
 * @param {DataPoint[]} dataPoints - Array of chart data points
 * @param {string} [type='line'] - Chart type
 * @param {string} [valueType='number'] - Value type
 * @returns {DataSeries} DataSeries object with id and name "global"
 */
const createGlobalSeries = (dataPoints, type = 'line', valueType = 'number') => ({
  id: "global",
  name: "Global",
  data: dataPoints,
  type,
  valueType
});

/**
 * Type definitions for data transformer return objects
 *
 * @typedef {Object} DataPoint
 * @property {[Date, number]} value - [date, value] array for chart
 * @property {string} readableDate - Formatted date string
 * @property {string} valueType - Type of value ('number', 'filesize', etc.)
 *
 * @typedef {Object} DataSeries
 * @property {string} id - Unique identifier for the series
 * @property {string} name - Series name (display name, can be label or id)
 * @property {DataPoint[]} data - Array of chart data points
 * @property {string} [type='line'] - Chart type ('line', 'bar', etc.)
 * @property {string} [valueType='number'] - Type of value ('number', 'filesize', etc.)
 *
 * @typedef {Object} RecordMetrics
 * @property {DataSeries[]} records - Record count series
 * @property {DataSeries[]} parents - Parent count series
 * @property {DataSeries[]} uploaders - Uploader count series
 * @property {DataSeries[]} fileCount - File count series
 * @property {DataSeries[]} dataVolume - Data volume series
 *
 * @typedef {Object} UsageMetrics
 * @property {DataSeries[]} views - View count series
 * @property {DataSeries[]} downloads - Download count series
 * @property {DataSeries[]} visitors - Visitor count series
 * @property {DataSeries[]} dataVolume - Data volume series
 *
 * @typedef {Object} RecordDeltaData
 * @property {RecordMetrics} global - Global record metrics
 * @property {RecordMetrics} byFilePresence - Record metrics by file presence
 * @property {RecordMetrics} resourceTypes
 * @property {RecordMetrics} accessStatus
 * @property {RecordMetrics} languages
 * @property {RecordMetrics} affiliations
 * @property {RecordMetrics} funders
 * @property {RecordMetrics} subjects
 * @property {RecordMetrics} publishers
 * @property {RecordMetrics} periodicals
 * @property {RecordMetrics} licenses
 * @property {RecordMetrics} fileTypes
 *
 * @typedef {Object} RecordSnapshotData
 * @property {RecordMetrics} global - Global record metrics
 * @property {RecordMetrics} byFilePresence - Record metrics by file presence
 * @property {RecordMetrics} resourceTypes
 * @property {RecordMetrics} accessStatus
 * @property {RecordMetrics} languages
 * @property {RecordMetrics} affiliations
 * @property {RecordMetrics} funders
 * @property {RecordMetrics} subjects
 * @property {RecordMetrics} publishers
 * @property {RecordMetrics} periodicals
 * @property {RecordMetrics} licenses
 * @property {RecordMetrics} fileTypes
 *
 * @typedef {Object} UsageDeltaData
 * @property {UsageMetrics} global - Global usage metrics
 * @property {UsageMetrics} byFilePresence - Usage metrics by file presence
 * @property {UsageMetrics} byAccessStatus
 * @property {UsageMetrics} byFileTypes
 * @property {UsageMetrics} byLanguages
 * @property {UsageMetrics} byResourceTypes
 * @property {UsageMetrics} bySubjects
 * @property {UsageMetrics} byPublishers
 * @property {UsageMetrics} byLicenses
 * @property {UsageMetrics} byCountries
 * @property {UsageMetrics} byReferrers
 * @property {UsageMetrics} byAffiliations
 *
 * @typedef {Object} UsageSnapshotData
 * @property {UsageMetrics} global - Global usage metrics
 * @property {UsageMetrics} byFilePresence - Usage metrics by file presence
 * @property {UsageMetrics} byAccessStatus
 * @property {UsageMetrics} byFileTypes
 * @property {UsageMetrics} byLanguages
 * @property {UsageMetrics} byResourceTypes
 * @property {UsageMetrics} bySubjects
 * @property {UsageMetrics} byPublishers
 * @property {UsageMetrics} byLicenses
 * @property {UsageMetrics} byCountries
 * @property {UsageMetrics} byReferrers
 * @property {UsageMetrics} byAffiliations
 * @property {UsageMetrics} topCountriesByView
 * @property {UsageMetrics} topCountriesByDownload
 * @property {UsageMetrics} topSubjectsByView
 * @property {UsageMetrics} topSubjectsByDownload
 * @property {UsageMetrics} topPublishersByView
 * @property {UsageMetrics} topPublishersByDownload
 * @property {UsageMetrics} topLicensesByView
 * @property {UsageMetrics} topLicensesByDownload
 * @property {UsageMetrics} topReferrersByView
 * @property {UsageMetrics} topReferrersByDownload
 * @property {UsageMetrics} topAffiliationsByView
 * @property {UsageMetrics} topAffiliationsByDownload
 *
 * @typedef {Object} TransformedApiData
 * @property {RecordDeltaData} recordDeltaDataCreated - Record creation counts
 * @property {RecordDeltaData} recordDeltaDataAdded - Record addition counts
 * @property {RecordDeltaData} recordDeltaDataPublished - Record publication counts
 * @property {RecordSnapshotData} recordSnapshotDataCreated - Cumulative record counts
 * @property {RecordSnapshotData} recordSnapshotDataAdded - Cumulative record counts
 * @property {RecordSnapshotData} recordSnapshotDataPublished - Cumulative record counts
 * @property {UsageDeltaData} usageDeltaData - Usage counts
 * @property {UsageSnapshotData} usageSnapshotData - Cumulative usage counts
 */

/**
 * Transform daily record delta aggregation documents for display in the dashboard.
 *
 * @param {Array} deltaDocs - Array of daily record delta aggregation documents
 *
 * @returns {RecordDeltaData} Transformed data with time series metrics organized by category
 */
const transformRecordDeltaData = (deltaDocs) => {

  const deltaData = {
    global: {
      records: [],
      parents: [],
      uploaders: [],
      fileCount: [],
      dataVolume: [],
    },
    byFilePresence: {
      records: [],
      parents: [],
      uploaders: [],
      fileCount: [],
      dataVolume: [],
    },
    accessStatus: {
      records: [],
      parents: [],
      uploaders: [],
      fileCount: [],
      dataVolume: [],
    },
    languages: {
      records: [],
      parents: [],
      uploaders: [],
      fileCount: [],
      dataVolume: [],
    },
    affiliations: {
      records: [],
      parents: [],
      uploaders: [],
      fileCount: [],
      dataVolume: [],
    },
    funders: {
      records: [],
      parents: [],
      uploaders: [],
      fileCount: [],
      dataVolume: [],
    },
    subjects: {
      records: [],
      parents: [],
      uploaders: [],
      fileCount: [],
      dataVolume: [],
    },
    publishers: {
      records: [],
      parents: [],
      uploaders: [],
      fileCount: [],
      dataVolume: [],
    },
    periodicals: {
      records: [],
      parents: [],
      uploaders: [],
      fileCount: [],
      dataVolume: [],
    },
    licenses: {
      records: [],
      parents: [],
      uploaders: [],
      fileCount: [],
      dataVolume: [],
    },
    fileTypes: {
      records: [],
      parents: [],
      uploaders: [],
      fileCount: [],
      dataVolume: [],
    },
    resourceTypes: {
      records: [],
      parents: [],
      uploaders: [],
      fileCount: [],
      dataVolume: [],
    },
  };


  const subcountTypes = {
    'by_resource_type': 'resourceTypes',
    'by_access_status': 'accessStatus',
    'by_language': 'languages',
    'by_affiliation_creator': 'affiliations',
    'by_affiliation_contributor': 'affiliations',
    'by_funder': 'funders',
    'by_subject': 'subjects',
    'by_publisher': 'publishers',
    'by_periodical': 'periodicals',
    'by_license': 'licenses',
    'by_file_type': 'fileTypes'
  };


  const getNetCount = (item) => {
    // Handle different subcount item structures
    if (item.added && item.removed) {
      // Direct added/removed structure (like by_file_type)
      const added = (item.added.metadata_only || 0) + (item.added.with_files || 0);
      const removed = (item.removed.metadata_only || 0) + (item.removed.with_files || 0);
      return added - removed;
    } else if (item.records) {
      // Nested structure with records property
      const added = (item.records.added?.metadata_only || 0) + (item.records.added?.with_files || 0);
      const removed = (item.records.removed?.metadata_only || 0) + (item.records.removed?.with_files || 0);
      return added - removed;
    }
    return 0;
  };

  const getNetFileCount = (item) => {
    // Handle different subcount item structures
    if (item.added && item.removed) {
      // Direct added/removed structure (like by_file_type)
      // Check for both files and file_count properties
      const addedFiles = item.added.files || item.added.file_count || 0;
      const removedFiles = item.removed.files || item.removed.file_count || 0;
      return addedFiles - removedFiles;
    } else if (item.files) {
      // Nested structure with files property
      return (item.files.added?.file_count || 0) - (item.files.removed?.file_count || 0);
    }
    return 0;
  };

  const getNetDataVolume = (item) => {
    // Handle different subcount item structures
    if (item.added && item.removed) {
      // Direct added/removed structure (like by_file_type)
      return (item.added.data_volume || 0) - (item.removed.data_volume || 0);
    } else if (item.files) {
      // Nested structure with files property
      return (item.files.added?.data_volume || 0) - (item.files.removed?.data_volume || 0);
    }
    return 0;
  };

  if (deltaDocs && Array.isArray(deltaDocs)) {
    const byFilePresenceDataPoints = [];

    deltaDocs.forEach(doc => {
      const source = doc;
      const date = source.period_start.split('T')[0];

      // Accumulate global data points
      deltaData.global.records.push(createDataPoint(date, getNetCount(source.records)));
      deltaData.global.parents.push(createDataPoint(date, getNetCount(source.parents)));
      deltaData.global.uploaders.push(createDataPoint(date, source.uploaders));
      deltaData.global.fileCount.push(createDataPoint(date, getNetFileCount(source.files)));
      deltaData.global.dataVolume.push(createDataPoint(date, getNetDataVolume(source.files), 'filesize'));

      // Collect byFilePresence data points
      byFilePresenceDataPoints.push({
        date,
        withFiles: getNetCount(source.records.added),
        withoutFiles: getNetCount(source.records.removed)
      });

      // Collect subcount data points for each metric type
      Object.keys(subcountTypes).forEach(subcountType => {
        const subcountSeries = source.subcounts[subcountType];
        if (subcountSeries && subcountSeries.length > 0) {
          const targetKey = subcountTypes[subcountType];

          // Initialize data structures for each metric type
          if (!deltaData[`${targetKey}DataPoints`]) {
            deltaData[`${targetKey}DataPoints`] = {
              records: [],
              parents: [],
              uploaders: [],
              fileCount: [],
              dataVolume: []
            };
            deltaData[`${targetKey}Items`] = [];
          }

          subcountSeries.forEach(item => {
            // Store the item for later series creation
            if (!deltaData[`${targetKey}Items`].find(existing => existing.id === item.id)) {
              deltaData[`${targetKey}Items`].push(item);
            }

            // Collect data points for each metric type
            const metricTypes = ['records', 'parents', 'uploaders', 'fileCount', 'dataVolume'];
            metricTypes.forEach(metricType => {
              let value = 0;
              let valueType = 'number';

              switch (metricType) {
                case 'records':
                  value = getNetCount(item.records || item);
                  break;
                case 'parents':
                  value = getNetCount(item.parents || item);
                  break;
                case 'uploaders':
                  value = item.uploaders || 0;
                  break;
                case 'fileCount':
                  value = getNetFileCount(item.files || item);
                  break;
                case 'dataVolume':
                  value = getNetDataVolume(item.files || item);
                  valueType = 'filesize';
                  break;
              }

              // Find or create data point for this date
              let existingDataPoint = deltaData[`${targetKey}DataPoints`][metricType].find(dp => dp.date === date);
              if (!existingDataPoint) {
                existingDataPoint = { date };
                deltaData[`${targetKey}DataPoints`][metricType].push(existingDataPoint);
              }
              existingDataPoint[item.id] = value;
            });
          });
        }
      });
    });

    // Convert global DataPoint arrays to DataSeries arrays
    deltaData.global.records = [createGlobalSeries(deltaData.global.records, 'line', 'number')];
    deltaData.global.parents = [createGlobalSeries(deltaData.global.parents, 'line', 'number')];
    deltaData.global.uploaders = [createGlobalSeries(deltaData.global.uploaders, 'line', 'number')];
    deltaData.global.fileCount = [createGlobalSeries(deltaData.global.fileCount, 'line', 'number')];
    deltaData.global.dataVolume = [createGlobalSeries(deltaData.global.dataVolume, 'line', 'filesize')];

    // Create byFilePresence series for each metric type
    const byFilePresenceMetrics = ['records', 'parents', 'uploaders', 'fileCount', 'dataVolume'];
    byFilePresenceMetrics.forEach(metricType => {
      const dataPoints = byFilePresenceDataPoints.map(dp => ({
        date: dp.date,
        withFiles: dp.withFiles,
        withoutFiles: dp.withoutFiles
      }));
      deltaData.byFilePresence[metricType] = createDataSeriesArray(['withFiles', 'withoutFiles'], dataPoints);
    });

    // Create subcount series for each metric type
    Object.keys(subcountTypes).forEach(subcountType => {
      const targetKey = subcountTypes[subcountType];
      if (deltaData[`${targetKey}Items`] && deltaData[`${targetKey}DataPoints`]) {
        const metricTypes = ['records', 'parents', 'uploaders', 'fileCount', 'dataVolume'];
        metricTypes.forEach(metricType => {
          const valueType = metricType === 'dataVolume' ? 'filesize' : 'number';
          deltaData[targetKey][metricType] = createDataSeriesFromItems(
            deltaData[`${targetKey}Items`],
            deltaData[`${targetKey}DataPoints`][metricType],
            'line',
            valueType
          );
        });
        // Clean up temporary data
        delete deltaData[`${targetKey}Items`];
        delete deltaData[`${targetKey}DataPoints`];
      }
    });
  }

  return deltaData;
};

/**
 * Transform daily record snapshot aggregation documents for display in the dashboard.
 *
 * @param {Array} snapshotDocs - Array of daily record snapshot aggregation documents
 *
 * @returns {RecordSnapshotData} Transformed data with cumulative time series metrics organized by category
 */
const transformRecordSnapshotData = (snapshotDocs) => {

  const snapshotData = {
    global: {
      records: [],
      parents: [],
      uploaders: [],
      fileCount: [],
      dataVolume: [],
    },
    byFilePresence: {
      records: [],
      parents: [],
      uploaders: [],
      fileCount: [],
      dataVolume: [],
    },
    accessStatus: {
      records: [],
      parents: [],
      uploaders: [],
      fileCount: [],
      dataVolume: [],
    },
    languages: {
      records: [],
      parents: [],
      uploaders: [],
      fileCount: [],
      dataVolume: [],
    },
    affiliations: {
      records: [],
      parents: [],
      uploaders: [],
      fileCount: [],
      dataVolume: [],
    },
    funders: {
      records: [],
      parents: [],
      uploaders: [],
      fileCount: [],
      dataVolume: [],
    },
    subjects: {
      records: [],
      parents: [],
      uploaders: [],
      fileCount: [],
      dataVolume: [],
    },
    publishers: {
      records: [],
      parents: [],
      uploaders: [],
      fileCount: [],
      dataVolume: [],
    },
    periodicals: {
      records: [],
      parents: [],
      uploaders: [],
      fileCount: [],
      dataVolume: [],
    },
    licenses: {
      records: [],
      parents: [],
      uploaders: [],
      fileCount: [],
      dataVolume: [],
    },
    fileTypes: {
      records: [],
      parents: [],
      uploaders: [],
      fileCount: [],
      dataVolume: [],
    },
    resourceTypes: {
      records: [],
      parents: [],
      uploaders: [],
      fileCount: [],
      dataVolume: [],
    },
  };

  const subcountTypes = {
    'all_resource_types': 'resourceTypes',
    'all_access_status': 'accessStatus',
    'all_languages': 'languages',
    'top_affiliations_creator': 'affiliations',
    'top_affiliations_contributor': 'affiliations',
    'top_funders': 'funders',
    'top_subjects': 'subjects',
    'top_publishers': 'publishers',
    'top_periodicals': 'periodicals',
    'all_licenses': 'licenses',
    'all_file_types': 'fileTypes'
  };

  const getTotalCount = (item) => {
    if (!item) return 0;
    return (item.metadata_only || 0) + (item.with_files || 0);
  };

  const getTotalFileCount = (item) => {
    if (!item) return 0;
    return item.file_count || 0;
  };

  const getTotalDataVolume = (item) => {
    if (!item) return 0;
    return item.data_volume || 0;
  };

  if (snapshotDocs && Array.isArray(snapshotDocs)) {
    const byFilePresenceDataPoints = [];

    snapshotDocs.forEach(doc => {
      const source = doc;
      const date = source.snapshot_date.split('T')[0];

      // Accumulate global data points
      snapshotData.global.records.push(createDataPoint(date, getTotalCount(source.total_records)));
      snapshotData.global.parents.push(createDataPoint(date, getTotalCount(source.total_parents)));
      snapshotData.global.uploaders.push(createDataPoint(date, source.total_uploaders));
      snapshotData.global.fileCount.push(createDataPoint(date, getTotalFileCount(source.total_files)));
      snapshotData.global.dataVolume.push(createDataPoint(date, getTotalDataVolume(source.total_files), 'filesize'));

      // Collect byFilePresence data points
      byFilePresenceDataPoints.push({
        date,
        withFiles: source.total_records.with_files,
        withoutFiles: source.total_records.metadata_only
      });

      // Collect subcount data points for each metric type
      Object.keys(subcountTypes).forEach(subcountType => {
        const subcountSeries = source.subcounts[subcountType];
        if (subcountSeries && subcountSeries.length > 0) {
          const targetKey = subcountTypes[subcountType];

          // Initialize data structures for each metric type
          if (!snapshotData[`${targetKey}DataPoints`]) {
            snapshotData[`${targetKey}DataPoints`] = {
              records: [],
              parents: [],
              uploaders: [],
              fileCount: [],
              dataVolume: []
            };
            snapshotData[`${targetKey}Items`] = [];
          }

          subcountSeries.forEach(item => {
            // Store the item for later series creation
            if (!snapshotData[`${targetKey}Items`].find(existing => existing.id === item.id)) {
              snapshotData[`${targetKey}Items`].push(item);
            }

            // Collect data points for each metric type
            const metricTypes = ['records', 'parents', 'uploaders', 'fileCount', 'dataVolume'];
            metricTypes.forEach(metricType => {
              let value = 0;
              let valueType = 'number';

              switch (metricType) {
                case 'records':
                  value = getTotalCount(item.records || item);
                  break;
                case 'parents':
                  value = getTotalCount(item.parents || item);
                  break;
                case 'uploaders':
                  value = item.total_uploaders || 0;
                  break;
                case 'fileCount':
                  value = getTotalFileCount(item.files || item);
                  break;
                case 'dataVolume':
                  value = getTotalDataVolume(item.files || item);
                  valueType = 'filesize';
                  break;
              }

              // Find or create data point for this date
              let existingDataPoint = snapshotData[`${targetKey}DataPoints`][metricType].find(dp => dp.date === date);
              if (!existingDataPoint) {
                existingDataPoint = { date };
                snapshotData[`${targetKey}DataPoints`][metricType].push(existingDataPoint);
              }
              existingDataPoint[item.id] = value;
            });
          });
        }
      });
    });

    // Create byFilePresence series for each metric type
    const byFilePresenceMetrics = ['records', 'parents', 'uploaders', 'fileCount', 'dataVolume'];
    byFilePresenceMetrics.forEach(metricType => {
      const dataPoints = byFilePresenceDataPoints.map(dp => ({
        date: dp.date,
        withFiles: dp.withFiles,
        withoutFiles: dp.withoutFiles
      }));
      snapshotData.byFilePresence[metricType] = createDataSeriesArray(['withFiles', 'withoutFiles'], dataPoints);
    });

    // Create subcount series for each metric type
    Object.keys(subcountTypes).forEach(subcountType => {
      const targetKey = subcountTypes[subcountType];
      if (snapshotData[`${targetKey}Items`] && snapshotData[`${targetKey}DataPoints`]) {
        const metricTypes = ['records', 'parents', 'uploaders', 'fileCount', 'dataVolume'];
        metricTypes.forEach(metricType => {
          const valueType = metricType === 'dataVolume' ? 'filesize' : 'number';
          snapshotData[targetKey][metricType] = createDataSeriesFromItems(
            snapshotData[`${targetKey}Items`],
            snapshotData[`${targetKey}DataPoints`][metricType],
            'line',
            valueType
          );
        });
        // Clean up temporary data
        delete snapshotData[`${targetKey}Items`];
        delete snapshotData[`${targetKey}DataPoints`];
      }
    });

    // Convert global DataPoint arrays to DataSeries arrays
    snapshotData.global.records = [createGlobalSeries(snapshotData.global.records, 'bar', 'number')];
    snapshotData.global.parents = [createGlobalSeries(snapshotData.global.parents, 'bar', 'number')];
    snapshotData.global.uploaders = [createGlobalSeries(snapshotData.global.uploaders, 'bar', 'number')];
    snapshotData.global.fileCount = [createGlobalSeries(snapshotData.global.fileCount, 'bar', 'number')];
    snapshotData.global.dataVolume = [createGlobalSeries(snapshotData.global.dataVolume, 'bar', 'filesize')];
  }

  return snapshotData;
};

/**
 * Transform daily usage delta aggregation documents for display in the dashboard.
 *
 * @param {Array} deltaDocs - Array of daily usage delta aggregation documents
 *
 * @returns {UsageDeltaData} Transformed data with usage time series metrics organized by category
 */
const transformUsageDeltaData = (deltaDocs) => {

  const deltaData = {
    global: {
      views: [],
      downloads: [],
      visitors: [],
      dataVolume: [],
    },
    byFilePresence: {
      views: [],
      downloads: [],
      visitors: [],
      dataVolume: [],
    },
    byAccessStatus: {
      views: [],
      downloads: [],
      visitors: [],
      dataVolume: [],
    },
    byFileTypes: {
      views: [],
      downloads: [],
      visitors: [],
      dataVolume: [],
    },
    byLanguages: {
      views: [],
      downloads: [],
      visitors: [],
      dataVolume: [],
    },
    byResourceTypes: {
      views: [],
      downloads: [],
      visitors: [],
      dataVolume: [],
    },
    bySubjects: {
      views: [],
      downloads: [],
      visitors: [],
      dataVolume: [],
    },
    byPublishers: {
      views: [],
      downloads: [],
      visitors: [],
      dataVolume: [],
    },
    byLicenses: {
      views: [],
      downloads: [],
      visitors: [],
      dataVolume: [],
    },
    byCountries: {
      views: [],
      downloads: [],
      visitors: [],
      dataVolume: [],
    },
    byReferrers: {
      views: [],
      downloads: [],
      visitors: [],
      dataVolume: [],
    },
    byAffiliations: {
      views: [],
      downloads: [],
      visitors: [],
      dataVolume: [],
    },
  };

  const subcountTypes = {
    'by_access_status': 'byAccessStatus',
    'by_file_types': 'byFileTypes',
    'by_languages': 'byLanguages',
    'by_resource_types': 'byResourceTypes',
    'by_subjects': 'bySubjects',
    'by_publishers': 'byPublishers',
    'by_licenses': 'byLicenses',
    'by_countries': 'byCountries',
    'by_referrers': 'byReferrers',
    'by_affiliations': 'byAffiliations',
  };

  const getNetViewEvents = (item) => {
    return item && item.view ? item.view.total_events : 0;
  };

  const getNetDownloadEvents = (item) => {
    return item && item.download ? item.download.total_events : 0;
  };

  const getNetVisitors = (item) => {
    if (!item) return 0;
    const viewVisitors = item.view ? item.view.unique_visitors : 0;
    const downloadVisitors = item.download ? item.download.unique_visitors : 0;
    return Math.max(viewVisitors, downloadVisitors);
  };

  const getNetDataVolume = (item) => {
    return item && item.download ? item.download.total_volume : 0;
  };

  if (deltaDocs && Array.isArray(deltaDocs)) {
    const byFilePresenceDataPoints = [];

    deltaDocs.forEach(doc => {
      const source = doc;
      const date = source.period_start.split('T')[0];

      // Accumulate global data points
      deltaData.global.views.push(createDataPoint(date, getNetViewEvents(source.totals)));
      deltaData.global.downloads.push(createDataPoint(date, getNetDownloadEvents(source.totals)));
      deltaData.global.visitors.push(createDataPoint(date, getNetVisitors(source.totals)));
      deltaData.global.dataVolume.push(createDataPoint(date, getNetDataVolume(source.totals), 'filesize'));

      // Collect byFilePresence data points
      byFilePresenceDataPoints.push({
        date,
        withFiles: getNetViewEvents(source.totals.view),
        withoutFiles: getNetDownloadEvents(source.totals.download)
      });

      // Collect subcount data points for each metric type
      Object.keys(subcountTypes).forEach(subcountType => {
        const subcountSeries = source.subcounts[subcountType];
        if (subcountSeries && subcountSeries.length > 0) {
          const targetKey = subcountTypes[subcountType];

          // Initialize data structures for each metric type
          if (!deltaData[`${targetKey}DataPoints`]) {
            deltaData[`${targetKey}DataPoints`] = {
              views: [],
              downloads: [],
              visitors: [],
              dataVolume: []
            };
            deltaData[`${targetKey}Items`] = [];
          }

          subcountSeries.forEach(item => {
            // Store the item for later series creation
            if (!deltaData[`${targetKey}Items`].find(existing => existing.id === item.id)) {
              deltaData[`${targetKey}Items`].push(item);
            }

            // Collect data points for each metric type
            const metricTypes = ['views', 'downloads', 'visitors', 'dataVolume'];
            metricTypes.forEach(metricType => {
              let value = 0;
              let valueType = 'number';

              switch (metricType) {
                case 'views':
                  value = getNetViewEvents(item);
                  break;
                case 'downloads':
                  value = getNetDownloadEvents(item);
                  break;
                case 'visitors':
                  value = getNetVisitors(item);
                  break;
                case 'dataVolume':
                  value = getNetDataVolume(item);
                  valueType = 'filesize';
                  break;
              }

              // Find or create data point for this date
              let existingDataPoint = deltaData[`${targetKey}DataPoints`][metricType].find(dp => dp.date === date);
              if (!existingDataPoint) {
                existingDataPoint = { date };
                deltaData[`${targetKey}DataPoints`][metricType].push(existingDataPoint);
              }
              existingDataPoint[item.id] = value;
            });
          });
        }
      });
    });

    // Create byFilePresence series for each metric type
    const byFilePresenceMetrics = ['views', 'downloads', 'visitors', 'dataVolume'];
    byFilePresenceMetrics.forEach(metricType => {
      const dataPoints = byFilePresenceDataPoints.map(dp => ({
        date: dp.date,
        withFiles: dp.withFiles,
        withoutFiles: dp.withoutFiles
      }));
      deltaData.byFilePresence[metricType] = createDataSeriesArray(['withFiles', 'withoutFiles'], dataPoints);
    });

    // Create subcount series for each metric type
    Object.keys(subcountTypes).forEach(subcountType => {
      const targetKey = subcountTypes[subcountType];
      if (deltaData[`${targetKey}Items`] && deltaData[`${targetKey}DataPoints`]) {
        const metricTypes = ['views', 'downloads', 'visitors', 'dataVolume'];
        metricTypes.forEach(metricType => {
          const valueType = metricType === 'dataVolume' ? 'filesize' : 'number';
          deltaData[targetKey][metricType] = createDataSeriesFromItems(
            deltaData[`${targetKey}Items`],
            deltaData[`${targetKey}DataPoints`][metricType],
            'line',
            valueType
          );
        });
        // Clean up temporary data
        delete deltaData[`${targetKey}Items`];
        delete deltaData[`${targetKey}DataPoints`];
      }
    });

    // Convert global DataPoint arrays to DataSeries arrays
    deltaData.global.views = [createGlobalSeries(deltaData.global.views, 'line', 'number')];
    deltaData.global.downloads = [createGlobalSeries(deltaData.global.downloads, 'line', 'number')];
    deltaData.global.visitors = [createGlobalSeries(deltaData.global.visitors, 'line', 'number')];
    deltaData.global.dataVolume = [createGlobalSeries(deltaData.global.dataVolume, 'line', 'filesize')];
  }

  return deltaData;
};

/**
 * Transform daily usage snapshot aggregation documents for display in the dashboard.
 *
 * @param {Array} snapshotDocs - Array of daily usage snapshot aggregation documents
 *
 * @returns {UsageSnapshotData} Transformed data with cumulative usage time series metrics organized by category
 */
const transformUsageSnapshotData = (snapshotDocs) => {

  const snapshotData = {
    global: {
      views: [],
      downloads: [],
      visitors: [],
      dataVolume: [],
    },
    byFilePresence: {
      views: [],
      downloads: [],
      visitors: [],
      dataVolume: [],
    },
    byAccessStatus: {
      views: [],
      downloads: [],
      visitors: [],
      dataVolume: [],
    },
    byFileTypes: {
      views: [],
      downloads: [],
      visitors: [],
      dataVolume: [],
    },
    byLanguages: {
      views: [],
      downloads: [],
      visitors: [],
      dataVolume: [],
    },
    byResourceTypes: {
      views: [],
      downloads: [],
      visitors: [],
      dataVolume: [],
    },
    bySubjects: {
      views: [],
      downloads: [],
      visitors: [],
      dataVolume: [],
    },
    byPublishers: {
      views: [],
      downloads: [],
      visitors: [],
      dataVolume: [],
    },
    byLicenses: {
      views: [],
      downloads: [],
      visitors: [],
      dataVolume: [],
    },
    byCountries: {
      views: [],
      downloads: [],
      visitors: [],
      dataVolume: [],
    },
    byReferrers: {
      views: [],
      downloads: [],
      visitors: [],
      dataVolume: [],
    },
    byAffiliations: {
      views: [],
      downloads: [],
      visitors: [],
      dataVolume: [],
    },
    // Separate properties for view-based and download-based data
    topCountriesByView: {
      views: [],
      downloads: [],
      visitors: [],
      dataVolume: [],
    },
    topCountriesByDownload: {
      views: [],
      downloads: [],
      visitors: [],
      dataVolume: [],
    },
    topSubjectsByView: {
      views: [],
      downloads: [],
      visitors: [],
      dataVolume: [],
    },
    topSubjectsByDownload: {
      views: [],
      downloads: [],
      visitors: [],
      dataVolume: [],
    },
    topPublishersByView: {
      views: [],
      downloads: [],
      visitors: [],
      dataVolume: [],
    },
    topPublishersByDownload: {
      views: [],
      downloads: [],
      visitors: [],
      dataVolume: [],
    },
    topLicensesByView: {
      views: [],
      downloads: [],
      visitors: [],
      dataVolume: [],
    },
    topLicensesByDownload: {
      views: [],
      downloads: [],
      visitors: [],
      dataVolume: [],
    },
    topReferrersByView: {
      views: [],
      downloads: [],
      visitors: [],
      dataVolume: [],
    },
    topReferrersByDownload: {
      views: [],
      downloads: [],
      visitors: [],
      dataVolume: [],
    },
    topAffiliationsByView: {
      views: [],
      downloads: [],
      visitors: [],
      dataVolume: [],
    },
    topAffiliationsByDownload: {
      views: [],
      downloads: [],
      visitors: [],
      dataVolume: [],
    },
  };

  const subcountTypes = {
    'all_access_status': 'byAccessStatus',
    'all_file_types': 'byFileTypes',
    'all_languages': 'byLanguages',
    'all_resource_types': 'byResourceTypes',
    'top_subjects': 'bySubjects',
    'top_publishers': 'byPublishers',
    'top_licenses': 'byLicenses',
    'top_countries': 'byCountries',
    'top_referrers': 'byReferrers',
    'top_affiliations': 'byAffiliations',
  };

  // Mapping for separate view/download properties
  const separateSubcountTypes = {
    'top_countries': { by_view: 'topCountriesByView', by_download: 'topCountriesByDownload' },
    'top_subjects': { by_view: 'topSubjectsByView', by_download: 'topSubjectsByDownload' },
    'top_publishers': { by_view: 'topPublishersByView', by_download: 'topPublishersByDownload' },
    'top_licenses': { by_view: 'topLicensesByView', by_download: 'topLicensesByDownload' },
    'top_referrers': { by_view: 'topReferrersByView', by_download: 'topReferrersByDownload' },
    'top_affiliations': { by_view: 'topAffiliationsByView', by_download: 'topAffiliationsByDownload' },
  };

  const getTotalViewEvents = (item) => {
    return item && item.total_events ? item.total_events : 0;
  };

  const getTotalDownloadEvents = (item) => {
    return item && item.total_events ? item.total_events : 0;
  };

  const getTotalVisitors = (item) => {
    const viewVisitors = item && item.unique_visitors ? item.unique_visitors : 0;
    const downloadVisitors = item && item.unique_visitors ? item.unique_visitors : 0;
    return Math.max(viewVisitors, downloadVisitors);
  };

  const getTotalDataVolume = (item) => {
    return item && item.total_volume ? item.total_volume : 0;
  };

  if (snapshotDocs && Array.isArray(snapshotDocs)) {
    const byFilePresenceDataPoints = [];

    snapshotDocs.forEach(doc => {
      const source = doc;
      const date = source.snapshot_date.split('T')[0];

      // Accumulate global data points
      snapshotData.global.views.push(createDataPoint(date, getTotalViewEvents(source.totals.view)));
      snapshotData.global.downloads.push(createDataPoint(date, getTotalDownloadEvents(source.totals.download)));
      snapshotData.global.visitors.push(createDataPoint(date, getTotalVisitors(source.totals.view)));
      snapshotData.global.dataVolume.push(createDataPoint(date, getTotalDataVolume(source.totals.download), 'filesize'));

      // Collect subcount data points for each metric type
      Object.keys(subcountTypes).forEach(subcountType => {
        const subcountSeries = source.subcounts[subcountType];
        if (subcountSeries) {
          const targetKey = subcountTypes[subcountType];

          // Handle different subcount structures
          if (Array.isArray(subcountSeries)) {
            // Simple array structure (all_* fields)
            if (subcountSeries.length > 0) {
              // Initialize data structures for each metric type
              if (!snapshotData[`${targetKey}DataPoints`]) {
                snapshotData[`${targetKey}DataPoints`] = {
                  views: [],
                  downloads: [],
                  visitors: [],
                  dataVolume: []
                };
                snapshotData[`${targetKey}Items`] = [];
              }

              subcountSeries.forEach(item => {
                // Store the item for later series creation
                if (!snapshotData[`${targetKey}Items`].find(existing => existing.id === item.id)) {
                  snapshotData[`${targetKey}Items`].push(item);
                }

                // Collect data points for each metric type
                const metricTypes = ['views', 'downloads', 'visitors', 'dataVolume'];
                metricTypes.forEach(metricType => {
                  let value = 0;
                  let valueType = 'number';

                  switch (metricType) {
                    case 'views':
                      value = getTotalViewEvents(item);
                      break;
                    case 'downloads':
                      value = getTotalDownloadEvents(item);
                      break;
                    case 'visitors':
                      value = getTotalVisitors(item);
                      break;
                    case 'dataVolume':
                      value = getTotalDataVolume(item);
                      valueType = 'filesize';
                      break;
                  }

                  // Find or create data point for this date
                  let existingDataPoint = snapshotData[`${targetKey}DataPoints`][metricType].find(dp => dp.date === date);
                  if (!existingDataPoint) {
                    existingDataPoint = { date };
                    snapshotData[`${targetKey}DataPoints`][metricType].push(existingDataPoint);
                  }
                  existingDataPoint[item.id] = value;
                });
              });
            }
          } else if (typeof subcountSeries === 'object' && subcountSeries !== null) {
            // Object structure with separate view/download data (top_* fields)
            const separateKeys = separateSubcountTypes[subcountType];
            if (separateKeys) {
              Object.keys(separateKeys).forEach(key => {
                const separateKey = separateKeys[key];
                const separateSeries = subcountSeries[key];

                if (separateSeries && separateSeries.length > 0) {
                  // Initialize data structures for each metric type
                  if (!snapshotData[`${separateKey}DataPoints`]) {
                    snapshotData[`${separateKey}DataPoints`] = {
                      views: [],
                      downloads: [],
                      visitors: [],
                      dataVolume: []
                    };
                    snapshotData[`${separateKey}Items`] = [];
                  }

                  separateSeries.forEach(item => {
                    // Store the item for later series creation
                    if (!snapshotData[`${separateKey}Items`].find(existing => existing.id === item.id)) {
                      snapshotData[`${separateKey}Items`].push(item);
                    }

                    // Collect data points for each metric type
                    const metricTypes = ['views', 'downloads', 'visitors', 'dataVolume'];
                    metricTypes.forEach(metricType => {
                      let value = 0;
                      let valueType = 'number';

                      switch (metricType) {
                        case 'views':
                          value = getTotalViewEvents(item.view);
                          break;
                        case 'downloads':
                          value = getTotalDownloadEvents(item.download);
                          break;
                        case 'visitors':
                          value = getTotalVisitors(item.view);
                          break;
                        case 'dataVolume':
                          value = getTotalDataVolume(item.download);
                          valueType = 'filesize';
                          break;
                      }

                      // Find or create data point for this date
                      let existingDataPoint = snapshotData[`${separateKey}DataPoints`][metricType].find(dp => dp.date === date);
                      if (!existingDataPoint) {
                        existingDataPoint = { date };
                        snapshotData[`${separateKey}DataPoints`][metricType].push(existingDataPoint);
                      }
                      existingDataPoint[item.id] = value;
                    });
                  });
                }
              });
            }
          }
        }
      });
    });

    // Create subcount series for each metric type
    Object.keys(subcountTypes).forEach(subcountType => {
      const targetKey = subcountTypes[subcountType];
      if (snapshotData[`${targetKey}Items`] && snapshotData[`${targetKey}DataPoints`]) {
        const metricTypes = ['views', 'downloads', 'visitors', 'dataVolume'];
        metricTypes.forEach(metricType => {
          const valueType = metricType === 'dataVolume' ? 'filesize' : 'number';
          snapshotData[targetKey][metricType] = createDataSeriesFromItems(
            snapshotData[`${targetKey}Items`],
            snapshotData[`${targetKey}DataPoints`][metricType],
            'line',
            valueType
          );
        });
        // Clean up temporary data
        delete snapshotData[`${targetKey}Items`];
        delete snapshotData[`${targetKey}DataPoints`];
      }
    });

    // Create separate subcount series for each metric type
    Object.keys(separateSubcountTypes).forEach(subcountType => {
      const separateKeys = separateSubcountTypes[subcountType];
      Object.keys(separateKeys).forEach(key => {
        const separateKey = separateKeys[key];
        if (snapshotData[`${separateKey}Items`] && snapshotData[`${separateKey}DataPoints`]) {
          const metricTypes = ['views', 'downloads', 'visitors', 'dataVolume'];
          metricTypes.forEach(metricType => {
            const valueType = metricType === 'dataVolume' ? 'filesize' : 'number';
            snapshotData[separateKey][metricType] = createDataSeriesFromItems(
              snapshotData[`${separateKey}Items`],
              snapshotData[`${separateKey}DataPoints`][metricType],
              'line',
              valueType
            );
          });
          // Clean up temporary data
          delete snapshotData[`${separateKey}Items`];
          delete snapshotData[`${separateKey}DataPoints`];
        }
      });
    });

    // Convert global DataPoint arrays to DataSeries arrays
    snapshotData.global.views = [createGlobalSeries(snapshotData.global.views, 'bar', 'number')];
    snapshotData.global.downloads = [createGlobalSeries(snapshotData.global.downloads, 'bar', 'number')];
    snapshotData.global.visitors = [createGlobalSeries(snapshotData.global.visitors, 'bar', 'number')];
    snapshotData.global.dataVolume = [createGlobalSeries(snapshotData.global.dataVolume, 'bar', 'filesize')];
  }

  return snapshotData;
};

/**
 * Transform daily record delta and snapshot aggregation documents into the format expected by dashboard components.
 *
 * @param {Object} rawStats - The raw stats object from the API containing record_deltas, record_snapshots, usage_deltas, usage_snapshots
 *
 * @returns {TransformedApiData} Transformed data with all record and usage metrics organized by category and time period
 *
 * Each transformed data object contains time series data points organized by:
 * - Global metrics (total counts across all records)
 * - By file presence (with/without files)
 * - By various categories (resource types, access rights, languages, etc.)
 * - Separate view/download data for usage statistics
 */
export const transformApiData = (rawStats) => {

  const returnData = {
    recordDeltaDataCreated: {},
    recordDeltaDataAdded: {},
    recordDeltaDataPublished: {},
    recordSnapshotDataCreated: {},
    recordSnapshotDataAdded: {},
    recordSnapshotDataPublished: {},
    usageDeltaData: {},
    usageSnapshotData: {},
  };

  if (!rawStats) {
    return returnData;
  }

  returnData.recordDeltaDataCreated = transformRecordDeltaData(rawStats.record_deltas_created);
  returnData.recordDeltaDataAdded = transformRecordDeltaData(rawStats.record_deltas_added);
  returnData.recordDeltaDataPublished = transformRecordDeltaData(rawStats.record_deltas_published);
  returnData.recordSnapshotDataCreated = transformRecordSnapshotData(rawStats.record_snapshots_created);
  returnData.recordSnapshotDataAdded = transformRecordSnapshotData(rawStats.record_snapshots_added);
  returnData.recordSnapshotDataPublished = transformRecordSnapshotData(rawStats.record_snapshots_published);
  returnData.usageDeltaData = transformUsageDeltaData(rawStats.usage_deltas);
  returnData.usageSnapshotData = transformUsageSnapshotData(rawStats.usage_snapshots);

  return returnData;
};


