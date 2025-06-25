/**
 * Transform daily record delta and snapshot aggregation documents into the format expected by test data components.
 *
 * @param {Array} deltaDocs - Array of daily record delta aggregation documents
 * @param {Array} snapshotDocs - Array of daily cumulative snapshot aggregation documents
 * @returns {Object} Transformed data in the format expected by testStatsData
 */
export const transformRecordDataToTestData = (deltaDocs, snapshotDocs) => {
  // Initialize default return structure
  const defaultReturn = {
    recordCount: [],
    recordCountAdded: [],
    recordCountRemoved: [],
    parentCount: [],
    parentCountAdded: [],
    parentCountRemoved: [],
    uploaders: [],
    dataVolume: [],
    dataVolumeAdded: [],
    dataVolumeRemoved: [],
    dataVolumeByParents: [],
    dataVolumeByParentsAdded: [],
    dataVolumeByParentsRemoved: [],
    fileCount: [],
    fileCountAdded: [],
    fileCountRemoved: [],
    fileCountByParents: [],
    fileCountByParentsAdded: [],
    fileCountByParentsRemoved: [],
    views: [],
    downloads: [],
    traffic: [],
    cumulativeRecordCount: [],
    cumulativeUploaders: [],
    cumulativeDataVolume: [],
    cumulativeViews: [],
    cumulativeDownloads: [],
    cumulativeTraffic: [],
    licenses: [],
    affiliations: [],
    funders: [],
    use_binary_filesize: true,
    topCountries: [],
    accessRights: [],
    resourceTypes: [],
    referrerDomains: [],
    mostDownloadedRecords: [],
    mostViewedRecords: []
  };

  if ((!deltaDocs || !Array.isArray(deltaDocs)) && (!snapshotDocs || !Array.isArray(snapshotDocs))) {
    return defaultReturn;
  }

  // Transform daily deltas into time series data
  const recordCount = [];
  const recordCountAdded = [];
  const recordCountRemoved = [];
  const parentCount = [];
  const parentCountAdded = [];
  const parentCountRemoved = [];
  const uploaders = [];
  const dataVolume = [];
  const dataVolumeAdded = [];
  const dataVolumeRemoved = [];
  const dataVolumeByParents = [];
  const dataVolumeByParentsAdded = [];
  const dataVolumeByParentsRemoved = [];
  const fileCount = [];
  const fileCountAdded = [];
  const fileCountRemoved = [];
  const fileCountByParents = [];
  const fileCountByParentsAdded = [];
  const fileCountByParentsRemoved = [];
  const views = [];
  const downloads = [];
  const traffic = [];

  // Transform daily snapshots into cumulative time series data
  const cumulativeRecordCount = [];
  const cumulativeUploaders = [];
  const cumulativeDataVolume = [];
  const cumulativeViews = [];
  const cumulativeDownloads = [];
  const cumulativeTraffic = [];

  // Aggregate subcounts across all days
  const subcountAggregates = {
    licenses: {},
    affiliations: {},
    funders: {},
    accessRights: {},
    resourceTypes: {},
    referrerDomains: {},
    topCountries: {},
    languages: {},
    subjects: {},
    publishers: {},
    periodicals: {},
    userAgents: {},
    fileTypes: {}
  };

  // Process delta documents
  if (deltaDocs && Array.isArray(deltaDocs)) {
    deltaDocs.forEach(doc => {
      const source = doc._source;
      const date = source.period_start.split('T')[0]; // Extract date part

      // Calculate added and removed values separately for records
      const recordsAdded = source.records.added.metadata_only + source.records.added.with_files;
      const recordsRemoved = source.records.removed.metadata_only + source.records.removed.with_files;
      const netRecords = recordsAdded - recordsRemoved;

      // Calculate added and removed values separately for parents
      const parentsAdded = source.parents.added.metadata_only + source.parents.added.with_files;
      const parentsRemoved = source.parents.removed.metadata_only + source.parents.removed.with_files;
      const netParents = parentsAdded - parentsRemoved;

      // Calculate added and removed values separately for files
      const filesAdded = source.files.added.file_count;
      const filesRemoved = source.files.removed.file_count;
      const netFiles = filesAdded - filesRemoved;

      // Calculate added and removed values separately for data volume
      const dataVolumeAdded = source.files.added.data_volume;
      const dataVolumeRemoved = source.files.removed.data_volume;
      const netDataVolume = dataVolumeAdded - dataVolumeRemoved;

      // Calculate parent-based metrics from subcounts
      let dataVolumeByParentsAdded = 0;
      let dataVolumeByParentsRemoved = 0;
      let fileCountByParentsAdded = 0;
      let fileCountByParentsRemoved = 0;

      if (source.subcounts) {
        // Aggregate parent-based metrics from all subcount types
        const subcountTypes = [
          'by_resource_type', 'by_access_rights', 'by_language',
          'by_affiliation_creator', 'by_affiliation_contributor',
          'by_funder', 'by_subject', 'by_publisher', 'by_periodical',
          'by_license', 'by_file_type'
        ];

        subcountTypes.forEach(type => {
          if (source.subcounts[type]) {
            source.subcounts[type].forEach(item => {
              // Data volume by parents
              if (item.files && item.files.added && item.files.removed) {
                dataVolumeByParentsAdded += item.files.added.data_volume || 0;
                dataVolumeByParentsRemoved += item.files.removed.data_volume || 0;
              }

              // File count by parents
              if (item.files && item.files.added && item.files.removed) {
                fileCountByParentsAdded += item.files.added.file_count || 0;
                fileCountByParentsRemoved += item.files.removed.file_count || 0;
              }
            });
          }
        });
      }

      const netDataVolumeByParents = dataVolumeByParentsAdded - dataVolumeByParentsRemoved;
      const netFileCountByParents = fileCountByParentsAdded - fileCountByParentsRemoved;

      const netUploaders = source.uploaders;

      // Add daily data points for net values (record-based)
      recordCount.push({
        date,
        value: netRecords,
        resourceTypes: {},
        subjectHeadings: {}
      });

      uploaders.push({
        date,
        value: netUploaders,
        resourceTypes: {},
        subjectHeadings: {}
      });

      dataVolume.push({
        date,
        value: netDataVolume,
        resourceTypes: {},
        subjectHeadings: {}
      });

      parentCount.push({
        date,
        value: netParents,
        resourceTypes: {},
        subjectHeadings: {}
      });

      fileCount.push({
        date,
        value: netFiles,
        resourceTypes: {},
        subjectHeadings: {}
      });

      // Add daily data points for net values (parent-based)
      dataVolumeByParents.push({
        date,
        value: netDataVolumeByParents,
        resourceTypes: {},
        subjectHeadings: {}
      });

      fileCountByParents.push({
        date,
        value: netFileCountByParents,
        resourceTypes: {},
        subjectHeadings: {}
      });

      // Add daily data points for added values (record-based)
      recordCountAdded.push({
        date,
        value: recordsAdded,
        resourceTypes: {},
        subjectHeadings: {}
      });

      dataVolumeAdded.push({
        date,
        value: dataVolumeAdded,
        resourceTypes: {},
        subjectHeadings: {}
      });

      parentCountAdded.push({
        date,
        value: parentsAdded,
        resourceTypes: {},
        subjectHeadings: {}
      });

      fileCountAdded.push({
        date,
        value: filesAdded,
        resourceTypes: {},
        subjectHeadings: {}
      });

      // Add daily data points for added values (parent-based)
      dataVolumeByParentsAdded.push({
        date,
        value: dataVolumeByParentsAdded,
        resourceTypes: {},
        subjectHeadings: {}
      });

      fileCountByParentsAdded.push({
        date,
        value: fileCountByParentsAdded,
        resourceTypes: {},
        subjectHeadings: {}
      });

      // Add daily data points for removed values (record-based)
      recordCountRemoved.push({
        date,
        value: recordsRemoved,
        resourceTypes: {},
        subjectHeadings: {}
      });

      dataVolumeRemoved.push({
        date,
        value: dataVolumeRemoved,
        resourceTypes: {},
        subjectHeadings: {}
      });

      parentCountRemoved.push({
        date,
        value: parentsRemoved,
        resourceTypes: {},
        subjectHeadings: {}
      });

      fileCountRemoved.push({
        date,
        value: filesRemoved,
        resourceTypes: {},
        subjectHeadings: {}
      });

      // Add daily data points for removed values (parent-based)
      dataVolumeByParentsRemoved.push({
        date,
        value: dataVolumeByParentsRemoved,
        resourceTypes: {},
        subjectHeadings: {}
      });

      fileCountByParentsRemoved.push({
        date,
        value: fileCountByParentsRemoved,
        resourceTypes: {},
        subjectHeadings: {}
      });

      // Views and downloads are not available in record deltas, so use 0
      views.push({
        date,
        value: 0,
        resourceTypes: {},
        subjectHeadings: {}
      });

      downloads.push({
        date,
        value: 0,
        resourceTypes: {},
        subjectHeadings: {}
      });

      // Traffic is not available in record deltas, so use 0
      traffic.push({
        date,
        value: 0,
        resourceTypes: {},
        subjectHeadings: {}
      });

      // Aggregate subcounts from deltas
      if (source.subcounts) {
        // Process licenses
        if (source.subcounts.by_license) {
          source.subcounts.by_license.forEach(item => {
            const netCount = (item.records.added.metadata_only + item.records.added.with_files) -
                            (item.records.removed.metadata_only + item.records.removed.with_files);
            if (netCount > 0) {
              if (!subcountAggregates.licenses[item.id]) {
                subcountAggregates.licenses[item.id] = {
                  id: item.id,
                  name: item.label || item.id,
                  count: 0
                };
              }
              subcountAggregates.licenses[item.id].count += netCount;
            }
          });
        }

        // Process affiliations (creator and contributor)
        const allAffiliations = [
          ...(source.subcounts.by_affiliation_creator || []),
          ...(source.subcounts.by_affiliation_contributor || [])
        ];
        allAffiliations.forEach(item => {
          const netCount = (item.records.added.metadata_only + item.records.added.with_files) -
                          (item.records.removed.metadata_only + item.records.removed.with_files);
          if (netCount > 0) {
            if (!subcountAggregates.affiliations[item.id]) {
              subcountAggregates.affiliations[item.id] = {
                name: item.label || item.id,
                count: 0
              };
            }
            subcountAggregates.affiliations[item.id].count += netCount;
          }
        });

        // Process funders
        if (source.subcounts.by_funder) {
          source.subcounts.by_funder.forEach(item => {
            const netCount = (item.records.added.metadata_only + item.records.added.with_files) -
                            (item.records.removed.metadata_only + item.records.removed.with_files);
            if (netCount > 0) {
              if (!subcountAggregates.funders[item.id]) {
                subcountAggregates.funders[item.id] = {
                  name: item.label || item.id,
                  count: 0
                };
              }
              subcountAggregates.funders[item.id].count += netCount;
            }
          });
        }

        // Process access rights
        if (source.subcounts.by_access_rights) {
          source.subcounts.by_access_rights.forEach(item => {
            const netCount = (item.records.added.metadata_only + item.records.added.with_files) -
                            (item.records.removed.metadata_only + item.records.removed.with_files);
            if (netCount > 0) {
              if (!subcountAggregates.accessRights[item.id]) {
                subcountAggregates.accessRights[item.id] = {
                  name: item.label || item.id,
                  count: 0
                };
              }
              subcountAggregates.accessRights[item.id].count += netCount;
            }
          });
        }

        // Process resource types
        if (source.subcounts.by_resource_type) {
          source.subcounts.by_resource_type.forEach(item => {
            const netCount = (item.records.added.metadata_only + item.records.added.with_files) -
                            (item.records.removed.metadata_only + item.records.removed.with_files);
            if (netCount > 0) {
              if (!subcountAggregates.resourceTypes[item.id]) {
                subcountAggregates.resourceTypes[item.id] = {
                  id: item.id,
                  name: item.label || item.id,
                  count: 0
                };
              }
              subcountAggregates.resourceTypes[item.id].count += netCount;
            }
          });
        }

        // Process languages
        if (source.subcounts.by_language) {
          source.subcounts.by_language.forEach(item => {
            const netCount = (item.records.added.metadata_only + item.records.added.with_files) -
                            (item.records.removed.metadata_only + item.records.removed.with_files);
            if (netCount > 0) {
              if (!subcountAggregates.languages[item.id]) {
                subcountAggregates.languages[item.id] = {
                  id: item.id,
                  name: item.label || item.id,
                  count: 0
                };
              }
              subcountAggregates.languages[item.id].count += netCount;
            }
          });
        }

        // Process subjects
        if (source.subcounts.by_subject) {
          source.subcounts.by_subject.forEach(item => {
            const netCount = (item.records.added.metadata_only + item.records.added.with_files) -
                            (item.records.removed.metadata_only + item.records.removed.with_files);
            if (netCount > 0) {
              if (!subcountAggregates.subjects[item.id]) {
                subcountAggregates.subjects[item.id] = {
                  id: item.id,
                  name: item.label || item.id,
                  count: 0
                };
              }
              subcountAggregates.subjects[item.id].count += netCount;
            }
          });
        }

        // Process publishers
        if (source.subcounts.by_publisher) {
          source.subcounts.by_publisher.forEach(item => {
            const netCount = (item.records.added.metadata_only + item.records.added.with_files) -
                            (item.records.removed.metadata_only + item.records.removed.with_files);
            if (netCount > 0) {
              if (!subcountAggregates.publishers[item.id]) {
                subcountAggregates.publishers[item.id] = {
                  id: item.id,
                  name: item.label || item.id,
                  count: 0
                };
              }
              subcountAggregates.publishers[item.id].count += netCount;
            }
          });
        }

        // Process periodicals
        if (source.subcounts.by_periodical) {
          source.subcounts.by_periodical.forEach(item => {
            const netCount = (item.records.added.metadata_only + item.records.added.with_files) -
                            (item.records.removed.metadata_only + item.records.removed.with_files);
            if (netCount > 0) {
              if (!subcountAggregates.periodicals[item.id]) {
                subcountAggregates.periodicals[item.id] = {
                  id: item.id,
                  name: item.label || item.id,
                  count: 0
                };
              }
              subcountAggregates.periodicals[item.id].count += netCount;
            }
          });
        }

        // Process file types
        if (source.subcounts.by_file_type) {
          source.subcounts.by_file_type.forEach(item => {
            const netCount = (item.records.added.metadata_only + item.records.added.with_files) -
                            (item.records.removed.metadata_only + item.records.removed.with_files);
            if (netCount > 0) {
              if (!subcountAggregates.fileTypes[item.id]) {
                subcountAggregates.fileTypes[item.id] = {
                  id: item.id,
                  name: item.label || item.id,
                  count: 0
                };
              }
              subcountAggregates.fileTypes[item.id].count += netCount;
            }
          });
        }
      }
    });
  }

  // Process snapshot documents
  if (snapshotDocs && Array.isArray(snapshotDocs)) {
    snapshotDocs.forEach(doc => {
      const source = doc._source;
      const date = source.snapshot_date.split('T')[0]; // Extract date part

      // Calculate total values from snapshot
      const totalRecords = source.total_records.metadata_only + source.total_records.with_files;
      const totalParents = source.total_parents.metadata_only + source.total_parents.with_files;
      const totalFiles = source.total_files.file_count;
      const totalDataVolume = source.total_files.data_volume;
      const totalUploaders = source.total_uploaders;

      // Add cumulative data points
      cumulativeRecordCount.push({
        date,
        value: totalRecords,
        resourceTypes: {},
        subjectHeadings: {}
      });

      cumulativeUploaders.push({
        date,
        value: totalUploaders,
        resourceTypes: {},
        subjectHeadings: {}
      });

      cumulativeDataVolume.push({
        date,
        value: totalDataVolume,
        resourceTypes: {},
        subjectHeadings: {}
      });

      // Views and downloads are not available in record snapshots, so use 0
      cumulativeViews.push({
        date,
        value: 0,
        resourceTypes: {},
        subjectHeadings: {}
      });

      cumulativeDownloads.push({
        date,
        value: 0,
        resourceTypes: {},
        subjectHeadings: {}
      });

      // Traffic is not available in record snapshots, so use 0
      cumulativeTraffic.push({
        date,
        value: 0,
        resourceTypes: {},
        subjectHeadings: {}
      });

      // Aggregate subcounts from snapshots
      if (source.subcounts) {
        // Process resource types
        if (source.subcounts.all_resource_types) {
          source.subcounts.all_resource_types.forEach(item => {
            const totalCount = item.records.metadata_only + item.records.with_files;
            if (totalCount > 0) {
              if (!subcountAggregates.resourceTypes[item.id]) {
                subcountAggregates.resourceTypes[item.id] = {
                  id: item.id,
                  name: item.label?.value || item.label || item.id,
                  count: 0
                };
              }
              subcountAggregates.resourceTypes[item.id].count = Math.max(
                subcountAggregates.resourceTypes[item.id].count,
                totalCount
              );
            }
          });
        }

        // Process access rights
        if (source.subcounts.all_access_rights) {
          source.subcounts.all_access_rights.forEach(item => {
            const totalCount = item.records.metadata_only + item.records.with_files;
            if (totalCount > 0) {
              if (!subcountAggregates.accessRights[item.id]) {
                subcountAggregates.accessRights[item.id] = {
                  name: item.label?.value || item.label || item.id,
                  count: 0
                };
              }
              subcountAggregates.accessRights[item.id].count = Math.max(
                subcountAggregates.accessRights[item.id].count,
                totalCount
              );
            }
          });
        }

        // Process licenses
        if (source.subcounts.all_licenses) {
          source.subcounts.all_licenses.forEach(item => {
            const totalCount = item.records.metadata_only + item.records.with_files;
            if (totalCount > 0) {
              if (!subcountAggregates.licenses[item.id]) {
                subcountAggregates.licenses[item.id] = {
                  id: item.id,
                  name: item.label?.value || item.label || item.id,
                  count: 0
                };
              }
              subcountAggregates.licenses[item.id].count = Math.max(
                subcountAggregates.licenses[item.id].count,
                totalCount
              );
            }
          });
        }

        // Process affiliations (creator and contributor)
        const allAffiliations = [
          ...(source.subcounts.top_affiliations_creator || []),
          ...(source.subcounts.top_affiliations_contributor || [])
        ];
        allAffiliations.forEach(item => {
          const totalCount = item.records.metadata_only + item.records.with_files;
          if (totalCount > 0) {
            if (!subcountAggregates.affiliations[item.id]) {
              subcountAggregates.affiliations[item.id] = {
                name: item.label?.value || item.label || item.id,
                count: 0
              };
            }
            subcountAggregates.affiliations[item.id].count = Math.max(
              subcountAggregates.affiliations[item.id].count,
              totalCount
            );
          }
        });

        // Process funders
        if (source.subcounts.top_funders) {
          source.subcounts.top_funders.forEach(item => {
            const totalCount = item.records.metadata_only + item.records.with_files;
            if (totalCount > 0) {
              if (!subcountAggregates.funders[item.id]) {
                subcountAggregates.funders[item.id] = {
                  name: item.label?.value || item.label || item.id,
                  count: 0
                };
              }
              subcountAggregates.funders[item.id].count = Math.max(
                subcountAggregates.funders[item.id].count,
                totalCount
              );
            }
          });
        }

        // Process languages
        if (source.subcounts.all_languages) {
          source.subcounts.all_languages.forEach(item => {
            const totalCount = item.records.metadata_only + item.records.with_files;
            if (totalCount > 0) {
              if (!subcountAggregates.languages[item.id]) {
                subcountAggregates.languages[item.id] = {
                  id: item.id,
                  name: item.label?.value || item.label || item.id,
                  count: 0
                };
              }
              subcountAggregates.languages[item.id].count = Math.max(
                subcountAggregates.languages[item.id].count,
                totalCount
              );
            }
          });
        }

        // Process subjects
        if (source.subcounts.top_subjects) {
          source.subcounts.top_subjects.forEach(item => {
            const totalCount = item.records.metadata_only + item.records.with_files;
            if (totalCount > 0) {
              if (!subcountAggregates.subjects[item.id]) {
                subcountAggregates.subjects[item.id] = {
                  id: item.id,
                  name: item.label?.value || item.label || item.id,
                  count: 0
                };
              }
              subcountAggregates.subjects[item.id].count = Math.max(
                subcountAggregates.subjects[item.id].count,
                totalCount
              );
            }
          });
        }

        // Process publishers
        if (source.subcounts.top_publishers) {
          source.subcounts.top_publishers.forEach(item => {
            const totalCount = item.records.metadata_only + item.records.with_files;
            if (totalCount > 0) {
              if (!subcountAggregates.publishers[item.id]) {
                subcountAggregates.publishers[item.id] = {
                  id: item.id,
                  name: item.label?.value || item.label || item.id,
                  count: 0
                };
              }
              subcountAggregates.publishers[item.id].count = Math.max(
                subcountAggregates.publishers[item.id].count,
                totalCount
              );
            }
          });
        }

        // Process periodicals
        if (source.subcounts.top_periodicals) {
          source.subcounts.top_periodicals.forEach(item => {
            const totalCount = item.records.metadata_only + item.records.with_files;
            if (totalCount > 0) {
              if (!subcountAggregates.periodicals[item.id]) {
                subcountAggregates.periodicals[item.id] = {
                  id: item.id,
                  name: item.label?.value || item.label || item.id,
                  count: 0
                };
              }
              subcountAggregates.periodicals[item.id].count = Math.max(
                subcountAggregates.periodicals[item.id].count,
                totalCount
              );
            }
          });
        }

        // Process file types
        if (source.subcounts.all_file_types) {
          source.subcounts.all_file_types.forEach(item => {
            const totalCount = item.records.metadata_only + item.records.with_files;
            if (totalCount > 0) {
              if (!subcountAggregates.fileTypes[item.id]) {
                subcountAggregates.fileTypes[item.id] = {
                  id: item.id,
                  name: item.label?.value || item.label || item.id,
                  count: 0
                };
              }
              subcountAggregates.fileTypes[item.id].count = Math.max(
                subcountAggregates.fileTypes[item.id].count,
                totalCount
              );
            }
          });
        }
      }
    });
  }

  // Convert aggregated subcounts to arrays and calculate percentages
  const totalRecords = recordCount.reduce((sum, item) => sum + item.value, 0);
  const maxTotalRecords = cumulativeRecordCount.length > 0
    ? Math.max(...cumulativeRecordCount.map(item => item.value))
    : 0;

  // Use the higher of the two totals for percentage calculations
  const percentageBase = Math.max(totalRecords, maxTotalRecords);

  const licenses = Object.values(subcountAggregates.licenses)
    .sort((a, b) => b.count - a.count)
    .map(item => ({
      ...item,
      percentage: percentageBase > 0 ? Math.round((item.count / percentageBase) * 100) : 0
    }));

  const affiliations = Object.values(subcountAggregates.affiliations)
    .sort((a, b) => b.count - a.count)
    .map(item => ({
      ...item,
      percentage: percentageBase > 0 ? Math.round((item.count / percentageBase) * 100) : 0
    }));

  const funders = Object.values(subcountAggregates.funders)
    .sort((a, b) => b.count - a.count)
    .map(item => ({
      ...item,
      percentage: percentageBase > 0 ? Math.round((item.count / percentageBase) * 100) : 0
    }));

  const accessRights = Object.values(subcountAggregates.accessRights)
    .sort((a, b) => b.count - a.count)
    .map(item => ({
      ...item,
      percentage: percentageBase > 0 ? Math.round((item.count / percentageBase) * 100) : 0
    }));

  const resourceTypes = Object.values(subcountAggregates.resourceTypes)
    .sort((a, b) => b.count - a.count)
    .map(item => ({
      ...item,
      percentage: percentageBase > 0 ? Math.round((item.count / percentageBase) * 100) : 0
    }));

  const languages = Object.values(subcountAggregates.languages)
    .sort((a, b) => b.count - a.count)
    .map(item => ({
      ...item,
      percentage: percentageBase > 0 ? Math.round((item.count / percentageBase) * 100) : 0
    }));

  const subjects = Object.values(subcountAggregates.subjects)
    .sort((a, b) => b.count - a.count)
    .map(item => ({
      ...item,
      percentage: percentageBase > 0 ? Math.round((item.count / percentageBase) * 100) : 0
    }));

  const publishers = Object.values(subcountAggregates.publishers)
    .sort((a, b) => b.count - a.count)
    .map(item => ({
      ...item,
      percentage: percentageBase > 0 ? Math.round((item.count / percentageBase) * 100) : 0
    }));

  const periodicals = Object.values(subcountAggregates.periodicals)
    .sort((a, b) => b.count - a.count)
    .map(item => ({
      ...item,
      percentage: percentageBase > 0 ? Math.round((item.count / percentageBase) * 100) : 0
    }));

  const fileTypes = Object.values(subcountAggregates.fileTypes)
    .sort((a, b) => b.count - a.count)
    .map(item => ({
      ...item,
      percentage: percentageBase > 0 ? Math.round((item.count / percentageBase) * 100) : 0
    }));

  return {
    // Daily values (from deltas) - net values (record-based)
    recordCount,
    uploaders,
    dataVolume,
    parentCount,
    fileCount,
    views,
    downloads,
    traffic,

    // Daily values (from deltas) - net values (parent-based)
    dataVolumeByParents,
    fileCountByParents,

    // Daily values (from deltas) - added values (record-based)
    recordCountAdded,
    dataVolumeAdded,
    parentCountAdded,
    fileCountAdded,

    // Daily values (from deltas) - added values (parent-based)
    dataVolumeByParentsAdded,
    fileCountByParentsAdded,

    // Daily values (from deltas) - removed values (record-based)
    recordCountRemoved,
    dataVolumeRemoved,
    parentCountRemoved,
    fileCountRemoved,

    // Daily values (from deltas) - removed values (parent-based)
    dataVolumeByParentsRemoved,
    fileCountByParentsRemoved,

    // Cumulative values (from snapshots)
    cumulativeRecordCount,
    cumulativeUploaders,
    cumulativeDataVolume,
    cumulativeViews,
    cumulativeDownloads,
    cumulativeTraffic,

    // Subcount data (combined from both deltas and snapshots)
    licenses,
    affiliations,
    funders,
    accessRights,
    resourceTypes,
    languages,
    subjects,
    publishers,
    periodicals,
    fileTypes,

    // Settings
    use_binary_filesize: true,

    // Empty arrays for data not available in record data
    topCountries: [],
    referrerDomains: [],
    mostDownloadedRecords: [],
    mostViewedRecords: []
  };
};
