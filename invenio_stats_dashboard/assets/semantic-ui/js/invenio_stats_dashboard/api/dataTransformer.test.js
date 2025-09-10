// Part of the Invenio-Stats-Dashboard extension for InvenioRDM
// Copyright (C) 2025 Mesh Research
//
// Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
// it under the terms of the MIT License; see LICENSE file for more details.

import { transformApiData } from './dataTransformer';
import { sampleRecordDelta, sampleUsageDelta, sampleRecordSnapshot, sampleUsageSnapshot } from './sampleDataObjects';

describe('transformApiData', () => {
  // Sample input data that matches the actual API structure from sampleDataObjects.js
  const sampleRawStats = {
    record_deltas_created: [sampleRecordDelta],
    record_snapshots_created: [sampleRecordSnapshot],
    usage_deltas: [sampleUsageDelta],
    usage_snapshots: [sampleUsageSnapshot]
  };

  describe('with valid input data', () => {
    let result;

    beforeEach(() => {
      result = transformApiData(sampleRawStats);
    });

    test('should return the expected structure', () => {
      expect(result).toHaveProperty('recordDeltaDataCreated');
      expect(result).toHaveProperty('recordDeltaDataAdded');
      expect(result).toHaveProperty('recordDeltaDataPublished');
      expect(result).toHaveProperty('recordSnapshotDataCreated');
      expect(result).toHaveProperty('recordSnapshotDataAdded');
      expect(result).toHaveProperty('recordSnapshotDataPublished');
      expect(result).toHaveProperty('usageDeltaData');
      expect(result).toHaveProperty('usageSnapshotData');
    });

    test('should transform record delta data correctly', () => {
      const deltaData = result.recordDeltaDataCreated;

      // Check global structure
      expect(deltaData).toHaveProperty('global');
      expect(deltaData.global).toHaveProperty('records');
      expect(deltaData.global).toHaveProperty('parents');
      expect(deltaData.global).toHaveProperty('uploaders');
      expect(deltaData.global).toHaveProperty('fileCount');
      expect(deltaData.global).toHaveProperty('dataVolume');

      // Check that global data is an array of DataSeries
      expect(Array.isArray(deltaData.global.records)).toBe(true);
      expect(deltaData.global.records[0]).toHaveProperty('id');
      expect(deltaData.global.records[0]).toHaveProperty('name');
      expect(deltaData.global.records[0]).toHaveProperty('data');
      expect(deltaData.global.records[0]).toHaveProperty('type');
      expect(deltaData.global.records[0]).toHaveProperty('valueType');

      // Check byFilePresence structure (all metrics for record deltas)
      expect(deltaData).toHaveProperty('byFilePresence');
      expect(deltaData.byFilePresence).toHaveProperty('records');
      expect(deltaData.byFilePresence).toHaveProperty('parents');
      expect(deltaData.byFilePresence).toHaveProperty('uploaders');
      expect(deltaData.byFilePresence).toHaveProperty('fileCount');
      expect(deltaData.byFilePresence).toHaveProperty('dataVolume');

      // Check subcount categories
      expect(deltaData).toHaveProperty('resourceTypes');
      expect(deltaData).toHaveProperty('languages');
      expect(deltaData).toHaveProperty('accessStatuses');
      expect(deltaData).toHaveProperty('affiliations');
      expect(deltaData).toHaveProperty('funders');
      expect(deltaData).toHaveProperty('subjects');
      expect(deltaData).toHaveProperty('publishers');
      expect(deltaData).toHaveProperty('periodicals');
      expect(deltaData).toHaveProperty('rights');
      expect(deltaData).toHaveProperty('fileTypes');
    });

    test('should transform record snapshot data correctly', () => {
      const snapshotData = result.recordSnapshotDataCreated;

      // Check global structure
      expect(snapshotData).toHaveProperty('global');
      expect(snapshotData.global).toHaveProperty('records');
      expect(snapshotData.global).toHaveProperty('parents');
      expect(snapshotData.global).toHaveProperty('uploaders');
      expect(snapshotData.global).toHaveProperty('fileCount');
      expect(snapshotData.global).toHaveProperty('dataVolume');

      // Check that global data is an array of DataSeries
      expect(Array.isArray(snapshotData.global.records)).toBe(true);
      expect(snapshotData.global.records[0]).toHaveProperty('id');
      expect(snapshotData.global.records[0]).toHaveProperty('name');
      expect(snapshotData.global.records[0]).toHaveProperty('data');
      expect(snapshotData.global.records[0]).toHaveProperty('type');
      expect(snapshotData.global.records[0]).toHaveProperty('valueType');

      // Check byFilePresence structure (only records and parents)
      expect(snapshotData).toHaveProperty('byFilePresence');
      expect(snapshotData.byFilePresence).toHaveProperty('records');
      expect(snapshotData.byFilePresence).toHaveProperty('parents');
      expect(snapshotData.byFilePresence).not.toHaveProperty('uploaders');
      expect(snapshotData.byFilePresence).not.toHaveProperty('fileCount');
      expect(snapshotData.byFilePresence).not.toHaveProperty('dataVolume');
    });

    test('should transform usage delta data correctly', () => {
      const deltaData = result.usageDeltaData;

      // Check global structure
      expect(deltaData).toHaveProperty('global');
      expect(deltaData.global).toHaveProperty('views');
      expect(deltaData.global).toHaveProperty('downloads');
      expect(deltaData.global).toHaveProperty('visitors');
      expect(deltaData.global).toHaveProperty('dataVolume');

      // Check that global data is an array of DataSeries
      expect(Array.isArray(deltaData.global.views)).toBe(true);
      expect(deltaData.global.views[0]).toHaveProperty('id');
      expect(deltaData.global.views[0]).toHaveProperty('name');
      expect(deltaData.global.views[0]).toHaveProperty('data');
      expect(deltaData.global.views[0]).toHaveProperty('type');
      expect(deltaData.global.views[0]).toHaveProperty('valueType');

      // byFilePresence is implemented for usage data
      expect(deltaData).toHaveProperty('byFilePresence');

      // Check subcount categories
      expect(deltaData).toHaveProperty('byAccessStatuses');
      expect(deltaData).toHaveProperty('byFileTypes');
      expect(deltaData).toHaveProperty('byLanguages');
      expect(deltaData).toHaveProperty('byResourceTypes');
      expect(deltaData).toHaveProperty('bySubjects');
      expect(deltaData).toHaveProperty('byPublishers');
      expect(deltaData).toHaveProperty('byRights');
      expect(deltaData).toHaveProperty('byCountries');
      expect(deltaData).toHaveProperty('byReferrers');
      expect(deltaData).toHaveProperty('byAffiliations');
    });

    test('should transform usage snapshot data correctly', () => {
      const snapshotData = result.usageSnapshotData;

      // Check global structure
      expect(snapshotData).toHaveProperty('global');
      expect(snapshotData.global).toHaveProperty('views');
      expect(snapshotData.global).toHaveProperty('downloads');
      expect(snapshotData.global).toHaveProperty('visitors');
      expect(snapshotData.global).toHaveProperty('dataVolume');

      // Check that global data is an array of DataSeries
      expect(Array.isArray(snapshotData.global.views)).toBe(true);
      expect(snapshotData.global.views[0]).toHaveProperty('id');
      expect(snapshotData.global.views[0]).toHaveProperty('name');
      expect(snapshotData.global.views[0]).toHaveProperty('data');
      expect(snapshotData.global.views[0]).toHaveProperty('type');
      expect(snapshotData.global.views[0]).toHaveProperty('valueType');

      // byFilePresence is implemented for usage data
      expect(snapshotData).toHaveProperty('byFilePresence');

      // Check separate view/download properties
      expect(snapshotData).toHaveProperty('topCountriesByView');
      expect(snapshotData).toHaveProperty('topCountriesByDownload');
      expect(snapshotData).toHaveProperty('topSubjectsByView');
      expect(snapshotData).toHaveProperty('topSubjectsByDownload');
      expect(snapshotData).toHaveProperty('topPublishersByView');
      expect(snapshotData).toHaveProperty('topPublishersByDownload');
      expect(snapshotData).toHaveProperty('topRightsByView');
      expect(snapshotData).toHaveProperty('topRightsByDownload');
      expect(snapshotData).toHaveProperty('topReferrersByView');
      expect(snapshotData).toHaveProperty('topReferrersByDownload');
      expect(snapshotData).toHaveProperty('topAffiliationsByView');
      expect(snapshotData).toHaveProperty('topAffiliationsByDownload');
    });

    test('should create correct DataPoint objects', () => {
      const deltaData = result.recordDeltaDataCreated;
      const dataPoint = deltaData.global.records[0].data[0];

      expect(dataPoint).toHaveProperty('value');
      expect(Array.isArray(dataPoint.value)).toBe(true);
      expect(dataPoint.value).toHaveLength(2);
      expect(dataPoint.value[0]).toBeInstanceOf(Date);
      expect(typeof dataPoint.value[1]).toBe('number');
      expect(dataPoint).toHaveProperty('readableDate');
      expect(typeof dataPoint.readableDate).toBe('string');
      expect(dataPoint).toHaveProperty('valueType');
      expect(typeof dataPoint.valueType).toBe('string');
    });

    test('should create correct DataSeries objects', () => {
      const deltaData = result.recordDeltaDataCreated;
      const dataSeries = deltaData.global.records[0];

      expect(dataSeries).toHaveProperty('id');
      expect(typeof dataSeries.id).toBe('string');
      expect(dataSeries).toHaveProperty('name');
      expect(typeof dataSeries.name).toBe('string');
      expect(dataSeries).toHaveProperty('data');
      expect(Array.isArray(dataSeries.data)).toBe(true);
      expect(dataSeries).toHaveProperty('type');
      expect(typeof dataSeries.type).toBe('string');
      expect(dataSeries).toHaveProperty('valueType');
      expect(typeof dataSeries.valueType).toBe('string');
    });

    test('should handle byFilePresence data correctly', () => {
      const deltaData = result.recordDeltaDataCreated;
      const byFilePresence = deltaData.byFilePresence.records;

      expect(Array.isArray(byFilePresence)).toBe(true);
      expect(byFilePresence.length).toBeGreaterThan(0);

      // Should have 'withFiles' and 'metadataOnly' series
      const seriesNames = byFilePresence.map(series => series.name);
      expect(seriesNames).toContain('withFiles');
      expect(seriesNames).toContain('metadataOnly');
    });

    test('should handle subcount data correctly', () => {
      const deltaData = result.recordDeltaDataCreated;
      const resourceTypes = deltaData.resourceTypes.records;

      expect(Array.isArray(resourceTypes)).toBe(true);
      expect(resourceTypes.length).toBeGreaterThan(0);

      // Each series should have the correct structure
      resourceTypes.forEach(series => {
        expect(series).toHaveProperty('id');
        expect(series).toHaveProperty('name');
        expect(series).toHaveProperty('data');
        expect(series).toHaveProperty('type');
        expect(series).toHaveProperty('valueType');
      });

      // Check that labels are properly localized strings (not objects)
      resourceTypes.forEach(series => {
        expect(typeof series.name).toBe('string');
        expect(series.name).not.toBe('[object Object]');
        expect(series.name.length).toBeGreaterThan(0);
      });

      // Check languages subcount as well
      const languages = deltaData.languages.records;
      if (languages.length > 0) {
        languages.forEach(series => {
          expect(typeof series.name).toBe('string');
          expect(series.name).not.toBe('[object Object]');
          expect(series.name.length).toBeGreaterThan(0);
        });
      }

      // Check rights subcount as well
      const rights = deltaData.rights.records;
      if (rights.length > 0) {
        rights.forEach(series => {
          expect(typeof series.name).toBe('string');
          expect(series.name).not.toBe('[object Object]');
          expect(series.name.length).toBeGreaterThan(0);
        });
      }
    });
  });

  describe('with empty input data', () => {
    test('should return empty structure when rawStats is null', () => {
      const result = transformApiData(null);

      expect(result).toHaveProperty('recordDeltaDataCreated');
      expect(result).toHaveProperty('recordDeltaDataAdded');
      expect(result).toHaveProperty('recordDeltaDataPublished');
      expect(result).toHaveProperty('recordSnapshotDataCreated');
      expect(result).toHaveProperty('recordSnapshotDataAdded');
      expect(result).toHaveProperty('recordSnapshotDataPublished');
      expect(result).toHaveProperty('usageDeltaData');
      expect(result).toHaveProperty('usageSnapshotData');
    });

    test('should return empty structure when rawStats is undefined', () => {
      const result = transformApiData(undefined);

      expect(result).toHaveProperty('recordDeltaDataCreated');
      expect(result).toHaveProperty('recordDeltaDataAdded');
      expect(result).toHaveProperty('recordDeltaDataPublished');
      expect(result).toHaveProperty('recordSnapshotDataCreated');
      expect(result).toHaveProperty('recordSnapshotDataAdded');
      expect(result).toHaveProperty('recordSnapshotDataPublished');
      expect(result).toHaveProperty('usageDeltaData');
      expect(result).toHaveProperty('usageSnapshotData');
    });

    test('should handle empty arrays in input data', () => {
      const emptyRawStats = {
        record_deltas_created: [],
        record_snapshots_created: [],
        usage_deltas: [],
        usage_snapshots: []
      };

      const result = transformApiData(emptyRawStats);

      expect(result).toHaveProperty('recordDeltaDataCreated');
      expect(result).toHaveProperty('recordDeltaDataAdded');
      expect(result).toHaveProperty('recordDeltaDataPublished');
      expect(result).toHaveProperty('recordSnapshotDataCreated');
      expect(result).toHaveProperty('recordSnapshotDataAdded');
      expect(result).toHaveProperty('recordSnapshotDataPublished');
      expect(result).toHaveProperty('usageDeltaData');
      expect(result).toHaveProperty('usageSnapshotData');
    });
  });

  describe('with real sample data', () => {
    test('should handle sampleRecordDelta correctly', () => {
      const rawStats = {
        record_deltas_created: [sampleRecordDelta],
        record_snapshots_created: [],
        usage_deltas: [],
        usage_snapshots: []
      };

      const result = transformApiData(rawStats);

      expect(result.recordDeltaDataCreated).toHaveProperty('global');
      expect(result.recordDeltaDataCreated).toHaveProperty('byFilePresence');
      expect(result.recordDeltaDataCreated).toHaveProperty('resourceTypes');
      expect(result.recordDeltaDataCreated).toHaveProperty('accessStatuses');
      expect(result.recordDeltaDataCreated).toHaveProperty('languages');
      expect(result.recordDeltaDataCreated).toHaveProperty('affiliations');
      expect(result.recordDeltaDataCreated).toHaveProperty('subjects');
      expect(result.recordDeltaDataCreated).toHaveProperty('publishers');
      expect(result.recordDeltaDataCreated).toHaveProperty('fileTypes');
    });

    test('should handle sampleRecordSnapshot correctly', () => {
      const rawStats = {
        record_deltas_created: [],
        record_snapshots_created: [sampleRecordSnapshot],
        usage_deltas: [],
        usage_snapshots: []
      };

      const result = transformApiData(rawStats);

      expect(result.recordSnapshotDataCreated).toHaveProperty('global');
      expect(result.recordSnapshotDataCreated).toHaveProperty('byFilePresence');
      expect(result.recordSnapshotDataCreated).toHaveProperty('accessStatuses');
    });

    test('should handle sampleUsageSnapshot correctly', () => {
      const rawStats = {
        record_deltas_created: [],
        record_snapshots_created: [],
        usage_deltas: [],
        usage_snapshots: [sampleUsageSnapshot]
      };

      const result = transformApiData(rawStats);

      expect(result.usageSnapshotData).toHaveProperty('global');
      expect(result.usageSnapshotData).toHaveProperty('byFilePresence');
      expect(result.usageSnapshotData).toHaveProperty('byAccessStatuses');
      expect(result.usageSnapshotData).toHaveProperty('byFileTypes');
      expect(result.usageSnapshotData).toHaveProperty('byLanguages');
      expect(result.usageSnapshotData).toHaveProperty('byResourceTypes');
      expect(result.usageSnapshotData).toHaveProperty('topCountriesByView');
      expect(result.usageSnapshotData).toHaveProperty('topCountriesByDownload');
      expect(result.usageSnapshotData).toHaveProperty('topSubjectsByView');
      expect(result.usageSnapshotData).toHaveProperty('topSubjectsByDownload');
      expect(result.usageSnapshotData).toHaveProperty('topPublishersByView');
      expect(result.usageSnapshotData).toHaveProperty('topPublishersByDownload');
      expect(result.usageSnapshotData).toHaveProperty('topRightsByView');
      expect(result.usageSnapshotData).toHaveProperty('topRightsByDownload');
      expect(result.usageSnapshotData).toHaveProperty('topReferrersByView');
      expect(result.usageSnapshotData).toHaveProperty('topReferrersByDownload');
      expect(result.usageSnapshotData).toHaveProperty('topAffiliationsByView');
      expect(result.usageSnapshotData).toHaveProperty('topAffiliationsByDownload');
    });
  });

  describe('data transformation accuracy', () => {
    test('should calculate net counts correctly for record deltas', () => {
      const rawStats = {
        record_deltas_created: [sampleRecordDelta],
        record_snapshots_created: [],
        usage_deltas: [],
        usage_snapshots: []
      };

      const result = transformApiData(rawStats);
      const globalRecords = result.recordDeltaDataCreated.global.records[0];

      // Net records: (0+2) - (0+0) = 2 - 0 = 2
      expect(globalRecords.data[0].value[1]).toBe(2);
    });

    test('should calculate total counts correctly for record snapshots', () => {
      const rawStats = {
        record_deltas_created: [],
        record_snapshots_created: [sampleRecordSnapshot],
        usage_deltas: [],
        usage_snapshots: []
      };

      const result = transformApiData(rawStats);
      const globalRecords = result.recordSnapshotDataCreated.global.records[0];

      // Total records: 1 + 0 = 1
      expect(globalRecords.data[0].value[1]).toBe(1);
    });

    test('should calculate usage metrics correctly for usage deltas', () => {
      const rawStats = {
        record_deltas_created: [],
        record_snapshots_created: [],
        usage_deltas: [sampleUsageDelta],
        usage_snapshots: []
      };

      const result = transformApiData(rawStats);
      const globalViews = result.usageDeltaData.global.views[0];
      const globalDownloads = result.usageDeltaData.global.downloads[0];
      const globalVisitors = result.usageDeltaData.global.visitors[0];
      const globalDataVolume = result.usageDeltaData.global.dataVolume[0];

      // Views: 8
      expect(globalViews.data[0].value[1]).toBe(8);
      // Downloads: 6
      expect(globalDownloads.data[0].value[1]).toBe(6);
      // Visitors: max(8, 6) = 8
      expect(globalVisitors.data[0].value[1]).toBe(8);
      // Data volume: 6144.0
      expect(globalDataVolume.data[0].value[1]).toBe(6144.0);
    });

    test('should calculate usage metrics correctly for usage snapshots', () => {
      const rawStats = {
        record_deltas_created: [],
        record_snapshots_created: [],
        usage_deltas: [],
        usage_snapshots: [sampleUsageSnapshot]
      };

      const result = transformApiData(rawStats);
      const globalViews = result.usageSnapshotData.global.views[0];
      const globalDownloads = result.usageSnapshotData.global.downloads[0];
      const globalVisitors = result.usageSnapshotData.global.visitors[0];
      const globalDataVolume = result.usageSnapshotData.global.dataVolume[0];

      // Views: 80
      expect(globalViews.data[0].value[1]).toBe(80);
      // Downloads: 60
      expect(globalDownloads.data[0].value[1]).toBe(60);
      // Visitors: max(80, 60) = 80
      expect(globalVisitors.data[0].value[1]).toBe(80);
      // Data volume: 61440.0
      expect(globalDataVolume.data[0].value[1]).toBe(61440.0);
    });

    test('should handle filesize valueType correctly', () => {
      const rawStats = {
        record_deltas_created: [sampleRecordDelta],
        record_snapshots_created: [],
        usage_deltas: [],
        usage_snapshots: []
      };

      const result = transformApiData(rawStats);
      const globalDataVolume = result.recordDeltaDataCreated.global.dataVolume[0];

      expect(globalDataVolume.valueType).toBe('filesize');
    });

    test('should handle empty subcount arrays correctly', () => {
      const rawStats = {
        record_deltas_created: [
          {
            ...sampleRecordDelta,
            subcounts: {
              by_access_statuses: [],
              by_affiliations_contributors: [],
              by_file_types: []
            }
          }
        ],
        record_snapshots_created: [],
        usage_deltas: [],
        usage_snapshots: []
      };

      const result = transformApiData(rawStats);

      // Should not crash and should return empty arrays for subcounts
      expect(result.recordDeltaDataCreated.accessStatuses.records).toEqual([]);
      expect(result.recordDeltaDataCreated.affiliations.records).toEqual([]);
      expect(result.recordDeltaDataCreated.fileTypes.records).toEqual([]);
    });

    test('should handle different subcount item structures correctly', () => {
      const rawStats = {
        record_deltas_created: [sampleRecordDelta],
        record_snapshots_created: [],
        usage_deltas: [],
        usage_snapshots: []
      };

      const result = transformApiData(rawStats);

      // Should handle both nested structure (by_access_statuses) and direct structure (by_file_types)
      expect(result.recordDeltaDataCreated.accessStatuses.records.length).toBeGreaterThan(0);
      expect(result.recordDeltaDataCreated.fileTypes.records.length).toBeGreaterThan(0);
    });

    test('should handle separate view/download structures in usage snapshots', () => {
      const rawStats = {
        record_deltas_created: [],
        record_snapshots_created: [],
        usage_deltas: [],
        usage_snapshots: [sampleUsageSnapshot]
      };

      const result = transformApiData(rawStats);

      // Should create separate series for view and download data
      expect(result.usageSnapshotData.topCountriesByView).toBeDefined();
      expect(result.usageSnapshotData.topCountriesByDownload).toBeDefined();
      expect(result.usageSnapshotData.topCountriesByView.views.length).toBeGreaterThan(0);
      expect(result.usageSnapshotData.topCountriesByDownload.downloads.length).toBeGreaterThan(0);
    });
  });

  describe('data consistency validation', () => {
    test('should maintain data consistency between input and output for record deltas', () => {
      const rawStats = {
        record_deltas_created: [sampleRecordDelta],
        record_snapshots_created: [],
        usage_deltas: [],
        usage_snapshots: []
      };

      const result = transformApiData(rawStats);
      const globalRecords = result.recordDeltaDataCreated.global.records[0];
      const globalParents = result.recordDeltaDataCreated.global.parents[0];
      const globalFiles = result.recordDeltaDataCreated.global.fileCount[0];
      const globalDataVolume = result.recordDeltaDataCreated.global.dataVolume[0];

      // Verify calculations match expected values from sampleRecordDelta
      const expectedRecords = 2; // (0+2) - (0+0) = 2
      const expectedParents = 2; // (0+2) - (0+0) = 2
      const expectedFiles = 2; // (0+2) - (0+0) = 2 (files in sample data)
      const expectedDataVolume = 59117831.0; // (0+59117831.0) - (0+0.0) = 59117831.0

      expect(globalRecords.data[0].value[1]).toBe(expectedRecords);
      expect(globalParents.data[0].value[1]).toBe(expectedParents);
      expect(globalFiles.data[0].value[1]).toBe(expectedFiles);
      expect(globalDataVolume.data[0].value[1]).toBe(expectedDataVolume);
    });

    test('should maintain data consistency between input and output for usage deltas', () => {
      const rawStats = {
        record_deltas_created: [],
        record_snapshots_created: [],
        usage_deltas: [sampleUsageDelta],
        usage_snapshots: []
      };

      const result = transformApiData(rawStats);
      const globalViews = result.usageDeltaData.global.views[0];
      const globalDownloads = result.usageDeltaData.global.downloads[0];
      const globalVisitors = result.usageDeltaData.global.visitors[0];
      const globalDataVolume = result.usageDeltaData.global.dataVolume[0];

      // Verify calculations match expected values from sampleUsageDelta
      expect(globalViews.data[0].value[1]).toBe(8);
      expect(globalDownloads.data[0].value[1]).toBe(6);
      expect(globalVisitors.data[0].value[1]).toBe(8); // max(8, 6)
      expect(globalDataVolume.data[0].value[1]).toBe(6144.0);
    });

    test('should validate DataPoint structure consistency', () => {
      const rawStats = {
        record_deltas_created: [sampleRecordDelta],
        record_snapshots_created: [],
        usage_deltas: [],
        usage_snapshots: []
      };

      const result = transformApiData(rawStats);
      const dataPoint = result.recordDeltaDataCreated.global.records[0].data[0];

      // Validate DataPoint structure
      expect(dataPoint).toHaveProperty('value');
      expect(Array.isArray(dataPoint.value)).toBe(true);
      expect(dataPoint.value.length).toBe(2);
      expect(typeof dataPoint.value[0]).toBe('object'); // Date object
      expect(typeof dataPoint.value[1]).toBe('number'); // Value

      // Validate date parsing - sample data uses 2025-05-30T00:00:00
      const expectedDate = new Date('2025-05-30T00:00:00Z');
      expect(dataPoint.value[0].getTime()).toBe(expectedDate.getTime());
    });

    test('should validate DataSeries structure consistency', () => {
      const rawStats = {
        record_deltas_created: [sampleRecordDelta],
        record_snapshots_created: [],
        usage_deltas: [],
        usage_snapshots: []
      };

      const result = transformApiData(rawStats);
      const dataSeries = result.recordDeltaDataCreated.global.records[0];

      // Validate DataSeries structure
      expect(dataSeries).toHaveProperty('id');
      expect(typeof dataSeries.id).toBe('string');
      expect(dataSeries).toHaveProperty('name');
      expect(typeof dataSeries.name).toBe('string');
      expect(dataSeries).toHaveProperty('data');
      expect(Array.isArray(dataSeries.data)).toBe(true);
      expect(dataSeries).toHaveProperty('type');
      expect(typeof dataSeries.type).toBe('string');
      expect(dataSeries).toHaveProperty('valueType');
      expect(typeof dataSeries.valueType).toBe('string');

      // Validate that id and name are consistent
      expect(dataSeries.id).toBe('global');
      expect(dataSeries.name).toBe('Global');
    });
  });
});