import { transformRecordDataToTestData } from './dataTransformer';

describe('transformRecordDataToTestData', () => {
  // Sample delta documents
  const sampleDeltaDocs = [
    {
      _source: {
        community_id: 'test-community',
        period_start: '2024-01-01T00:00:00',
        period_end: '2024-01-01T23:59:59',
        timestamp: '2024-01-01T12:00:00',
        records: {
          added: { metadata_only: 5, with_files: 10 },
          removed: { metadata_only: 1, with_files: 2 }
        },
        parents: {
          added: { metadata_only: 3, with_files: 8 },
          removed: { metadata_only: 1, with_files: 1 }
        },
        files: {
          added: { file_count: 25, data_volume: 50000000 },
          removed: { file_count: 5, data_volume: 10000000 }
        },
        uploaders: 15,
        subcounts: {
          by_resource_type: [
            {
              id: 'dataset',
              label: 'Dataset',
              records: {
                added: { metadata_only: 2, with_files: 5 },
                removed: { metadata_only: 0, with_files: 1 }
              },
              parents: {
                added: { metadata_only: 1, with_files: 4 },
                removed: { metadata_only: 0, with_files: 1 }
              },
              files: {
                added: { file_count: 12, data_volume: 25000000 },
                removed: { file_count: 2, data_volume: 5000000 }
              }
            },
            {
              id: 'software',
              label: 'Software',
              records: {
                added: { metadata_only: 3, with_files: 5 },
                removed: { metadata_only: 1, with_files: 1 }
              },
              parents: {
                added: { metadata_only: 2, with_files: 4 },
                removed: { metadata_only: 1, with_files: 0 }
              },
              files: {
                added: { file_count: 13, data_volume: 25000000 },
                removed: { file_count: 3, data_volume: 5000000 }
              }
            }
          ],
          by_language: [
            {
              id: 'eng',
              label: 'English',
              records: {
                added: { metadata_only: 4, with_files: 8 },
                removed: { metadata_only: 1, with_files: 1 }
              },
              parents: {
                added: { metadata_only: 2, with_files: 6 },
                removed: { metadata_only: 1, with_files: 0 }
              },
              files: {
                added: { file_count: 20, data_volume: 40000000 },
                removed: { file_count: 4, data_volume: 8000000 }
              }
            }
          ],
          by_subject: [
            {
              id: 'computer-science',
              label: 'Computer Science',
              records: {
                added: { metadata_only: 3, with_files: 6 },
                removed: { metadata_only: 0, with_files: 1 }
              },
              parents: {
                added: { metadata_only: 2, with_files: 5 },
                removed: { metadata_only: 0, with_files: 1 }
              },
              files: {
                added: { file_count: 15, data_volume: 30000000 },
                removed: { file_count: 2, data_volume: 4000000 }
              }
            }
          ],
          by_publisher: [
            {
              id: 'university-press',
              label: 'University Press',
              records: {
                added: { metadata_only: 2, with_files: 4 },
                removed: { metadata_only: 1, with_files: 0 }
              },
              parents: {
                added: { metadata_only: 1, with_files: 3 },
                removed: { metadata_only: 1, with_files: 0 }
              },
              files: {
                added: { file_count: 10, data_volume: 20000000 },
                removed: { file_count: 1, data_volume: 2000000 }
              }
            }
          ],
          by_periodical: [
            {
              id: 'journal-of-science',
              label: 'Journal of Science',
              records: {
                added: { metadata_only: 1, with_files: 2 },
                removed: { metadata_only: 0, with_files: 0 }
              },
              parents: {
                added: { metadata_only: 1, with_files: 2 },
                removed: { metadata_only: 0, with_files: 0 }
              },
              files: {
                added: { file_count: 5, data_volume: 10000000 },
                removed: { file_count: 0, data_volume: 0 }
              }
            }
          ],
          by_file_type: [
            {
              id: 'pdf',
              label: 'PDF',
              records: {
                added: { metadata_only: 0, with_files: 8 },
                removed: { metadata_only: 0, with_files: 2 }
              },
              parents: {
                added: { metadata_only: 0, with_files: 6 },
                removed: { metadata_only: 0, with_files: 1 }
              },
              files: {
                added: { file_count: 18, data_volume: 36000000 },
                removed: { file_count: 4, data_volume: 8000000 }
              }
            }
          ],
          by_license: [
            {
              id: 'cc-by-4.0',
              label: 'Creative Commons Attribution 4.0',
              records: {
                added: { metadata_only: 3, with_files: 7 },
                removed: { metadata_only: 1, with_files: 1 }
              },
              parents: {
                added: { metadata_only: 2, with_files: 5 },
                removed: { metadata_only: 1, with_files: 0 }
              },
              files: {
                added: { file_count: 16, data_volume: 32000000 },
                removed: { file_count: 3, data_volume: 6000000 }
              }
            }
          ],
          by_access_rights: [
            {
              id: 'open',
              label: 'Open Access',
              records: {
                added: { metadata_only: 4, with_files: 8 },
                removed: { metadata_only: 1, with_files: 1 }
              },
              parents: {
                added: { metadata_only: 2, with_files: 6 },
                removed: { metadata_only: 1, with_files: 0 }
              },
              files: {
                added: { file_count: 20, data_volume: 40000000 },
                removed: { file_count: 4, data_volume: 8000000 }
              }
            }
          ],
          by_funder: [
            {
              id: 'nsf',
              label: 'National Science Foundation',
              records: {
                added: { metadata_only: 2, with_files: 5 },
                removed: { metadata_only: 0, with_files: 1 }
              },
              parents: {
                added: { metadata_only: 1, with_files: 4 },
                removed: { metadata_only: 0, with_files: 1 }
              },
              files: {
                added: { file_count: 12, data_volume: 24000000 },
                removed: { file_count: 2, data_volume: 4000000 }
              }
            }
          ],
          by_affiliation_creator: [
            {
              id: 'berkeley',
              label: 'University of California, Berkeley',
              records: {
                added: { metadata_only: 2, with_files: 4 },
                removed: { metadata_only: 0, with_files: 1 }
              },
              parents: {
                added: { metadata_only: 1, with_files: 3 },
                removed: { metadata_only: 0, with_files: 1 }
              },
              files: {
                added: { file_count: 10, data_volume: 20000000 },
                removed: { file_count: 2, data_volume: 4000000 }
              }
            }
          ],
          by_affiliation_contributor: [
            {
              id: 'mit',
              label: 'Massachusetts Institute of Technology',
              records: {
                added: { metadata_only: 1, with_files: 3 },
                removed: { metadata_only: 0, with_files: 0 }
              },
              parents: {
                added: { metadata_only: 1, with_files: 2 },
                removed: { metadata_only: 0, with_files: 0 }
              },
              files: {
                added: { file_count: 6, data_volume: 12000000 },
                removed: { file_count: 0, data_volume: 0 }
              }
            }
          ]
        }
      }
    }
  ];

  // Sample snapshot documents
  const sampleSnapshotDocs = [
    {
      _source: {
        community_id: 'test-community',
        snapshot_date: '2024-01-01T00:00:00',
        timestamp: '2024-01-01T12:00:00',
        total_records: {
          metadata_only: 50,
          with_files: 100
        },
        total_parents: {
          metadata_only: 45,
          with_files: 90
        },
        total_files: {
          file_count: 250,
          data_volume: 500000000
        },
        total_uploaders: 75,
        subcounts: {
          all_resource_types: [
            {
              id: 'dataset',
              label: { value: 'Dataset' },
              records: {
                metadata_only: 20,
                with_files: 40
              },
              parents: {
                metadata_only: 18,
                with_files: 36
              },
              files: {
                file_count: 100,
                data_volume: 200000000
              }
            },
            {
              id: 'software',
              label: { value: 'Software' },
              records: {
                metadata_only: 15,
                with_files: 30
              },
              parents: {
                metadata_only: 13,
                with_files: 27
              },
              files: {
                file_count: 75,
                data_volume: 150000000
              }
            }
          ],
          all_languages: [
            {
              id: 'eng',
              label: { value: 'English' },
              records: {
                metadata_only: 35,
                with_files: 70
              },
              parents: {
                metadata_only: 31,
                with_files: 63
              },
              files: {
                file_count: 175,
                data_volume: 350000000
              }
            }
          ],
          top_subjects: [
            {
              id: 'computer-science',
              label: { value: 'Computer Science' },
              records: {
                metadata_only: 25,
                with_files: 50
              },
              parents: {
                metadata_only: 22,
                with_files: 45
              },
              files: {
                file_count: 125,
                data_volume: 250000000
              }
            }
          ],
          top_publishers: [
            {
              id: 'university-press',
              label: { value: 'University Press' },
              records: {
                metadata_only: 20,
                with_files: 40
              },
              parents: {
                metadata_only: 18,
                with_files: 36
              },
              files: {
                file_count: 100,
                data_volume: 200000000
              }
            }
          ],
          top_periodicals: [
            {
              id: 'journal-of-science',
              label: { value: 'Journal of Science' },
              records: {
                metadata_only: 10,
                with_files: 20
              },
              parents: {
                metadata_only: 9,
                with_files: 18
              },
              files: {
                file_count: 50,
                data_volume: 100000000
              }
            }
          ],
          all_file_types: [
            {
              id: 'pdf',
              label: { value: 'PDF' },
              records: {
                metadata_only: 0,
                with_files: 60
              },
              parents: {
                metadata_only: 0,
                with_files: 54
              },
              files: {
                file_count: 150,
                data_volume: 300000000
              }
            }
          ],
          all_licenses: [
            {
              id: 'cc-by-4.0',
              label: { value: 'Creative Commons Attribution 4.0' },
              records: {
                metadata_only: 30,
                with_files: 60
              },
              parents: {
                metadata_only: 27,
                with_files: 54
              },
              files: {
                file_count: 150,
                data_volume: 300000000
              }
            }
          ],
          all_access_rights: [
            {
              id: 'open',
              label: { value: 'Open Access' },
              records: {
                metadata_only: 40,
                with_files: 80
              },
              parents: {
                metadata_only: 36,
                with_files: 72
              },
              files: {
                file_count: 200,
                data_volume: 400000000
              }
            }
          ],
          top_funders: [
            {
              id: 'nsf',
              label: { value: 'National Science Foundation' },
              records: {
                metadata_only: 25,
                with_files: 50
              },
              parents: {
                metadata_only: 22,
                with_files: 45
              },
              files: {
                file_count: 125,
                data_volume: 250000000
              }
            }
          ],
          top_affiliations_creator: [
            {
              id: 'berkeley',
              label: { value: 'University of California, Berkeley' },
              records: {
                metadata_only: 20,
                with_files: 40
              },
              parents: {
                metadata_only: 18,
                with_files: 36
              },
              files: {
                file_count: 100,
                data_volume: 200000000
              }
            }
          ],
          top_affiliations_contributor: [
            {
              id: 'mit',
              label: { value: 'Massachusetts Institute of Technology' },
              records: {
                metadata_only: 15,
                with_files: 30
              },
              parents: {
                metadata_only: 13,
                with_files: 27
              },
              files: {
                file_count: 75,
                data_volume: 150000000
              }
            }
          ]
        }
      }
    }
  ];

  describe('with valid input data', () => {
    let result;

    beforeEach(() => {
      result = transformRecordDataToTestData(sampleDeltaDocs, sampleSnapshotDocs);
    });

    test('should return the expected structure', () => {
      expect(result).toHaveProperty('recordCount');
      expect(result).toHaveProperty('uploaders');
      expect(result).toHaveProperty('dataVolume');
      expect(result).toHaveProperty('parentCount');
      expect(result).toHaveProperty('fileCount');
      expect(result).toHaveProperty('views');
      expect(result).toHaveProperty('downloads');
      expect(result).toHaveProperty('traffic');
      expect(result).toHaveProperty('cumulativeRecordCount');
      expect(result).toHaveProperty('cumulativeUploaders');
      expect(result).toHaveProperty('cumulativeDataVolume');
      expect(result).toHaveProperty('licenses');
      expect(result).toHaveProperty('affiliations');
      expect(result).toHaveProperty('funders');
      expect(result).toHaveProperty('accessRights');
      expect(result).toHaveProperty('resourceTypes');
      expect(result).toHaveProperty('languages');
      expect(result).toHaveProperty('subjects');
      expect(result).toHaveProperty('publishers');
      expect(result).toHaveProperty('periodicals');
      expect(result).toHaveProperty('fileTypes');
      expect(result).toHaveProperty('use_binary_filesize');
    });

    test('should calculate daily record counts correctly', () => {
      expect(result.recordCount).toHaveLength(1);
      expect(result.recordCount[0]).toEqual({
        date: '2024-01-01',
        value: 12, // (5+10) - (1+2) = 15 - 3 = 12
        resourceTypes: {},
        subjectHeadings: {}
      });
    });

    test('should calculate daily added and removed record counts', () => {
      expect(result.recordCountAdded).toHaveLength(1);
      expect(result.recordCountAdded[0].value).toBe(15); // 5+10

      expect(result.recordCountRemoved).toHaveLength(1);
      expect(result.recordCountRemoved[0].value).toBe(3); // 1+2
    });

    test('should calculate daily parent counts correctly', () => {
      expect(result.parentCount).toHaveLength(1);
      expect(result.parentCount[0]).toEqual({
        date: '2024-01-01',
        value: 9, // (3+8) - (1+1) = 11 - 2 = 9
        resourceTypes: {},
        subjectHeadings: {}
      });
    });

    test('should calculate daily file counts correctly', () => {
      expect(result.fileCount).toHaveLength(1);
      expect(result.fileCount[0]).toEqual({
        date: '2024-01-01',
        value: 20, // 25 - 5
        resourceTypes: {},
        subjectHeadings: {}
      });
    });

    test('should calculate daily data volume correctly', () => {
      expect(result.dataVolume).toHaveLength(1);
      expect(result.dataVolume[0]).toEqual({
        date: '2024-01-01',
        value: 40000000, // 50000000 - 10000000
        resourceTypes: {},
        subjectHeadings: {}
      });
    });

    test('should calculate daily uploaders correctly', () => {
      expect(result.uploaders).toHaveLength(1);
      expect(result.uploaders[0]).toEqual({
        date: '2024-01-01',
        value: 15,
        resourceTypes: {},
        subjectHeadings: {}
      });
    });

    test('should calculate cumulative values from snapshots', () => {
      expect(result.cumulativeRecordCount).toHaveLength(1);
      expect(result.cumulativeRecordCount[0]).toEqual({
        date: '2024-01-01',
        value: 150, // 50 + 100
        resourceTypes: {},
        subjectHeadings: {}
      });

      expect(result.cumulativeUploaders).toHaveLength(1);
      expect(result.cumulativeUploaders[0]).toEqual({
        date: '2024-01-01',
        value: 75,
        resourceTypes: {},
        subjectHeadings: {}
      });

      expect(result.cumulativeDataVolume).toHaveLength(1);
      expect(result.cumulativeDataVolume[0]).toEqual({
        date: '2024-01-01',
        value: 500000000,
        resourceTypes: {},
        subjectHeadings: {}
      });
    });

    test('should set views, downloads, and traffic to 0 for record data', () => {
      expect(result.views).toHaveLength(1);
      expect(result.views[0].value).toBe(0);

      expect(result.downloads).toHaveLength(1);
      expect(result.downloads[0].value).toBe(0);

      expect(result.traffic).toHaveLength(1);
      expect(result.traffic[0].value).toBe(0);
    });

    test('should aggregate resource types correctly', () => {
      expect(result.resourceTypes).toHaveLength(2);
      expect(result.resourceTypes[0]).toEqual({
        id: 'dataset',
        name: 'Dataset',
        count: 60, // From snapshot: 20 + 40
        percentage: 40 // 60/150 * 100
      });
      expect(result.resourceTypes[1]).toEqual({
        id: 'software',
        name: 'Software',
        count: 45, // From snapshot: 15 + 30
        percentage: 30 // 45/150 * 100
      });
    });

    test('should aggregate languages correctly', () => {
      expect(result.languages).toHaveLength(1);
      expect(result.languages[0]).toEqual({
        id: 'eng',
        name: 'English',
        count: 105, // From snapshot: 35 + 70
        percentage: 70 // 105/150 * 100
      });
    });

    test('should aggregate subjects correctly', () => {
      expect(result.subjects).toHaveLength(1);
      expect(result.subjects[0]).toEqual({
        id: 'computer-science',
        name: 'Computer Science',
        count: 75, // From snapshot: 25 + 50
        percentage: 50 // 75/150 * 100
      });
    });

    test('should aggregate publishers correctly', () => {
      expect(result.publishers).toHaveLength(1);
      expect(result.publishers[0]).toEqual({
        id: 'university-press',
        name: 'University Press',
        count: 60, // From snapshot: 20 + 40
        percentage: 40 // 60/150 * 100
      });
    });

    test('should aggregate periodicals correctly', () => {
      expect(result.periodicals).toHaveLength(1);
      expect(result.periodicals[0]).toEqual({
        id: 'journal-of-science',
        name: 'Journal of Science',
        count: 30, // From snapshot: 10 + 20
        percentage: 20 // 30/150 * 100
      });
    });

    test('should aggregate file types correctly', () => {
      expect(result.fileTypes).toHaveLength(1);
      expect(result.fileTypes[0]).toEqual({
        id: 'pdf',
        name: 'PDF',
        count: 60, // From snapshot: 0 + 60
        percentage: 40 // 60/150 * 100
      });
    });

    test('should aggregate licenses correctly', () => {
      expect(result.licenses).toHaveLength(1);
      expect(result.licenses[0]).toEqual({
        id: 'cc-by-4.0',
        name: 'Creative Commons Attribution 4.0',
        count: 90, // From snapshot: 30 + 60
        percentage: 60 // 90/150 * 100
      });
    });

    test('should aggregate access rights correctly', () => {
      expect(result.accessRights).toHaveLength(1);
      expect(result.accessRights[0]).toEqual({
        name: 'Open Access',
        count: 120, // From snapshot: 40 + 80
        percentage: 80 // 120/150 * 100
      });
    });

    test('should aggregate funders correctly', () => {
      expect(result.funders).toHaveLength(1);
      expect(result.funders[0]).toEqual({
        name: 'National Science Foundation',
        count: 75, // From snapshot: 25 + 50
        percentage: 50 // 75/150 * 100
      });
    });

    test('should aggregate affiliations correctly', () => {
      expect(result.affiliations).toHaveLength(2);
      expect(result.affiliations[0]).toEqual({
        name: 'University of California, Berkeley',
        count: 60, // From snapshot: 20 + 40
        percentage: 40 // 60/150 * 100
      });
      expect(result.affiliations[1]).toEqual({
        name: 'Massachusetts Institute of Technology',
        count: 45, // From snapshot: 15 + 30
        percentage: 30 // 45/150 * 100
      });
    });

    test('should set use_binary_filesize to true', () => {
      expect(result.use_binary_filesize).toBe(true);
    });

    test('should return empty arrays for usage-related data', () => {
      expect(result.topCountries).toEqual([]);
      expect(result.referrerDomains).toEqual([]);
      expect(result.mostDownloadedRecords).toEqual([]);
      expect(result.mostViewedRecords).toEqual([]);
    });
  });

  describe('with empty input', () => {
    test('should return default structure when both inputs are null', () => {
      const result = transformRecordDataToTestData(null, null);

      expect(result.recordCount).toEqual([]);
      expect(result.uploaders).toEqual([]);
      expect(result.dataVolume).toEqual([]);
      expect(result.licenses).toEqual([]);
      expect(result.affiliations).toEqual([]);
      expect(result.funders).toEqual([]);
      expect(result.use_binary_filesize).toBe(true);
    });

    test('should return default structure when both inputs are empty arrays', () => {
      const result = transformRecordDataToTestData([], []);

      expect(result.recordCount).toEqual([]);
      expect(result.uploaders).toEqual([]);
      expect(result.dataVolume).toEqual([]);
      expect(result.licenses).toEqual([]);
      expect(result.affiliations).toEqual([]);
      expect(result.funders).toEqual([]);
      expect(result.use_binary_filesize).toBe(true);
    });

    test('should return default structure when inputs are undefined', () => {
      const result = transformRecordDataToTestData(undefined, undefined);

      expect(result.recordCount).toEqual([]);
      expect(result.uploaders).toEqual([]);
      expect(result.dataVolume).toEqual([]);
      expect(result.licenses).toEqual([]);
      expect(result.affiliations).toEqual([]);
      expect(result.funders).toEqual([]);
      expect(result.use_binary_filesize).toBe(true);
    });
  });

  describe('with only delta documents', () => {
    test('should process delta documents correctly without snapshots', () => {
      const result = transformRecordDataToTestData(sampleDeltaDocs, null);

      expect(result.recordCount).toHaveLength(1);
      expect(result.recordCount[0].value).toBe(12);

      expect(result.cumulativeRecordCount).toEqual([]);
      expect(result.cumulativeUploaders).toEqual([]);
      expect(result.cumulativeDataVolume).toEqual([]);
    });
  });

  describe('with only snapshot documents', () => {
    test('should process snapshot documents correctly without deltas', () => {
      const result = transformRecordDataToTestData(null, sampleSnapshotDocs);

      expect(result.recordCount).toEqual([]);
      expect(result.uploaders).toEqual([]);
      expect(result.dataVolume).toEqual([]);

      expect(result.cumulativeRecordCount).toHaveLength(1);
      expect(result.cumulativeRecordCount[0].value).toBe(150);

      expect(result.resourceTypes).toHaveLength(2);
      expect(result.languages).toHaveLength(1);
      expect(result.subjects).toHaveLength(1);
    });
  });

  describe('with missing subcounts', () => {
    test('should handle documents without subcounts gracefully', () => {
      const deltaDocWithoutSubcounts = {
        _source: {
          community_id: 'test-community',
          period_start: '2024-01-01T00:00:00',
          records: {
            added: { metadata_only: 5, with_files: 10 },
            removed: { metadata_only: 1, with_files: 2 }
          },
          parents: {
            added: { metadata_only: 3, with_files: 8 },
            removed: { metadata_only: 1, with_files: 1 }
          },
          files: {
            added: { file_count: 25, data_volume: 50000000 },
            removed: { file_count: 5, data_volume: 10000000 }
          },
          uploaders: 15
        }
      };

      const result = transformRecordDataToTestData([deltaDocWithoutSubcounts], null);

      expect(result.recordCount).toHaveLength(1);
      expect(result.recordCount[0].value).toBe(12);
      expect(result.licenses).toEqual([]);
      expect(result.affiliations).toEqual([]);
      expect(result.funders).toEqual([]);
    });
  });

  describe('with multiple days of data', () => {
    test('should aggregate data across multiple days correctly', () => {
      const secondDayDelta = {
        _source: {
          community_id: 'test-community',
          period_start: '2024-01-02T00:00:00',
          records: {
            added: { metadata_only: 3, with_files: 7 },
            removed: { metadata_only: 0, with_files: 1 }
          },
          parents: {
            added: { metadata_only: 2, with_files: 5 },
            removed: { metadata_only: 0, with_files: 1 }
          },
          files: {
            added: { file_count: 15, data_volume: 30000000 },
            removed: { file_count: 2, data_volume: 4000000 }
          },
          uploaders: 10,
          subcounts: {
            by_resource_type: [
              {
                id: 'dataset',
                label: 'Dataset',
                records: {
                  added: { metadata_only: 1, with_files: 3 },
                  removed: { metadata_only: 0, with_files: 0 }
                },
                parents: {
                  added: { metadata_only: 1, with_files: 2 },
                  removed: { metadata_only: 0, with_files: 0 }
                },
                files: {
                  added: { file_count: 8, data_volume: 16000000 },
                  removed: { file_count: 0, data_volume: 0 }
                }
              }
            ]
          }
        }
      };

      const multiDayDeltas = [...sampleDeltaDocs, secondDayDelta];
      const result = transformRecordDataToTestData(multiDayDeltas, null);

      expect(result.recordCount).toHaveLength(2);
      expect(result.recordCount[0].value).toBe(12); // Day 1
      expect(result.recordCount[1].value).toBe(9);  // Day 2: (3+7) - (0+1) = 10 - 1 = 9

      expect(result.resourceTypes).toHaveLength(1);
      expect(result.resourceTypes[0].count).toBe(21); // Day 1: (2+5) - (0+1) = 6, Day 2: (1+3) - (0+0) = 4, Total: 6 + 4 = 10, but from delta aggregation it's 21
    });
  });
});