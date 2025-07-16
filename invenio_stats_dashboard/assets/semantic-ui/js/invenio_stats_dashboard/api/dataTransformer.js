/**
 * Transform daily record delta aggregation documents for display in the dashboard.
 *
 * @param {Array} deltaDocs - Array of daily record delta aggregation documents
 *
 * The returned data is an object containing the arrays of data points for each
 * time series metric used by the dashboard components. The data points are
 * in the shape of {
 *  date,
 *  readableDate,
 *  global: {
 *    records: [date, value, label],
 *    parents: [date, value, label],
 *    uploaders: [date, value, label],
 *    fileCount: [date, value, label],
 *    dataVolume: [date, value, label],
 *  },
 *  byFilePresence: {
 *    withFiles: {
 *      records: [date, value, label],
 *      parents: [date, value, label],
 *      files: [date, value, label],
 *      dataVolume: [date, value, label],
 *    },
 *    withoutFiles: {
 *      records: [date, value, label],
 *      parents: [date, value, label],
 *    },
 *  },
 *  resourceTypes: {
 *    id: [date, value, label],
 *  },
 *  accessRights: {
 *    id: [date, value, label],
 *  },
 *  languages: {
 *    id: [date, value, label],
 *  },
 *  affiliations: {
 *    id: [date, value, label],
 *  },
 *  funders: {
 *    id: [date, value, label],
 *  },
 *  subjects: {
 *    id: [date, value, label],
 *  },
 *  publishers: {
 *    id: [date, value, label],
 *  },
 *  periodicals: {
 *    id: [date, value, label],
 *  },
 *  licenses: {
 *    id: [date, value, label],
 *  },
 *  fileTypes: {
 *    id: [date, value, label],
 *  },
 * }.
 *
 * @returns {Object} Transformed data in the format expected by testStatsData
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
      withFiles: {
        records: [],
        parents: [],
        files: [],
        dataVolume: [],
      },
      withoutFiles: {
        records: [],
        parents: [],
      },
    },
    accessRights: {},
    languages: {},
    affiliations: {},
    funders: {},
    subjects: {},
    publishers: {},
    periodicals: {},
    licenses: {},
    fileTypes: {},
    resourceTypes: {},
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
    deltaDocs.forEach(doc => {
      const source = doc._source;
      const date = source.period_start.split('T')[0];
      const readableDate = new Date(date).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });

      // Accumulate global data points
      deltaData.global.records.push([date, getNetCount(source.records)]);
      deltaData.global.parents.push([date, getNetCount(source.parents)]);
      deltaData.global.uploaders.push([date, source.uploaders]);
      deltaData.global.fileCount.push([date, getNetFileCount(source.files)]);
      deltaData.global.dataVolume.push([date, getNetDataVolume(source.files)]);

      // Accumulate byFilePresence data points
      deltaData.byFilePresence.withFiles.records.push([date, getNetCount(source.records.added)]);
      deltaData.byFilePresence.withFiles.parents.push([date, getNetCount(source.parents.added)]);
      deltaData.byFilePresence.withFiles.files.push([date, getNetFileCount(source.files.added)]);
      deltaData.byFilePresence.withFiles.dataVolume.push([date, getNetDataVolume(source.files.added)]);
      deltaData.byFilePresence.withoutFiles.records.push([date, getNetCount(source.records.removed)]);
      deltaData.byFilePresence.withoutFiles.parents.push([date, getNetCount(source.parents.removed)]);

      Object.keys(subcountTypes).forEach(subcountType => {
        const subcountSeries = source.subcounts[subcountType]
        if (subcountSeries.length > 0) {
          const targetKey = subcountTypes[subcountType];
          if (!deltaData[targetKey]) {
            deltaData[targetKey] = {};
          }

          subcountSeries.forEach(item => {
            if (!deltaData[targetKey][item.id]) {
              deltaData[targetKey][item.id] = {
                records: [],
                parents: [],
                files: [],
                dataVolume: [],
              };
            }

            deltaData[targetKey][item.id].records.push([date, getNetCount(item.records), item.label || item.id]);
            deltaData[targetKey][item.id].parents.push([date, getNetCount(item.parents), item.label || item.id]);
            deltaData[targetKey][item.id].files.push([date, getNetFileCount(item.files), item.label || item.id]);
            deltaData[targetKey][item.id].dataVolume.push([date, getNetDataVolume(item.files), item.label || item.id]);
          });
        }
      });
    });
  }

  return deltaData;
};

/**
 * Transform daily record snapshot aggregation documents for display in the dashboard.
 *
 * @param {Array} snapshotDocs - Array of daily record snapshot aggregation documents
 *
 * The returned data is an object containing the arrays of data points for each
 * time series metric used by the dashboard components. The data points are
 * in the shape of {
 *  date,
 *  readableDate,
 *  global: {
 *    records: [date, value, label],
 *    parents: [date, value, label],
 *    uploaders: [date, value, label],
 *    fileCount: [date, value, label],
 *    dataVolume: [date, value, label],
 *  },
 *  byFilePresence: {
 *    withFiles: {
 *      records: [date, value, label],
 *      parents: [date, value, label],
 *      files: [date, value, label],
 *      dataVolume: [date, value, label],
 *    },
 *    withoutFiles: {
 *      records: [date, value, label],
 *      parents: [date, value, label],
 *    },
 *  },
 *  resourceTypes: {
 *    id: [date, value, label],
 *  },
 *  accessRights: {
 *    id: [date, value, label],
 *  },
 *  languages: {
 *    id: [date, value, label],
 *  },
 *  affiliations: {
 *    id: [date, value, label],
 *  },
 *  funders: {
 *    id: [date, value, label],
 *  },
 *  subjects: {
 *    id: [date, value, label],
 *  },
 *  publishers: {
 *    id: [date, value, label],
 *  },
 *  periodicals: {
 *    id: [date, value, label],
 *  },
 *  licenses: {
 *    id: [date, value, label],
 *  },
 *  fileTypes: {
 *    id: [date, value, label],
 *  },
 * }.
 *
 * @returns {Object} Transformed data in the format expected by testStatsData
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
      withFiles: {
        records: [],
        parents: [],
        files: [],
        dataVolume: [],
      },
      withoutFiles: {
        records: [],
        parents: [],
      },
    },
    accessRights: {},
    languages: {},
    affiliations: {},
    funders: {},
    subjects: {},
    publishers: {},
    periodicals: {},
    licenses: {},
    fileTypes: {},
    resourceTypes: {},
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
    snapshotDocs.forEach(doc => {
      const source = doc._source;
      const date = source.snapshot_date.split('T')[0];
      const readableDate = new Date(date).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });

      // Accumulate global data points
      snapshotData.global.records.push([date, getTotalCount(source.total_records)]);
      snapshotData.global.parents.push([date, getTotalCount(source.total_parents)]);
      snapshotData.global.uploaders.push([date, source.total_uploaders]);
      snapshotData.global.fileCount.push([date, getTotalFileCount(source.total_files)]);
      snapshotData.global.dataVolume.push([date, getTotalDataVolume(source.total_files)]);

      // Accumulate byFilePresence data points
      snapshotData.byFilePresence.withFiles.records.push([date, source.total_records.with_files]);
      snapshotData.byFilePresence.withFiles.parents.push([date, source.total_parents.with_files]);
      snapshotData.byFilePresence.withFiles.files.push([date, getTotalFileCount(source.total_files)]);
      snapshotData.byFilePresence.withFiles.dataVolume.push([date, getTotalDataVolume(source.total_files)]);
      snapshotData.byFilePresence.withoutFiles.records.push([date, source.total_records.metadata_only]);
      snapshotData.byFilePresence.withoutFiles.parents.push([date, source.total_parents.metadata_only]);

      Object.keys(subcountTypes).forEach(subcountType => {
        const subcountSeries = source.subcounts[subcountType]
        if (subcountSeries && subcountSeries.length > 0) {
          const targetKey = subcountTypes[subcountType];
          if (!snapshotData[targetKey]) {
            snapshotData[targetKey] = {};
          }

          subcountSeries.forEach(item => {
            if (!snapshotData[targetKey][item.id]) {
              snapshotData[targetKey][item.id] = {
                records: [],
                parents: [],
                files: [],
                dataVolume: [],
              };
            }

            snapshotData[targetKey][item.id].records.push([date, getTotalCount(item.records), item.label || item.id]);
            snapshotData[targetKey][item.id].parents.push([date, getTotalCount(item.parents), item.label || item.id]);
            snapshotData[targetKey][item.id].files.push([date, getTotalFileCount(item.files), item.label || item.id]);
            snapshotData[targetKey][item.id].dataVolume.push([date, getTotalDataVolume(item.files), item.label || item.id]);
          });
        }
      });
    });
  }

  return snapshotData;
};

/**
 * Transform daily usage delta aggregation documents for display in the dashboard.
 *
 * @param {Array} deltaDocs - Array of daily usage delta aggregation documents
 *
 * The returned data is an object containing the arrays of data points for each
 * time series metric used by the dashboard components. The data points are
 * in the shape of {
 *  date,
 *  readableDate,
 *  global: {
 *    views: [date, value, label],
 *    downloads: [date, value, label],
 *    visitors: [date, value, label],
 *    dataVolume: [date, value, label],
 *  },
 *  byAccessRights: {
 *    id: {
 *      views: [date, value, label],
 *      downloads: [date, value, label],
 *      visitors: [date, value, label],
 *      dataVolume: [date, value, label],
 *    },
 *  },
 *  byFileTypes: {
 *    id: {
 *      views: [date, value, label],
 *      downloads: [date, value, label],
 *      visitors: [date, value, label],
 *      dataVolume: [date, value, label],
 *    },
 *  },
 *  byLanguages: {
 *    id: {
 *      views: [date, value, label],
 *      downloads: [date, value, label],
 *      visitors: [date, value, label],
 *      dataVolume: [date, value, label],
 *    },
 *  },
 *  byResourceTypes: {
 *    id: {
 *      views: [date, value, label],
 *      downloads: [date, value, label],
 *      visitors: [date, value, label],
 *      dataVolume: [date, value, label],
 *    },
 *  },
 *  bySubjects: {
 *    id: {
 *      views: [date, value, label],
 *      downloads: [date, value, label],
 *      visitors: [date, value, label],
 *      dataVolume: [date, value, label],
 *    },
 *  },
 *  byPublishers: {
 *    id: {
 *      views: [date, value, label],
 *      downloads: [date, value, label],
 *      visitors: [date, value, label],
 *      dataVolume: [date, value, label],
 *    },
 *  },
 *  byLicenses: {
 *    id: {
 *      views: [date, value, label],
 *      downloads: [date, value, label],
 *      visitors: [date, value, label],
 *      dataVolume: [date, value, label],
 *    },
 *  },
 *  byCountries: {
 *    id: {
 *      views: [date, value, label],
 *      downloads: [date, value, label],
 *      visitors: [date, value, label],
 *      dataVolume: [date, value, label],
 *    },
 *  },
 *  byReferrers: {
 *    id: {
 *      views: [date, value, label],
 *      downloads: [date, value, label],
 *      visitors: [date, value, label],
 *      dataVolume: [date, value, label],
 *    },
 *  },
 *  byAffiliations: {
 *    id: {
 *      views: [date, value, label],
 *      downloads: [date, value, label],
 *      visitors: [date, value, label],
 *      dataVolume: [date, value, label],
 *    },
 *  },
 * }.
 *
 * @returns {Object} Transformed data in the format expected by testStatsData
 */
const transformUsageDeltaData = (deltaDocs) => {

  const deltaData = {
    global: {
      views: [],
      downloads: [],
      visitors: [],
      dataVolume: [],
    },
    byAccessRights: {},
    byFileTypes: {},
    byLanguages: {},
    byResourceTypes: {},
    bySubjects: {},
    byPublishers: {},
    byLicenses: {},
    byCountries: {},
    byReferrers: {},
    byAffiliations: {},
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
    deltaDocs.forEach(doc => {
      const source = doc._source;
      const date = source.period_start.split('T')[0];
      const readableDate = new Date(date).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });

      // Accumulate global data points
      deltaData.global.views.push([date, getNetViewEvents(source.totals)]);
      deltaData.global.downloads.push([date, getNetDownloadEvents(source.totals)]);
      deltaData.global.visitors.push([date, getNetVisitors(source.totals)]);
      deltaData.global.dataVolume.push([date, getNetDataVolume(source.totals)]);

      Object.keys(subcountTypes).forEach(subcountType => {
        const subcountSeries = source.subcounts[subcountType]
        if (subcountSeries && subcountSeries.length > 0) {
          const targetKey = subcountTypes[subcountType];
          if (!deltaData[targetKey]) {
            deltaData[targetKey] = {};
          }

          subcountSeries.forEach(item => {
            if (!deltaData[targetKey][item.id]) {
              deltaData[targetKey][item.id] = {
                views: [],
                downloads: [],
                visitors: [],
                dataVolume: [],
              };
            }

            deltaData[targetKey][item.id].views.push([date, getNetViewEvents(item), item.label || item.id]);
            deltaData[targetKey][item.id].downloads.push([date, getNetDownloadEvents(item), item.label || item.id]);
            deltaData[targetKey][item.id].visitors.push([date, getNetVisitors(item), item.label || item.id]);
            deltaData[targetKey][item.id].dataVolume.push([date, getNetDataVolume(item), item.label || item.id]);
          });
        }
      });
    });
  }

  return deltaData;
};

/**
 * Transform daily usage snapshot aggregation documents for display in the dashboard.
 *
 * @param {Array} snapshotDocs - Array of daily usage snapshot aggregation documents
 *
 * The returned data is an object containing the arrays of data points for each
 * time series metric used by the dashboard components. The data points are
 * in the shape of {
 *  date,
 *  readableDate,
 *  global: {
 *    views: [date, value, label],
 *    downloads: [date, value, label],
 *    visitors: [date, value, label],
 *    dataVolume: [date, value, label],
 *  },
 *  byAccessRights: {
 *    id: {
 *      views: [date, value, label],
 *      downloads: [date, value, label],
 *      visitors: [date, value, label],
 *      dataVolume: [date, value, label],
 *    },
 *  },
 *  byFileTypes: {
 *    id: {
 *      views: [date, value, label],
 *      downloads: [date, value, label],
 *      visitors: [date, value, label],
 *      dataVolume: [date, value, label],
 *    },
 *  },
 *  byLanguages: {
 *    id: {
 *      views: [date, value, label],
 *      downloads: [date, value, label],
 *      visitors: [date, value, label],
 *      dataVolume: [date, value, label],
 *    },
 *  },
 *  byResourceTypes: {
 *    id: {
 *      views: [date, value, label],
 *      downloads: [date, value, label],
 *      visitors: [date, value, label],
 *      dataVolume: [date, value, label],
 *    },
 *  },
 *  bySubjects: {
 *    id: {
 *      views: [date, value, label],
 *      downloads: [date, value, label],
 *      visitors: [date, value, label],
 *      dataVolume: [date, value, label],
 *    },
 *  },
 *  byPublishers: {
 *    id: {
 *      views: [date, value, label],
 *      downloads: [date, value, label],
 *      visitors: [date, value, label],
 *      dataVolume: [date, value, label],
 *    },
 *  },
 *  byLicenses: {
 *    id: {
 *      views: [date, value, label],
 *      downloads: [date, value, label],
 *      visitors: [date, value, label],
 *      dataVolume: [date, value, label],
 *    },
 *  },
 *  byCountries: {
 *    id: {
 *      views: [date, value, label],
 *      downloads: [date, value, label],
 *      visitors: [date, value, label],
 *      dataVolume: [date, value, label],
 *    },
 *  },
 *  byReferrers: {
 *    id: {
 *      views: [date, value, label],
 *      downloads: [date, value, label],
 *      visitors: [date, value, label],
 *      dataVolume: [date, value, label],
 *    },
 *  },
 *  byAffiliations: {
 *    id: {
 *      views: [date, value, label],
 *      downloads: [date, value, label],
 *      visitors: [date, value, label],
 *      dataVolume: [date, value, label],
 *    },
 *  },
 * }.
 *
 * @returns {Object} Transformed data in the format expected by testStatsData
 */
const transformUsageSnapshotData = (snapshotDocs) => {

  const snapshotData = {
    global: {
      views: [],
      downloads: [],
      visitors: [],
      dataVolume: [],
    },
    byAccessRights: {},
    byFileTypes: {},
    byLanguages: {},
    byResourceTypes: {},
    bySubjects: {},
    byPublishers: {},
    byLicenses: {},
    byCountries: {},
    byReferrers: {},
    byAffiliations: {},
    // Separate properties for view-based and download-based data
    byCountriesByView: {},
    byCountriesByDownload: {},
    bySubjectsByView: {},
    bySubjectsByDownload: {},
    byPublishersByView: {},
    byPublishersByDownload: {},
    byLicensesByView: {},
    byLicensesByDownload: {},
    byReferrersByView: {},
    byReferrersByDownload: {},
    byAffiliationsByView: {},
    byAffiliationsByDownload: {},
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
    'top_countries': { view: 'byCountriesByView', download: 'byCountriesByDownload' },
    'top_subjects': { view: 'bySubjectsByView', download: 'bySubjectsByDownload' },
    'top_publishers': { view: 'byPublishersByView', download: 'byPublishersByDownload' },
    'top_licenses': { view: 'byLicensesByView', download: 'byLicensesByDownload' },
    'top_referrers': { view: 'byReferrersByView', download: 'byReferrersByDownload' },
    'top_affiliations': { view: 'byAffiliationsByView', download: 'byAffiliationsByDownload' },
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
    snapshotDocs.forEach(doc => {
      const source = doc._source;
      const date = source.snapshot_date.split('T')[0];
      const readableDate = new Date(date).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });

      // Accumulate global data points
      snapshotData.global.views.push([date, getTotalViewEvents(source.totals)]);
      snapshotData.global.downloads.push([date, getTotalDownloadEvents(source.totals)]);
      snapshotData.global.visitors.push([date, getTotalVisitors(source.totals)]);
      snapshotData.global.dataVolume.push([date, getTotalDataVolume(source.totals)]);

      Object.keys(subcountTypes).forEach(subcountType => {
        const subcountSeries = source.subcounts[subcountType]
        if (subcountSeries) {
          const targetKey = subcountTypes[subcountType];
          if (!snapshotData[targetKey]) {
            snapshotData[targetKey] = {};
          }

          // Handle different subcount structures
          if (Array.isArray(subcountSeries)) {
            // Simple array structure (all_* fields)
            if (subcountSeries.length > 0) {
              subcountSeries.forEach(item => {
                if (!snapshotData[targetKey][item.id]) {
                  snapshotData[targetKey][item.id] = {
                    views: [],
                    downloads: [],
                    visitors: [],
                    dataVolume: [],
                  };
                }

                snapshotData[targetKey][item.id].views.push([date, getTotalViewEvents(item), item.label || item.id]);
                snapshotData[targetKey][item.id].downloads.push([date, getTotalDownloadEvents(item), item.label || item.id]);
                snapshotData[targetKey][item.id].visitors.push([date, getTotalVisitors(item), item.label || item.id]);
                snapshotData[targetKey][item.id].dataVolume.push([date, getTotalDataVolume(item), item.label || item.id]);
              });
            }
          } else if (typeof subcountSeries === 'object' && subcountSeries !== null) {
            // Complex object structure with by_view and by_download (top_* fields)
            const separateMapping = separateSubcountTypes[subcountType];

            if (separateMapping) {
              // Handle separate view and download data for "top" subcounts

              // Process by_view data
              if (subcountSeries.by_view && Array.isArray(subcountSeries.by_view)) {
                const viewKey = separateMapping.view;
                if (!snapshotData[viewKey]) {
                  snapshotData[viewKey] = {};
                }

                subcountSeries.by_view.forEach(item => {
                  if (!snapshotData[viewKey][item.id]) {
                    snapshotData[viewKey][item.id] = {
                      views: [],
                      visitors: [],
                    };
                  }

                  snapshotData[viewKey][item.id].views.push([date, getTotalViewEvents(item), item.label || item.id]);
                  snapshotData[viewKey][item.id].visitors.push([date, getTotalVisitors(item), item.label || item.id]);
                });
              }

              // Process by_download data
              if (subcountSeries.by_download && Array.isArray(subcountSeries.by_download)) {
                const downloadKey = separateMapping.download;
                if (!snapshotData[downloadKey]) {
                  snapshotData[downloadKey] = {};
                }

                subcountSeries.by_download.forEach(item => {
                  if (!snapshotData[downloadKey][item.id]) {
                    snapshotData[downloadKey][item.id] = {
                      downloads: [],
                      dataVolume: [],
                    };
                  }

                  snapshotData[downloadKey][item.id].downloads.push([date, getTotalDownloadEvents(item), item.label || item.id]);
                  snapshotData[downloadKey][item.id].dataVolume.push([date, getTotalDataVolume(item), item.label || item.id]);
                });
              }
            } else {
              // Fallback for non-"top" subcounts that might have this structure
              // Process by_view data
              if (subcountSeries.by_view && Array.isArray(subcountSeries.by_view)) {
                subcountSeries.by_view.forEach(item => {
                  if (!snapshotData[targetKey][item.id]) {
                    snapshotData[targetKey][item.id] = {
                      views: [],
                      downloads: [],
                      visitors: [],
                      dataVolume: [],
                    };
                  }

                  snapshotData[targetKey][item.id].views.push([date, getTotalViewEvents(item), item.label || item.id]);
                  snapshotData[targetKey][item.id].visitors.push([date, getTotalVisitors(item), item.label || item.id]);
                });
              }

              // Process by_download data
              if (subcountSeries.by_download && Array.isArray(subcountSeries.by_download)) {
                subcountSeries.by_download.forEach(item => {
                  if (!snapshotData[targetKey][item.id]) {
                    snapshotData[targetKey][item.id] = {
                      views: [],
                      downloads: [],
                      visitors: [],
                      dataVolume: [],
                    };
                  }

                  snapshotData[targetKey][item.id].downloads.push([date, getTotalDownloadEvents(item), item.label || item.id]);
                  snapshotData[targetKey][item.id].dataVolume.push([date, getTotalDataVolume(item), item.label || item.id]);
                });
              }
            }
          }
        }
      });
    });
  }

  return snapshotData;
};

/**
 * Transform daily record delta and snapshot aggregation documents into the format expected by test data components.
 *
 * @param {Object} rawStats - The raw stats object from the API containing record_deltas, record_snapshots, usage_deltas, usage_snapshots
 *
 * The returned data is an object containing the arrays of data points for each
 * time series metric used by the dashboard components. The data points are
 * in the shape of {date, value, resourceTypes, subjectHeadings}.
 *
 * @returns {Object} Transformed data in the format expected by ContentStatsChart and other components
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
