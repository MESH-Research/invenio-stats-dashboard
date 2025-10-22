// Part of the Invenio-Stats-Dashboard extension for InvenioRDM
// Copyright (C) 2025 Mesh Research
//
// Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
// it under the terms of the MIT License; see LICENSE file for more details.

import { extractCountryMapData } from './mapHelpers';

describe('mapHelpers', () => {
  describe('extractCountryMapData', () => {
    it('should extract country data from usage snapshot data with country name mapping', () => {
      const mockStats = [{
        year: 2024,
        usageSnapshotData: {
          countriesByView: {
            views: [
              {
                id: 'US',
                name: 'United States',
                data: [
                  { value: [new Date('2024-01-01'), 100, 'United States', 'US'] },
                  { value: [new Date('2024-01-02'), 150, 'United States', 'US'] }
                ]
              },
              {
                id: 'CA',
                name: 'Canada',
                data: [
                  { value: [new Date('2024-01-01'), 50, 'Canada', 'CA'] }
                ]
              }
            ]
          }
        }
      }];

      const countryNameMap = {
        'United States': 'USA',
        'Canada': 'Canada'
      };

      const result = extractCountryMapData(mockStats, 'views', null, true);

      expect(result).toHaveLength(2);
      expect(result[0]).toEqual({
        name: 'United States',
        value: 150, // Latest value
        originalName: 'United States',
        readableName: 'United States'
      });
      expect(result[1]).toEqual({
        name: 'Canada',
        value: 50,
        originalName: 'Canada',
        readableName: 'Canada'
      });
    });

    it('should handle downloads metric', () => {
      const mockStats = [{
        year: 2024,
        usageSnapshotData: {
          countriesByDownload: {
            downloads: [
              {
                id: 'US',
                name: 'United States',
                data: [
                  { value: [new Date('2024-01-01'), 75, 'United States', 'US'] }
                ]
              }
            ]
          }
        }
      }];

      const result = extractCountryMapData(mockStats, 'downloads', null, true);

      expect(result).toHaveLength(1);
      expect(result[0]).toEqual({
        name: 'United States',
        value: 75,
        originalName: 'United States',
        readableName: 'United States'
      });
    });

    it('should fallback to countries data', () => {
      const mockStats = [{
        year: 2024,
        usageSnapshotData: {
          countries: {
            views: [
              {
                id: 'US',
                name: 'United States',
                data: [
                  { value: [new Date('2024-01-01'), 100, 'United States', 'US'] }
                ]
              }
            ]
          }
        }
      }];

      const result = extractCountryMapData(mockStats, 'views', null, true);

      expect(result).toHaveLength(1);
      expect(result[0]).toEqual({
        name: 'United States',
        value: 100,
        originalName: 'United States',
        readableName: 'United States'
      });
    });

    it('should handle empty stats', () => {
      const result = extractCountryMapData(null, 'views', null, true);
      expect(result).toEqual([]);
    });

    it('should handle missing data', () => {
      const mockStats = [{
        year: 2024,
        usageSnapshotData: {}
      }];

      const result = extractCountryMapData(mockStats, 'views', null, true);
      expect(result).toEqual([]);
    });

    it('should filter by date range', () => {
      const mockStats = [{
        year: 2024,
        usageSnapshotData: {
          countriesByView: {
            views: [
              {
                id: 'US',
                name: 'United States',
                data: [
                  { value: [new Date('2023-12-31'), 50, 'United States', 'US'] }, // Outside range
                  { value: [new Date('2024-01-01'), 100, 'United States', 'US'] }, // Inside range
                  { value: [new Date('2024-01-02'), 150, 'United States', 'US'] }  // Inside range
                ]
              }
            ]
          }
        }
      }];

      const dateRange = {
        start: new Date('2024-01-01'),
        end: new Date('2024-01-02')
      };

      const result = extractCountryMapData(mockStats, 'views', dateRange, true);

      expect(result).toHaveLength(1);
      expect(result[0].value).toBe(150); // Latest value within range
    });

        it('should handle edge cases', () => {
      const mockStats = [{
        year: 2024,
        usageSnapshotData: {
          countriesByView: {
            views: [
              {
                id: 'US',
                name: 'United States',
                data: [
                  { value: [new Date('2024-01-01'), 100, 'United States', 'US'] }
                ]
              }
            ]
          }
        }
      }];

      const result = extractCountryMapData(mockStats, 'views', null, true);

      expect(result).toHaveLength(1);
      expect(result[0].value).toBe(100);
    });

    it('should extract and sum country data from delta data when useSnapshot is false', () => {
      const mockStats = [{
        year: 2024,
        usageDeltaData: {
          countries: {
            views: [
              {
                id: 'US',
                name: 'United States',
                data: [
                  { value: [new Date('2024-01-01'), 100, 'United States', 'US'] },
                  { value: [new Date('2024-01-02'), 50, 'United States', 'US'] }
                ]
              },
              {
                id: 'CA',
                name: 'Canada',
                data: [
                  { value: [new Date('2024-01-01'), 25, 'Canada', 'CA'] }
                ]
              }
            ]
          }
        }
      }];

      const countryNameMap = {
        'United States': 'USA',
        'Canada': 'Canada'
      };

      const result = extractCountryMapData(mockStats, 'views', null, false);

      expect(result).toHaveLength(2);
      expect(result[0]).toEqual({
        name: 'United States',
        value: 150, // Sum of 100 + 50
        originalName: 'United States',
        readableName: 'United States'
      });
      expect(result[1]).toEqual({
        name: 'Canada',
        value: 25,
        originalName: 'Canada',
        readableName: 'Canada'
      });
    });

    it('should handle empty delta stats', () => {
      const result = extractCountryMapData(null, 'views', null, false);
      expect(result).toEqual([]);
    });

    it('should handle missing delta data', () => {
      const mockStats = [{
        year: 2024,
        usageDeltaData: {}
      }];

      const result = extractCountryMapData(mockStats, 'views', null, false);
      expect(result).toEqual([]);
    });

    it('should filter delta data by date range', () => {
      const mockStats = [{
        year: 2024,
        usageDeltaData: {
          countries: {
            views: [
              {
                id: 'US',
                name: 'United States',
                data: [
                  { value: [new Date('2023-12-31'), 50, 'United States', 'US'] }, // Outside range
                  { value: [new Date('2024-01-01'), 100, 'United States', 'US'] }, // Inside range
                  { value: [new Date('2024-01-02'), 75, 'United States', 'US'] },  // Inside range
                  { value: [new Date('2024-01-03'), 25, 'United States', 'US'] }   // Outside range
                ]
              }
            ]
          }
        }
      }];

      const dateRange = {
        start: new Date('2024-01-01'),
        end: new Date('2024-01-02')
      };

      const result = extractCountryMapData(mockStats, 'views', dateRange, false);

      expect(result).toHaveLength(1);
      expect(result[0].value).toBe(175); // Sum of values within range (100 + 75)
    });

    it('should aggregate delta data by mapped country name', () => {
      const mockStats = [{
        year: 2024,
        usageDeltaData: {
          countries: {
            views: [
              {
                id: 'US',
                name: 'United States',
                data: [
                  { value: [new Date('2024-01-01'), 100, 'United States', 'US'] }
                ]
              },
              {
                id: 'USA',
                name: 'USA',
                data: [
                  { value: [new Date('2024-01-02'), 50, 'USA', 'USA'] }
                ]
              }
            ]
          }
        }
      }];

      const countryNameMap = {
        'United States': 'USA',
        'USA': 'USA'
      };

      const result = extractCountryMapData(mockStats, 'views', null, false);

      expect(result).toHaveLength(2);
      expect(result[0]).toEqual({
        name: 'United States',
        value: 100,
        originalName: 'United States',
        readableName: 'United States'
      });
      expect(result[1]).toEqual({
        name: 'USA',
        value: 50,
        originalName: 'USA',
        readableName: 'USA'
      });
    });

    it('should handle edge cases', () => {
      const mockStats = [{
        year: 2024,
        usageSnapshotData: {
          countriesByView: {
            views: [
              {
                id: 'US',
                name: 'United States',
                data: [
                  { value: [new Date('2024-01-01'), 100, 'United States', 'US'] }
                ]
              }
            ]
          }
        }
      }];

      const result = extractCountryMapData(mockStats, 'views', null, true);

      expect(result).toHaveLength(1);
      expect(result[0].value).toBe(100);
    });
  });
});