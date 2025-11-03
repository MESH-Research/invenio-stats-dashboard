/**
 * Part of Invenio-Stats-Dashboard
 * Copyright (C) 2025 Mesh Research
 *
 * Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
 * it under the terms of the MIT License; see LICENSE file for more details.
 */

// Mock performance API for Node.js test environment
global.performance = global.performance || {
  now: jest.fn(() => Date.now()),
};

// Mock dependencies first
jest.mock('../utils/statsCacheWorker', () => ({
  getCachedStats: jest.fn(),
  setCachedStats: jest.fn(),
}));

jest.mock('./yearlyBlockManager', () => ({
  findMissingBlocks: jest.fn(),
  mergeYearlyStats: jest.fn(),
}));

// Mock axios for statsApiClient.getStats
jest.mock('axios', () => ({
  create: jest.fn(() => ({
    post: jest.fn().mockResolvedValue({
      data: {},
    }),
    get: jest.fn(),
  })),
}));

// Import after mocks
import { fetchStatsWithYearlyBlocks } from './api';
import { getCachedStats, setCachedStats } from '../utils/statsCacheWorker';
import { findMissingBlocks, mergeYearlyStats } from './yearlyBlockManager';

// Get statsApiClient from the actual module after import
import * as apiModule from './api';
const statsApiClient = apiModule.statsApiClient;

describe('API Cache Integration', () => {
  const mockCommunityId = 'test-community';
  const mockDashboardType = 'community';
  const mockDateBasis = 'added';
  const currentYear = new Date().getUTCFullYear();
  const pastYear = currentYear - 1;

  beforeEach(() => {
    jest.clearAllMocks();
    
    // Set up mergeYearlyStats mock implementation
    const { mergeYearlyStats } = require('./yearlyBlockManager');
    mergeYearlyStats.mockImplementation((currentStats, newYearlyStats) => {
      const current = Array.isArray(currentStats) ? currentStats : [];
      const newStats = Array.isArray(newYearlyStats) ? newYearlyStats : [];
      const flattened = newStats.flat();
      return [...current, ...flattened];
    });
    
    // Set up setCachedStats to return a resolved promise (so .catch() works)
    const { setCachedStats } = require('../utils/statsCacheWorker');
    setCachedStats.mockResolvedValue({ success: true });
    
    // Mock statsApiClient.getStats for all tests
    // Use a fresh mock implementation each time to avoid conflicts
    if (statsApiClient.getStats.mockRestore) {
      statsApiClient.getStats.mockRestore();
    }
    jest.spyOn(statsApiClient, 'getStats').mockImplementation(() => Promise.resolve({
      recordDeltaDataAdded: {},
      recordSnapshotDataAdded: {},
      usageDeltaData: {},
      usageSnapshotData: {},
    }));
  });

  describe('fetchStatsWithYearlyBlocks - Cache First Strategy', () => {
    it('should check cache before making API requests', async () => {
      const startDate = new Date(`${currentYear}-01-01`);
      const endDate = new Date(`${currentYear}-12-31`);

      const mockBlock = {
        year: currentYear,
        startDate,
        endDate,
      };

      findMissingBlocks.mockReturnValue([mockBlock]);

      // Mock cache miss
      getCachedStats.mockResolvedValue(null);

      // Mock API response
      const mockStats = {
        recordDeltaDataAdded: {},
        recordSnapshotDataAdded: {},
        usageDeltaData: {},
        usageSnapshotData: {},
      };
      statsApiClient.getStats.mockResolvedValueOnce(mockStats);

      const result = await fetchStatsWithYearlyBlocks({
        communityId: mockCommunityId,
        dashboardType: mockDashboardType,
        startDate,
        endDate,
        dateBasis: mockDateBasis,
        currentStats: [],
      });

      // Should check cache first
      expect(getCachedStats).toHaveBeenCalledWith(
        mockCommunityId,
        mockDashboardType,
        mockDateBasis,
        `${currentYear}-01-01`,
        `${currentYear}-12-31`,
      );

      // Should fetch from API when cache miss
      expect(statsApiClient.getStats).toHaveBeenCalled();

      // Should cache the fetched data
      expect(setCachedStats).toHaveBeenCalled();
    });

    it('should use cached data when available and valid', async () => {
      const startDate = new Date(`${pastYear}-01-01`);
      const endDate = new Date(`${pastYear}-12-31`);

      const mockBlock = {
        year: pastYear,
        startDate,
        endDate,
      };

      findMissingBlocks.mockReturnValue([mockBlock]);

      // Mock cache hit
      const mockCachedData = {
        recordDeltaDataAdded: {},
        recordSnapshotDataAdded: {},
        usageDeltaData: {},
        usageSnapshotData: {},
      };

      getCachedStats.mockResolvedValue({
        data: mockCachedData,
        serverFetchTimestamp: Date.now() - 1000,
        year: pastYear,
      });

      let result;
      try {
        result = await fetchStatsWithYearlyBlocks({
          communityId: mockCommunityId,
          dashboardType: mockDashboardType,
          startDate,
          endDate,
          dateBasis: mockDateBasis,
          currentStats: [],
        });
      } catch (error) {
        console.error('Test error:', error);
        throw error;
      }

      // Should check cache
      expect(getCachedStats).toHaveBeenCalled();

      // Should NOT call API when cache hit
      expect(statsApiClient.getStats).not.toHaveBeenCalled();

      // Should NOT set cache again (already cached)
      expect(setCachedStats).not.toHaveBeenCalled();

      // Should return cached data
      expect(result).toBeDefined();
      
      
      expect(result).toHaveProperty('stats');
      
      // When cached blocks are found, they are merged with currentStats
      // The cached data is spread with year property: {...mockCachedData, year: pastYear}
      // mergeYearlyStats should merge this into the stats array
      expect(result.stats).toBeDefined();
      expect(Array.isArray(result.stats)).toBe(true);
      // Should have the cached data with year property
      expect(result.stats.length).toBeGreaterThan(0);
    });

    it('should fetch from API when cache miss for current year', async () => {
      const startDate = new Date(`${currentYear}-01-01`);
      const endDate = new Date(`${currentYear}-12-31`);

      const mockBlock = {
        year: currentYear,
        startDate,
        endDate,
      };

      findMissingBlocks.mockReturnValue([mockBlock]);

      // Mock cache miss
      getCachedStats.mockResolvedValue(null);

      // Mock API response (override default)
      const mockStats = {
        recordDeltaDataAdded: { global: { records: [] } },
        recordSnapshotDataAdded: { global: { records: [] } },
        usageDeltaData: { global: { downloads: [] } },
        usageSnapshotData: { global: { downloads: [] } },
      };
      statsApiClient.getStats.mockResolvedValueOnce(mockStats);

      const result = await fetchStatsWithYearlyBlocks({
        communityId: mockCommunityId,
        dashboardType: mockDashboardType,
        startDate,
        endDate,
        dateBasis: mockDateBasis,
        currentStats: [],
      });

      // Should check cache first
      expect(getCachedStats).toHaveBeenCalled();

      // Should fetch from API
      expect(statsApiClient.getStats).toHaveBeenCalledWith(
        mockCommunityId,
        mockDashboardType,
        `${currentYear}-01-01`,
        `${currentYear}-12-31`,
        mockDateBasis,
        {},
      );

      // Should cache the result with year information
      expect(setCachedStats).toHaveBeenCalledWith(
        mockCommunityId,
        mockDashboardType,
        mockStats,
        mockDateBasis,
        `${currentYear}-01-01`,
        `${currentYear}-12-31`,
        currentYear,
      );
    });

    it('should fetch from API when cache miss for past year', async () => {
      const startDate = new Date(`${pastYear}-01-01`);
      const endDate = new Date(`${pastYear}-12-31`);

      const mockBlock = {
        year: pastYear,
        startDate,
        endDate,
      };

      findMissingBlocks.mockReturnValue([mockBlock]);

      // Mock cache miss
      getCachedStats.mockResolvedValue(null);

      // Mock API response
      const mockStats = {
        recordDeltaDataAdded: {},
        recordSnapshotDataAdded: {},
        usageDeltaData: {},
        usageSnapshotData: {},
      };
      statsApiClient.getStats.mockResolvedValueOnce(mockStats);

      const result = await fetchStatsWithYearlyBlocks({
        communityId: mockCommunityId,
        dashboardType: mockDashboardType,
        startDate,
        endDate,
        dateBasis: mockDateBasis,
        currentStats: [],
      });

      // Should cache with past year (no serverFetchTimestamp for past years)
      expect(setCachedStats).toHaveBeenCalledWith(
        mockCommunityId,
        mockDashboardType,
        mockStats,
        mockDateBasis,
        `${pastYear}-01-01`,
        `${pastYear}-12-31`,
        pastYear,
      );
    });

    it('should set currentYearLastUpdated from cache for current year', async () => {
      const startDate = new Date(`${currentYear}-01-01`);
      const endDate = new Date(`${currentYear}-12-31`);
      const mockServerFetchTime = Date.now() - 5000; // 5 seconds ago

      const mockBlock = {
        year: currentYear,
        startDate,
        endDate,
      };

      findMissingBlocks.mockReturnValue([mockBlock]);

      // Mock cache hit with server fetch timestamp
      const mockCachedData = {
        recordDeltaDataAdded: {},
        recordSnapshotDataAdded: {},
        usageDeltaData: {},
        usageSnapshotData: {},
      };

      getCachedStats.mockResolvedValue({
        data: mockCachedData,
        serverFetchTimestamp: mockServerFetchTime,
        year: currentYear,
      });

      const result = await fetchStatsWithYearlyBlocks({
        communityId: mockCommunityId,
        dashboardType: mockDashboardType,
        startDate,
        endDate,
        dateBasis: mockDateBasis,
        currentStats: [],
      });

      expect(result.currentYearLastUpdated).toBe(mockServerFetchTime);
    });

    it('should set currentYearLastUpdated from API fetch for current year', async () => {
      const startDate = new Date(`${currentYear}-01-01`);
      const endDate = new Date(`${currentYear}-12-31`);

      const mockBlock = {
        year: currentYear,
        startDate,
        endDate,
      };

      findMissingBlocks.mockReturnValue([mockBlock]);

      // Mock cache miss
      getCachedStats.mockResolvedValue(null);

      // Mock API response - override the default mock for this test
      const mockStats = {
        recordDeltaDataAdded: {},
        recordSnapshotDataAdded: {},
        usageDeltaData: {},
        usageSnapshotData: {},
      };
      
      // Restore the spy and set up a fresh mock for this test
      if (statsApiClient.getStats.mockRestore) {
        statsApiClient.getStats.mockRestore();
      }
      jest.spyOn(statsApiClient, 'getStats').mockResolvedValue(mockStats);

      const beforeFetch = Date.now();
      const result = await fetchStatsWithYearlyBlocks({
        communityId: mockCommunityId,
        dashboardType: mockDashboardType,
        startDate,
        endDate,
        dateBasis: mockDateBasis,
        currentStats: [],
      });
      const afterFetch = Date.now();
      
      // Verify API was called
      expect(statsApiClient.getStats).toHaveBeenCalled();

      // Should have currentYearLastUpdated set from server fetch
      expect(result).toBeDefined();
      expect(result.currentYearLastUpdated).toBeDefined();
      expect(result.currentYearLastUpdated).not.toBeNull();
      expect(typeof result.currentYearLastUpdated).toBe('number');
      expect(result.currentYearLastUpdated).toBeGreaterThanOrEqual(beforeFetch);
      expect(result.currentYearLastUpdated).toBeLessThanOrEqual(afterFetch);
    });

    it('should handle mixed cache hits and misses', async () => {
      const startDate = new Date(`${pastYear}-01-01`);
      const endDate = new Date(`${currentYear}-12-31`);

      const pastBlock = {
        year: pastYear,
        startDate: new Date(`${pastYear}-01-01`),
        endDate: new Date(`${pastYear}-12-31`),
      };

      const currentBlock = {
        year: currentYear,
        startDate: new Date(`${currentYear}-01-01`),
        endDate: new Date(`${currentYear}-12-31`),
      };

      findMissingBlocks.mockReturnValue([pastBlock, currentBlock]);

      // Mock cache hit for past year, miss for current year
      const mockCachedPastData = {
        recordDeltaDataAdded: {},
        recordSnapshotDataAdded: {},
        usageDeltaData: {},
        usageSnapshotData: {},
      };

      getCachedStats
        .mockResolvedValueOnce({
          data: mockCachedPastData,
          serverFetchTimestamp: null,
          year: pastYear,
        })
        .mockResolvedValueOnce(null); // Cache miss for current year

      // Mock API response for current year
      const mockStats = {
        recordDeltaDataAdded: {},
        recordSnapshotDataAdded: {},
        usageDeltaData: {},
        usageSnapshotData: {},
      };
      statsApiClient.getStats.mockResolvedValueOnce(mockStats);

      const result = await fetchStatsWithYearlyBlocks({
        communityId: mockCommunityId,
        dashboardType: mockDashboardType,
        startDate,
        endDate,
        dateBasis: mockDateBasis,
        currentStats: [],
      });

      // Should check cache for both blocks
      expect(getCachedStats).toHaveBeenCalledTimes(2);

      // Should only fetch API for current year
      expect(statsApiClient.getStats).toHaveBeenCalledTimes(1);

      // Should cache the current year data
      expect(setCachedStats).toHaveBeenCalledTimes(1);
      expect(setCachedStats).toHaveBeenCalledWith(
        expect.anything(),
        expect.anything(),
        expect.anything(),
        expect.anything(),
        expect.anything(),
        expect.anything(),
        currentYear, // Should cache with current year
      );
    });

    it('should not update lastUpdated when all data is cached', async () => {
      const startDate = new Date(`${pastYear}-01-01`);
      const endDate = new Date(`${pastYear}-12-31`);

      // No missing blocks - all data already in memory
      findMissingBlocks.mockReturnValue([]);

      const mockCurrentStats = [
        {
          year: pastYear,
          recordDeltaDataAdded: {},
          recordSnapshotDataAdded: {},
          usageDeltaData: {},
          usageSnapshotData: {},
        },
      ];

      const result = await fetchStatsWithYearlyBlocks({
        communityId: mockCommunityId,
        dashboardType: mockDashboardType,
        startDate,
        endDate,
        dateBasis: mockDateBasis,
        currentStats: mockCurrentStats,
      });

      // Should not check cache (no missing blocks)
      expect(getCachedStats).not.toHaveBeenCalled();

      // Should not fetch from API
      expect(statsApiClient.getStats).not.toHaveBeenCalled();

      // Should not update lastUpdated
      expect(result.lastUpdated).toBeUndefined();
      expect(result.currentYearLastUpdated).toBeUndefined();
    });

    it('should call getCachedStats with correct parameters', async () => {
      const startDate = new Date(`${currentYear}-01-01`);
      const endDate = new Date(`${currentYear}-12-31`);

      const mockBlock = {
        year: currentYear,
        startDate,
        endDate,
      };

      findMissingBlocks.mockReturnValue([mockBlock]);
      getCachedStats.mockResolvedValue(null);
      statsApiClient.getStats.mockResolvedValue({
        recordDeltaDataAdded: {},
        recordSnapshotDataAdded: {},
        usageDeltaData: {},
        usageSnapshotData: {},
      });

      await fetchStatsWithYearlyBlocks({
        communityId: mockCommunityId,
        dashboardType: mockDashboardType,
        startDate,
        endDate,
        dateBasis: mockDateBasis,
        currentStats: [],
      });

      expect(getCachedStats).toHaveBeenCalledWith(
        mockCommunityId,
        mockDashboardType,
        mockDateBasis,
        `${currentYear}-01-01`,
        `${currentYear}-12-31`,
      );
    });

    it('should handle cache errors gracefully', async () => {
      const startDate = new Date(`${currentYear}-01-01`);
      const endDate = new Date(`${currentYear}-12-31`);

      const mockBlock = {
        year: currentYear,
        startDate,
        endDate,
      };

      findMissingBlocks.mockReturnValue([mockBlock]);

      // Mock cache error - getCachedStats returns null on error (doesn't throw)
      getCachedStats.mockResolvedValue(null);

      // Mock API response
      const mockStats = {
        recordDeltaDataAdded: {},
        recordSnapshotDataAdded: {},
        usageDeltaData: {},
        usageSnapshotData: {},
      };
      statsApiClient.getStats.mockResolvedValueOnce(mockStats);

      // Should not throw, but fall back to API
      const result = await fetchStatsWithYearlyBlocks({
        communityId: mockCommunityId,
        dashboardType: mockDashboardType,
        startDate,
        endDate,
        dateBasis: mockDateBasis,
        currentStats: [],
      });

      // Should return result
      expect(result).toBeDefined();

      // Should check cache first
      expect(getCachedStats).toHaveBeenCalled();

      // Should fall back to API when cache fails/returns null
      expect(statsApiClient.getStats).toHaveBeenCalled();
    });
  });
});

