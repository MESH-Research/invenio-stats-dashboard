// Part of the Invenio-Stats-Dashboard extension for InvenioRDM
// Copyright (C) 2025 Mesh Research
//
// Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
// it under the terms of the MIT License; see LICENSE file for more details.

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
 * Create an array of DataSeries objects from an array of data points with named properties.
 * This function is used to transform data points that have properties like 'withFiles' and 'metadataOnly'
 * into separate series for charting.
 *
 * @param {string[]} seriesNames - Array of property names to extract as separate series
 * @param {FilePresenceDataPoint[]} [dataPointsArray=[]] - Array of data points with named properties
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
 * @param {Object} [localizationMap] - Map of subcount id to localized label string
 * @returns {DataSeries[]} Array of DataSeries objects
 */
const createDataSeriesFromItems = (subcountItems, dataPointsArray = [], type = 'line', valueType = 'number', localizationMap = {}) => {
  const seriesArray = subcountItems.map(item => ({
    id: item.id,
    name: localizationMap[item.id] || item.id,
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
 * @typedef {Object} FilePresenceDataPoint
 * @property {string} date - Date string (YYYY-MM-DD format)
 * @property {number} withFiles - Value for records with files
 * @property {number} metadataOnly - Value for metadata-only records
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
 * @typedef {Object} FilePresenceMetrics
 * @property {DataSeries[]} records - Record count series split by file presence
 * @property {DataSeries[]} parents - Parent count series split by file presence
 *
 * @typedef {Object} UsageMetrics
 * @property {DataSeries[]} views - View count series
 * @property {DataSeries[]} downloads - Download count series
 * @property {DataSeries[]} visitors - Visitor count series
 * @property {DataSeries[]} dataVolume - Data volume series
 *
 * @typedef {Object} RecordDeltaData
 * @property {RecordMetrics} global - Global record metrics
 * @property {FilePresenceMetrics} byFilePresence - Record metrics by file presence (records and parents only)
 * @property {RecordMetrics} resourceTypes
 * @property {RecordMetrics} accessStatus
 * @property {RecordMetrics} languages
 * @property {RecordMetrics} affiliations
 * @property {RecordMetrics} funders
 * @property {RecordMetrics} subjects
 * @property {RecordMetrics} publishers
 * @property {RecordMetrics} periodicals
 * @property {RecordMetrics} rights
 * @property {RecordMetrics} fileTypes
 *
 * @typedef {Object} RecordSnapshotData
 * @property {RecordMetrics} global - Global record metrics
 * @property {FilePresenceMetrics} byFilePresence - Record metrics by file presence (records and parents only)
 * @property {RecordMetrics} resourceTypes
 * @property {RecordMetrics} accessStatus
 * @property {RecordMetrics} languages
 * @property {RecordMetrics} affiliations
 * @property {RecordMetrics} funders
 * @property {RecordMetrics} subjects
 * @property {RecordMetrics} publishers
 * @property {RecordMetrics} periodicals
 * @property {RecordMetrics} rights
 * @property {RecordMetrics} fileTypes
 *
 * @typedef {Object} UsageDeltaData
 * @property {UsageMetrics} global - Global usage metrics
 * @property {UsageMetrics} byAccessStatuses
 * @property {UsageMetrics} byFileTypes
 * @property {UsageMetrics} byLanguages
 * @property {UsageMetrics} byResourceTypes
 * @property {UsageMetrics} bySubjects
 * @property {UsageMetrics} byPublishers
 * @property {UsageMetrics} byRights
 * @property {UsageMetrics} byCountries
 * @property {UsageMetrics} byReferrers
 * @property {UsageMetrics} byAffiliations
 *
 * @typedef {Object} UsageSnapshotData
 * @property {UsageMetrics} global - Global usage metrics
 * @property {UsageMetrics} byAccessStatuses
 * @property {UsageMetrics} byFileTypes
 * @property {UsageMetrics} byLanguages
 * @property {UsageMetrics} byResourceTypes
 * @property {UsageMetrics} bySubjects
 * @property {UsageMetrics} byPublishers
 * @property {UsageMetrics} byRights
 * @property {UsageMetrics} byCountries
 * @property {UsageMetrics} byReferrers
 * @property {UsageMetrics} byAffiliations
 * @property {UsageMetrics} topCountriesByView
 * @property {UsageMetrics} topCountriesByDownload
 * @property {UsageMetrics} topSubjectsByView
 * @property {UsageMetrics} topSubjectsByDownload
 * @property {UsageMetrics} topPublishersByView
 * @property {UsageMetrics} topPublishersByDownload
 * @property {UsageMetrics} topRightsByView
 * @property {UsageMetrics} topRightsByDownload
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
 * @param {Array} deltaDocs - Array of daily record delta aggregation documents from the API
 * @returns {RecordDeltaData} Transformed data with delta time series metrics organized by category
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
      parents: []
    },
    accessStatuses: {
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
    rights: {
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
    'by_resource_types': 'resourceTypes',
    'by_access_statuses': 'accessStatuses',
    'by_languages': 'languages',
    'by_affiliations_creators': 'affiliations',
    'by_affiliations_contributors': 'affiliations',
    'by_funders': 'funders',
    'by_subjects': 'subjects',
    'by_publishers': 'publishers',
    'by_periodicals': 'periodicals',
    'by_rights': 'rights',
    'by_file_types': 'fileTypes'
  };


  /**
   * Calculate the net count change for a subcount item by combining with_files and metadata_only counts.
   *
   * @param {Object} item - Subcount item with added/removed structure
   * @returns {number} Net count change (added - removed)
   */
  const getNetCount = (item) => {
    if (item.added && item.removed) {
      const added = (item.added.metadata_only || 0) + (item.added.with_files || 0);
      const removed = (item.removed.metadata_only || 0) + (item.removed.with_files || 0);
      return added - removed;
    }
    return 0;
  };

  /**
   * Calculate the net file count change for a subcount item.
   *
   * @param {Object} item - Subcount item with added/removed structure or nested files structure
   * @returns {number} Net file count change (added - removed)
   */
  const getNetFileCount = (item) => {
    if (item.added && item.removed) {
      // Direct structure (like source.files)
      return (item.added.file_count || 0) - (item.removed.file_count || 0);
    } else if (item.files) {
      // Nested structure (like subcount items)
      return (item.files.added?.file_count || 0) - (item.files.removed?.file_count || 0);
    }
    return 0;
  };

  /**
   * Calculate the net data volume change for a subcount item.
   *
   * @param {Object} item - Subcount item with added/removed structure or nested files structure
   * @returns {number} Net data volume change in bytes (added - removed)
   */
  const getNetDataVolume = (item) => {
    if (item.added && item.removed) {
      // Direct structure (like source.files)
      return (item.added.data_volume || 0) - (item.removed.data_volume || 0);
    } else if (item.files) {
      // Nested structure (like subcount items)
      return (item.files.added?.data_volume || 0) - (item.files.removed?.data_volume || 0);
    }
    return 0;
  };

    if (deltaDocs && Array.isArray(deltaDocs)) {
    // Create localization map from all documents
    const localizationMap = createLocalizationMap(deltaDocs);

    deltaDocs.forEach(doc => {
      const source = doc;
      const date = source.period_start.split('T')[0];

      // Accumulate global data points
      deltaData.global.records.push(createDataPoint(date, getNetCount(source.records)));
      deltaData.global.parents.push(createDataPoint(date, getNetCount(source.parents)));
      deltaData.global.uploaders.push(createDataPoint(date, source.uploaders));
      deltaData.global.fileCount.push(createDataPoint(date, getNetFileCount(source.files)));
      deltaData.global.dataVolume.push(createDataPoint(date, getNetDataVolume(source.files), 'filesize'));

      // Collect byFilePresence data points directly into deltaData structure
      // but only for metrics that have both withFiles and metadataOnly
      ['records', 'parents'].forEach(key => {
        const dataPoint = { date };

        // Calculate net change for delta data
        const addedWithFiles = source[key].added?.with_files || 0;
        const removedWithFiles = source[key].removed?.with_files || 0;
        const addedMetadataOnly = source[key].added?.metadata_only || 0;
        const removedMetadataOnly = source[key].removed?.metadata_only || 0;

        dataPoint.withFiles = addedWithFiles - removedWithFiles;
        dataPoint.metadataOnly = addedMetadataOnly - removedMetadataOnly;

        deltaData.byFilePresence[key].push(dataPoint);
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
      const dataPoints = deltaData.byFilePresence[metricType];
      const valueType = metricType === 'dataVolume' ? 'filesize' : 'number';
      deltaData.byFilePresence[metricType] = createDataSeriesArray(['withFiles', 'metadataOnly'], dataPoints, 'line', valueType);
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
            valueType,
            localizationMap
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
 * @param {Array} snapshotDocs - Array of daily record snapshot aggregation documents from the API
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
      parents: []
    },
    accessStatuses: {
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
    rights: {
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
    'all_access_statuses': 'accessStatuses',
    'top_languages': 'languages',
    'top_affiliations_creator': 'affiliations',
    'top_affiliations_contributor': 'affiliations',
    'top_funders': 'funders',
    'top_subjects': 'subjects',
    'top_publishers': 'publishers',
    'top_periodicals': 'periodicals',
    'all_rights': 'rights',
    'all_file_types': 'fileTypes'
  };

  /**
   * Calculate the total count for a record item by combining with_files and metadata_only counts.
   *
   * @param {Object} item - Record item with metadata_only and with_files properties
   * @returns {number} Total count (metadata_only + with_files)
   */
  const getTotalCount = (item) => {
    if (!item) return 0;
    return (item.metadata_only || 0) + (item.with_files || 0);
  };

  /**
   * Extract the total file count from a record item.
   *
   * @param {Object} item - Record item with file_count property
   * @returns {number} Total file count or 0 if not available
   */
  const getTotalFileCount = (item) => {
    if (!item) return 0;
    return item.file_count || 0;
  };

  /**
   * Extract the total data volume from a record item.
   *
   * @param {Object} item - Record item with data_volume property
   * @returns {number} Total data volume in bytes or 0 if not available
   */
  const getTotalDataVolume = (item) => {
    if (!item) return 0;
    return item.data_volume || 0;
  };

    if (snapshotDocs && Array.isArray(snapshotDocs)) {
    // Create localization map from all documents
    const localizationMap = createLocalizationMap(snapshotDocs);

    snapshotDocs.forEach(doc => {
      const source = doc;
      const date = source.snapshot_date.split('T')[0];

      // Accumulate global data points
      snapshotData.global.records.push(createDataPoint(date, getTotalCount(source.total_records)));
      snapshotData.global.parents.push(createDataPoint(date, getTotalCount(source.total_parents)));
      snapshotData.global.uploaders.push(createDataPoint(date, source.total_uploaders));
      snapshotData.global.fileCount.push(createDataPoint(date, getTotalFileCount(source.total_files)));
      snapshotData.global.dataVolume.push(createDataPoint(date, getTotalDataVolume(source.total_files), 'filesize'));

      // Collect byFilePresence data points directly into snapshotData structure
      // but only for metrics that have both withFiles and metadataOnly
      ['records', 'parents'].forEach(key => {
        const dataPoint = { date };

        dataPoint.withFiles = source[`total_${key}`].with_files || 0;
        dataPoint.metadataOnly = source[`total_${key}`].metadata_only || 0;

        snapshotData.byFilePresence[key].push(dataPoint);
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
    const byFilePresenceMetrics = ['records', 'parents'];
    byFilePresenceMetrics.forEach(metricType => {
      const dataPoints = snapshotData.byFilePresence[metricType];
      const valueType = metricType === 'dataVolume' ? 'filesize' : 'number';
      snapshotData.byFilePresence[metricType] = createDataSeriesArray(['withFiles', 'metadataOnly'], dataPoints, 'line', valueType);
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
                valueType,
                localizationMap
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
 * @param {Array} deltaDocs - Array of daily usage delta aggregation documents from the API
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
    byAccessStatuses: {
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
    byRights: {
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
    'by_access_statuses': 'byAccessStatuses',
    'by_file_types': 'byFileTypes',
    'by_languages': 'byLanguages',
    'by_resource_types': 'byResourceTypes',
    'by_subjects': 'bySubjects',
    'by_publishers': 'byPublishers',
    'by_rights': 'byRights',
    'by_countries': 'byCountries',
    'by_referrers': 'byReferrers',
    'by_affiliations': 'byAffiliations',
  };

  /**
   * Extract the net view events count from a usage item.
   *
   * @param {Object} item - Usage item with optional view property
   * @returns {number} Total view events count or 0 if not available
   */
  const getNetViewEvents = (item) => {
    return item && item.view ? item.view.total_events : 0;
  };

  /**
   * Extract the net download events count from a usage item.
   *
   * @param {Object} item - Usage item with optional download property
   * @returns {number} Total download events count or 0 if not available
   */
  const getNetDownloadEvents = (item) => {
    return item && item.download ? item.download.total_events : 0;
  };

  /**
   * Extract the net unique visitors count from a usage item.
   * Takes the maximum of view and download visitors since a visitor can interact with both.
   *
   * @param {Object} item - Usage item with optional view and download properties
   * @returns {number} Maximum unique visitors count or 0 if not available
   */
  const getNetVisitors = (item) => {
    if (!item) return 0;
    const viewVisitors = item.view ? item.view.unique_visitors : 0;
    const downloadVisitors = item.download ? item.download.unique_visitors : 0;
    return Math.max(viewVisitors, downloadVisitors);
  };

  /**
   * Extract the net data volume from a usage item.
   * Only available for download events.
   *
   * @param {Object} item - Usage item with optional download property
   * @returns {number} Total data volume in bytes or 0 if not available
   */
  const getNetDataVolume = (item) => {
    return item && item.download ? item.download.total_volume : 0;
  };

    if (deltaDocs && Array.isArray(deltaDocs)) {
    // Create localization map from all documents
    const localizationMap = createLocalizationMap(deltaDocs);

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
            valueType,
            localizationMap
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
 * @param {Array} snapshotDocs - Array of daily usage snapshot aggregation documents from the API
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
    byAccessStatuses: {
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
    byRights: {
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
    topRightsByView: {
      views: [],
      downloads: [],
      visitors: [],
      dataVolume: [],
    },
    topRightsByDownload: {
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
    'all_access_statuses': 'byAccessStatuses',
    'all_file_types': 'byFileTypes',
    'top_languages': 'byLanguages',
    'all_resource_types': 'byResourceTypes',
    'top_subjects': 'bySubjects',
    'top_publishers': 'byPublishers',
    'top_rights': 'byRights',
    'top_countries': 'byCountries',
    'top_referrers': 'byReferrers',
    'top_affiliations': 'byAffiliations',
  };

  // Mapping for separate view/download properties
  const separateSubcountTypes = {
    'top_countries': { by_view: 'topCountriesByView', by_download: 'topCountriesByDownload' },
    'top_subjects': { by_view: 'topSubjectsByView', by_download: 'topSubjectsByDownload' },
    'top_publishers': { by_view: 'topPublishersByView', by_download: 'topPublishersByDownload' },
    'top_rights': { by_view: 'topRightsByView', by_download: 'topRightsByDownload' },
    'top_referrers': { by_view: 'topReferrersByView', by_download: 'topReferrersByDownload' },
    'top_affiliations': { by_view: 'topAffiliationsByView', by_download: 'topAffiliationsByDownload' },
  };

  /**
   * Extract the total view events count from a usage snapshot item.
   *
   * @param {Object} item - Usage snapshot item with optional total_events property
   * @returns {number} Total view events count or 0 if not available
   */
  const getTotalViewEvents = (item) => {
    return item && item.total_events ? item.total_events : 0;
  };

  /**
   * Extract the total download events count from a usage snapshot item.
   *
   * @param {Object} item - Usage snapshot item with optional total_events property
   * @returns {number} Total download events count or 0 if not available
   */
  const getTotalDownloadEvents = (item) => {
    return item && item.total_events ? item.total_events : 0;
  };

  /**
   * Extract the total unique visitors count from a usage snapshot item.
   * Takes the maximum of view and download visitors since a visitor can interact with both.
   *
   * @param {Object} item - Usage snapshot item with optional unique_visitors property
   * @returns {number} Maximum unique visitors count or 0 if not available
   */
  const getTotalVisitors = (item) => {
    const viewVisitors = item && item.unique_visitors ? item.unique_visitors : 0;
    const downloadVisitors = item && item.unique_visitors ? item.unique_visitors : 0;
    return Math.max(viewVisitors, downloadVisitors);
  };

  /**
   * Extract the total data volume from a usage snapshot item.
   * Only available for download events.
   *
   * @param {Object} item - Usage snapshot item with optional total_volume property
   * @returns {number} Total data volume in bytes or 0 if not available
   */
  const getTotalDataVolume = (item) => {
    return item && item.total_volume ? item.total_volume : 0;
  };

    if (snapshotDocs && Array.isArray(snapshotDocs)) {
    // Create localization map from all documents
    const localizationMap = createLocalizationMap(snapshotDocs);

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
            valueType,
            localizationMap
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
              valueType,
              localizationMap
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
export const extractLocalizedLabel = (label, targetLanguage) => {
  if (typeof label === 'string') {
    return label;
  }

  if (label && typeof label === 'object') {
    // First, try to get the target language directly
    if (label[targetLanguage]) {
      return label[targetLanguage];
    }

    // If target language not available, try English as fallback
    if (label.en) {
      // Use i18next to translate the English string to the target language
      return i18next.t(label.en, { lng: targetLanguage });
    }

    // If no English fallback, use the first available language
    const availableLanguages = Object.keys(label);
    if (availableLanguages.length > 0) {
      const firstLanguage = availableLanguages[0];
      const firstLabel = label[firstLanguage];
      // Translate the first available label to the target language
      return i18next.t(firstLabel, { lng: targetLanguage });
    }
  }

  return '';
};

export const createLocalizationMap = (docs) => {
  const localizationMap = {};
  const currentLanguage = i18next.language || 'en';

  // Collect all unique subcount items from all documents
  const allSubcountItems = {};

  docs.forEach(doc => {
    if (doc.subcounts) {
      Object.keys(doc.subcounts).forEach(subcountType => {
        const subcountSeries = doc.subcounts[subcountType];
        if (subcountSeries && Array.isArray(subcountSeries)) {
          if (!allSubcountItems[subcountType]) {
            allSubcountItems[subcountType] = [];
          }
          subcountSeries.forEach(item => {
            if (!allSubcountItems[subcountType].find(existing => existing.id === item.id)) {
              allSubcountItems[subcountType].push(item);
            }
          });
        }
      });
    }
  });

  // Process each subcount category to create the localization map
  Object.keys(allSubcountItems).forEach(categoryKey => {
    const subcountItems = allSubcountItems[categoryKey];
    if (Array.isArray(subcountItems)) {
      subcountItems.forEach(item => {
        if (item.id && item.label) {
          localizationMap[item.id] = extractLocalizedLabel(item.label, currentLanguage);
        }
      });
    }
  });

  return localizationMap;
};

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


