import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { formatDate } from "../../utils/dates";

/**
 * Create a chart data point with proper date formatting
 *
 * @param {string} date - Date string in format YYYY-MM-DD
 * @param {number} value - Numeric value
 * @param {string} [valueType='number'] - Type of value ('number', 'filesize', etc.)
 * @returns {ChartDataPoint} Chart data point object
 */
const createChartDataPoint = (date, value, valueType = 'number') => {
  const dateObj = new Date(date);
  const readableDate = formatDate(date, false);

  return {
    value: [dateObj, value],
    readableDate: readableDate,
    valueType: valueType
  };
};

/**
 * Create an array of SubcountSeries objects for byFilePresence data, optionally populating with data points.
 *
 * @param {string[]} seriesNames - Array of series names (e.g., ['withFiles', 'withoutFiles'])
 * @param {Object[]} [dataPointsArray] - Array of objects mapping series name to value for each date, e.g.:
 *    [{date: '2024-01-01', withFiles: 5, withoutFiles: 2}, ...]
 * @param {string} [type='line'] - Chart type for all series
 * @param {string} [valueType='number'] - Value type for all series
 * @returns {SubcountSeries[]} Array of SubcountSeries objects
 */
const createSubcountSeriesArray = (seriesNames, dataPointsArray = [], type = 'line', valueType = 'number') => {
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
            series.data.push(createChartDataPoint(date, values[name], valueType));
          }
        }
      }
    });
  }

  return seriesArray;
};

/**
 * Create an array of SubcountSeries objects from raw subcount data.
 *
 * @param {Array} subcountItems - Array of subcount items with id and optional label
 * @param {Object[]} [dataPointsArray] - Array of objects mapping subcount id to value for each date
 * @param {string} [type='line'] - Chart type for all series
 * @param {string} [valueType='number'] - Value type for all series
 * @returns {SubcountSeries[]} Array of SubcountSeries objects
 */
const createSubcountSeriesFromItems = (subcountItems, dataPointsArray = [], type = 'line', valueType = 'number') => {
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
          series.data.push(createChartDataPoint(date, values[series.id], valueType));
        }
      }
    });
  }

  return seriesArray;
};

/**
 * Type definitions for data transformer return objects
 *
 * @typedef {Object} ChartDataPoint
 * @property {[Date, number]} value - [date, value] array for chart
 * @property {string} readableDate - Formatted date string
 * @property {string} valueType - Type of value ('number', 'filesize', etc.)
 *
 * @typedef {Object} SubcountSeries
 * @property {string} id - Unique identifier for the series
 * @property {string} name - Series name (display name, can be label or id)
 * @property {ChartDataPoint[]} data - Array of chart data points
 * @property {string} [type='line'] - Chart type ('line', 'bar', etc.)
 * @property {string} [valueType='number'] - Type of value ('number', 'filesize', etc.)
 *
 * @typedef {Object} RecordSeries
 * @property {ChartDataPoint[]} records - Record count data points
 * @property {ChartDataPoint[]} parents - Parent count data points
 * @property {ChartDataPoint[]} files - File count data points
 * @property {ChartDataPoint[]} dataVolume - Data volume points
 * @property {ChartDataPoint[]} uploaders - Uploader count data points
 *
 * @typedef {Object} UsageSeries
 * @property {ChartDataPoint[]} views - View count data points
 * @property {ChartDataPoint[]} downloads - Download count data points
 * @property {ChartDataPoint[]} visitors - Visitor count data points
 * @property {ChartDataPoint[]} dataVolume - Data volume points
 *
 * @typedef {Object} SubcountMetrics
 * @property {SubcountSeries[]} records - Record count series for this category
 * @property {SubcountSeries[]} parents - Parent count series for this category
 * @property {SubcountSeries[]} uploaders - Uploader count series for this category
 * @property {SubcountSeries[]} fileCount - File count series for this category
 * @property {SubcountSeries[]} dataVolume - Data volume series for this category
 *
 * @typedef {Object} SubcountUsageMetrics
 * @property {SubcountSeries[]} views - View count series for this category
 * @property {SubcountSeries[]} downloads - Download count series for this category
 * @property {SubcountSeries[]} visitors - Visitor count series for this category
 * @property {SubcountSeries[]} dataVolume - Data volume series for this category
 *
 * @typedef {Object} RecordDeltaData
 * @property {RecordSeries} global - Global record metrics
 * @property {SubcountMetrics} byFilePresence - Record metrics by file presence
 * @property {SubcountMetrics} resourceTypes
 * @property {SubcountMetrics} accessRights
 * @property {SubcountMetrics} languages
 * @property {SubcountMetrics} affiliations
 * @property {SubcountMetrics} funders
 * @property {SubcountMetrics} subjects
 * @property {SubcountMetrics} publishers
 * @property {SubcountMetrics} periodicals
 * @property {SubcountMetrics} licenses
 * @property {SubcountMetrics} fileTypes
 *
 * @typedef {Object} RecordSnapshotData
 * @property {RecordSeries} global - Global record metrics
 * @property {SubcountMetrics} byFilePresence - Record metrics by file presence
 * @property {SubcountMetrics} resourceTypes
 * @property {SubcountMetrics} accessRights
 * @property {SubcountMetrics} languages
 * @property {SubcountMetrics} affiliations
 * @property {SubcountMetrics} funders
 * @property {SubcountMetrics} subjects
 * @property {SubcountMetrics} publishers
 * @property {SubcountMetrics} periodicals
 * @property {SubcountMetrics} licenses
 * @property {SubcountMetrics} fileTypes
 *
 * @typedef {Object} UsageDeltaData
 * @property {UsageSeries} global - Global usage metrics
 * @property {SubcountUsageMetrics} byFilePresence - Usage metrics by file presence
 * @property {SubcountUsageMetrics} byAccessRights
 * @property {SubcountUsageMetrics} byFileTypes
 * @property {SubcountUsageMetrics} byLanguages
 * @property {SubcountUsageMetrics} byResourceTypes
 * @property {SubcountUsageMetrics} bySubjects
 * @property {SubcountUsageMetrics} byPublishers
 * @property {SubcountUsageMetrics} byLicenses
 * @property {SubcountUsageMetrics} byCountries
 * @property {SubcountUsageMetrics} byReferrers
 * @property {SubcountUsageMetrics} byAffiliations
 *
 * @typedef {Object} UsageSnapshotData
 * @property {UsageSeries} global - Global usage metrics
 * @property {SubcountUsageMetrics} byFilePresence - Usage metrics by file presence
 * @property {SubcountUsageMetrics} byAccessRights
 * @property {SubcountUsageMetrics} byFileTypes
 * @property {SubcountUsageMetrics} byLanguages
 * @property {SubcountUsageMetrics} byResourceTypes
 * @property {SubcountUsageMetrics} bySubjects
 * @property {SubcountUsageMetrics} byPublishers
 * @property {SubcountUsageMetrics} byLicenses
 * @property {SubcountUsageMetrics} byCountries
 * @property {SubcountUsageMetrics} byReferrers
 * @property {SubcountUsageMetrics} byAffiliations
 * @property {SubcountUsageMetrics} topCountriesByView
 * @property {SubcountUsageMetrics} topCountriesByDownload
 * @property {SubcountUsageMetrics} topSubjectsByView
 * @property {SubcountUsageMetrics} topSubjectsByDownload
 * @property {SubcountUsageMetrics} topPublishersByView
 * @property {SubcountUsageMetrics} topPublishersByDownload
 * @property {SubcountUsageMetrics} topLicensesByView
 * @property {SubcountUsageMetrics} topLicensesByDownload
 * @property {SubcountUsageMetrics} topReferrersByView
 * @property {SubcountUsageMetrics} topReferrersByDownload
 * @property {SubcountUsageMetrics} topAffiliationsByView
 * @property {SubcountUsageMetrics} topAffiliationsByDownload
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
    accessRights: {
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
    'by_access_rights': 'accessRights',
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
    const added = item.added.metadata_only + item.added.with_files;
    const removed = item.removed.metadata_only + item.removed.with_files;
    return added - removed;
  };

  const getNetFileCount = (item) => {
    const added = item.added.file_count;
    const removed = item.removed.file_count;
    return added - removed;
  };

  const getNetDataVolume = (item) => {
    const added = item.added.data_volume;
    const removed = item.removed.data_volume;
    return added - removed;
  };

  if (deltaDocs && Array.isArray(deltaDocs)) {
    const byFilePresenceDataPoints = [];

    deltaDocs.forEach(doc => {
      const source = doc._source;
      const date = source.period_start.split('T')[0];

      // Accumulate global data points
      deltaData.global.records.push(createChartDataPoint(date, getNetCount(source.records)));
      deltaData.global.parents.push(createChartDataPoint(date, getNetCount(source.parents)));
      deltaData.global.uploaders.push(createChartDataPoint(date, source.uploaders));
      deltaData.global.fileCount.push(createChartDataPoint(date, getNetFileCount(source.files)));
      deltaData.global.dataVolume.push(createChartDataPoint(date, getNetDataVolume(source.files), 'filesize'));

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
                  value = getNetCount(item.records);
                  break;
                case 'parents':
                  value = getNetCount(item.parents);
                  break;
                case 'uploaders':
                  value = item.uploaders || 0;
                  break;
                case 'fileCount':
                  value = getNetFileCount(item.files);
                  break;
                case 'dataVolume':
                  value = getNetDataVolume(item.files);
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
    const byFilePresenceMetrics = ['records', 'parents', 'uploaders', 'fileCount', 'dataVolume'];
    byFilePresenceMetrics.forEach(metricType => {
      const dataPoints = byFilePresenceDataPoints.map(dp => ({
        date: dp.date,
        withFiles: dp.withFiles,
        withoutFiles: dp.withoutFiles
      }));
      deltaData.byFilePresence[metricType] = createSubcountSeriesArray(['withFiles', 'withoutFiles'], dataPoints);
    });

    // Create subcount series for each metric type
    Object.keys(subcountTypes).forEach(subcountType => {
      const targetKey = subcountTypes[subcountType];
      if (deltaData[`${targetKey}Items`] && deltaData[`${targetKey}DataPoints`]) {
        const metricTypes = ['records', 'parents', 'uploaders', 'fileCount', 'dataVolume'];
        metricTypes.forEach(metricType => {
          const valueType = metricType === 'dataVolume' ? 'filesize' : 'number';
          deltaData[targetKey][metricType] = createSubcountSeriesFromItems(
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
    accessRights: {
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
    'all_access_rights': 'accessRights',
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
    return item.metadata_only + item.with_files;
  };

  const getTotalFileCount = (item) => {
    return item.file_count;
  };

  const getTotalDataVolume = (item) => {
    return item.data_volume;
  };

  if (snapshotDocs && Array.isArray(snapshotDocs)) {
    const byFilePresenceDataPoints = [];

    snapshotDocs.forEach(doc => {
      const source = doc._source;
      const date = source.snapshot_date.split('T')[0];

      // Accumulate global data points
      snapshotData.global.records.push(createChartDataPoint(date, getTotalCount(source.total_records)));
      snapshotData.global.parents.push(createChartDataPoint(date, getTotalCount(source.total_parents)));
      snapshotData.global.uploaders.push(createChartDataPoint(date, source.total_uploaders));
      snapshotData.global.fileCount.push(createChartDataPoint(date, getTotalFileCount(source.total_files)));
      snapshotData.global.dataVolume.push(createChartDataPoint(date, getTotalDataVolume(source.total_files), 'filesize'));

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
                  value = getTotalCount(item.total_records);
                  break;
                case 'parents':
                  value = getTotalCount(item.total_parents);
                  break;
                case 'uploaders':
                  value = item.total_uploaders || 0;
                  break;
                case 'fileCount':
                  value = getTotalFileCount(item.total_files);
                  break;
                case 'dataVolume':
                  value = getTotalDataVolume(item.total_files);
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
      snapshotData.byFilePresence[metricType] = createSubcountSeriesArray(['withFiles', 'withoutFiles'], dataPoints);
    });

    // Create subcount series for each metric type
    Object.keys(subcountTypes).forEach(subcountType => {
      const targetKey = subcountTypes[subcountType];
      if (snapshotData[`${targetKey}Items`] && snapshotData[`${targetKey}DataPoints`]) {
        const metricTypes = ['records', 'parents', 'uploaders', 'fileCount', 'dataVolume'];
        metricTypes.forEach(metricType => {
          const valueType = metricType === 'dataVolume' ? 'filesize' : 'number';
          snapshotData[targetKey][metricType] = createSubcountSeriesFromItems(
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
    byAccessRights: {
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
    'by_access_rights': 'byAccessRights',
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
    return item.view ? item.view.total_events : 0;
  };

  const getNetDownloadEvents = (item) => {
    return item.download ? item.download.total_events : 0;
  };

  const getNetVisitors = (item) => {
    const viewVisitors = item.view ? item.view.unique_visitors : 0;
    const downloadVisitors = item.download ? item.download.unique_visitors : 0;
    return Math.max(viewVisitors, downloadVisitors);
  };

  const getNetDataVolume = (item) => {
    return item.download ? item.download.total_volume : 0;
  };

  if (deltaDocs && Array.isArray(deltaDocs)) {
    const byFilePresenceDataPoints = [];

    deltaDocs.forEach(doc => {
      const source = doc._source;
      const date = source.period_start.split('T')[0];

      // Accumulate global data points
      deltaData.global.views.push(createChartDataPoint(date, getNetViewEvents(source.totals)));
      deltaData.global.downloads.push(createChartDataPoint(date, getNetDownloadEvents(source.totals)));
      deltaData.global.visitors.push(createChartDataPoint(date, getNetVisitors(source.totals)));
      deltaData.global.dataVolume.push(createChartDataPoint(date, getNetDataVolume(source.totals), 'filesize'));

      // Collect byFilePresence data points
      byFilePresenceDataPoints.push({
        date,
        withFiles: getNetViewEvents(source.totals.with_files),
        withoutFiles: getNetViewEvents(source.totals.metadata_only)
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
      deltaData.byFilePresence[metricType] = createSubcountSeriesArray(['withFiles', 'withoutFiles'], dataPoints);
    });

    // Create subcount series for each metric type
    Object.keys(subcountTypes).forEach(subcountType => {
      const targetKey = subcountTypes[subcountType];
      if (deltaData[`${targetKey}Items`] && deltaData[`${targetKey}DataPoints`]) {
        const metricTypes = ['views', 'downloads', 'visitors', 'dataVolume'];
        metricTypes.forEach(metricType => {
          const valueType = metricType === 'dataVolume' ? 'filesize' : 'number';
          deltaData[targetKey][metricType] = createSubcountSeriesFromItems(
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
    byAccessRights: {
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
    'all_access_rights': 'byAccessRights',
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
    'top_countries': { view: 'topCountriesByView', download: 'topCountriesByDownload' },
    'top_subjects': { view: 'topSubjectsByView', download: 'topSubjectsByDownload' },
    'top_publishers': { view: 'topPublishersByView', download: 'topPublishersByDownload' },
    'top_licenses': { view: 'topLicensesByView', download: 'topLicensesByDownload' },
    'top_referrers': { view: 'topReferrersByView', download: 'topReferrersByDownload' },
    'top_affiliations': { view: 'topAffiliationsByView', download: 'topAffiliationsByDownload' },
  };

  const getTotalViewEvents = (item) => {
    return item.view ? item.view.total_events : 0;
  };

  const getTotalDownloadEvents = (item) => {
    return item.download ? item.download.total_events : 0;
  };

  const getTotalVisitors = (item) => {
    const viewVisitors = item.view ? item.view.unique_visitors : 0;
    const downloadVisitors = item.download ? item.download.unique_visitors : 0;
    return Math.max(viewVisitors, downloadVisitors);
  };

  const getTotalDataVolume = (item) => {
    return item.download ? item.download.total_volume : 0;
  };

  if (snapshotDocs && Array.isArray(snapshotDocs)) {
    const byFilePresenceDataPoints = [];

    snapshotDocs.forEach(doc => {
      const source = doc._source;
      const date = source.snapshot_date.split('T')[0];

      // Accumulate global data points
      snapshotData.global.views.push(createChartDataPoint(date, getTotalViewEvents(source.totals)));
      snapshotData.global.downloads.push(createChartDataPoint(date, getTotalDownloadEvents(source.totals)));
      snapshotData.global.visitors.push(createChartDataPoint(date, getTotalVisitors(source.totals)));
      snapshotData.global.dataVolume.push(createChartDataPoint(date, getTotalDataVolume(source.totals), 'filesize'));

      // Collect byFilePresence data points
      byFilePresenceDataPoints.push({
        date,
        withFiles: getTotalViewEvents(source.totals.with_files),
        withoutFiles: getTotalViewEvents(source.totals.metadata_only)
      });

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
          } else {
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

    // Create byFilePresence series for each metric type
    const byFilePresenceMetrics = ['views', 'downloads', 'visitors', 'dataVolume'];
    byFilePresenceMetrics.forEach(metricType => {
      const dataPoints = byFilePresenceDataPoints.map(dp => ({
        date: dp.date,
        withFiles: dp.withFiles,
        withoutFiles: dp.withoutFiles
      }));
      snapshotData.byFilePresence[metricType] = createSubcountSeriesArray(['withFiles', 'withoutFiles'], dataPoints);
    });

    // Create subcount series for each metric type
    Object.keys(subcountTypes).forEach(subcountType => {
      const targetKey = subcountTypes[subcountType];
      if (snapshotData[`${targetKey}Items`] && snapshotData[`${targetKey}DataPoints`]) {
        const metricTypes = ['views', 'downloads', 'visitors', 'dataVolume'];
        metricTypes.forEach(metricType => {
          const valueType = metricType === 'dataVolume' ? 'filesize' : 'number';
          snapshotData[targetKey][metricType] = createSubcountSeriesFromItems(
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
            snapshotData[separateKey][metricType] = createSubcountSeriesFromItems(
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

  // Convert aggregated subcounts to arrays and calculate percentages
  // const totalRecords = recordCount.reduce((sum, item) => sum + item.value, 0);
  // const maxTotalRecords = cumulativeRecordCount.length > 0
  //   ? Math.max(...cumulativeRecordCount.map(item => item.value))
  //   : 0;

  // // Use the higher of the two totals for percentage calculations
  // const percentageBase = Math.max(totalRecords, maxTotalRecords);

  // const licenses = Object.values(subcountAggregates.licenses)
  //   .sort((a, b) => b.count - a.count)
  //   .map(item => ({
  //     ...item,
  //     percentage: percentageBase > 0 ? Math.round((item.count / percentageBase) * 100) : 0
  //   }));

  return returnData;
    // Empty arrays for data not available in record data
    // topCountries: [],
    // referrerDomains: [],
    // mostDownloadedRecords: [],
    // mostViewedRecords: []
};


