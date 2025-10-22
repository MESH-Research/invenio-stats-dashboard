/**
 * Part of Invenio-Stats-Dashboard
 * Copyright (C) 2025 Mesh Research
 *
 * Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
 * it under the terms of the MIT License; see LICENSE file for more details.
 */

import {
  setCachedStats,
  getCachedStats,
  clearAllCachedStats,
  clearCachedStatsForKey
} from './statsCache';

describe('StatsCache', () => {
  let consoleSpy;

  beforeEach(() => {
    // Set up console spy for each test
    consoleSpy = jest.spyOn(console, 'log').mockImplementation(() => {});
  });

  afterEach(() => {
    consoleSpy.mockRestore();
  });

  describe('setCachedStats', () => {
    it('should log cache attempt with correct parameters', async () => {
      const communityId = 'test-community';
      const dashboardType = 'community';
      const transformedData = { test: 'data' };
      const startDate = '2024-01-01';
      const endDate = '2024-01-31';

      await setCachedStats(communityId, dashboardType, transformedData, startDate, endDate);

      expect(consoleSpy).toHaveBeenCalledWith('setCachedStats called with:', {
        communityId,
        dashboardType,
        startDate,
        endDate
      });
      expect(consoleSpy).toHaveBeenCalledWith('Generated cache key:', expect.any(String));
    });

    it('should handle null dates', async () => {
      await setCachedStats('test-community', 'community', { test: 'data' }, null, null);

      expect(consoleSpy).toHaveBeenCalledWith('setCachedStats called with:', {
        communityId: 'test-community',
        dashboardType: 'community',
        startDate: null,
        endDate: null
      });
      expect(consoleSpy).toHaveBeenCalledWith('Generated cache key:', expect.any(String));
    });
  });

  describe('getCachedStats', () => {
    it('should log retrieval attempt and return null', async () => {
      const result = await getCachedStats('test-community', 'community', '2024-01-01', '2024-01-31');

      expect(consoleSpy).toHaveBeenCalledWith('getCachedStats called with:', {
        communityId: 'test-community',
        dashboardType: 'community',
        startDate: '2024-01-01',
        endDate: '2024-01-31'
      });
      expect(consoleSpy).toHaveBeenCalledWith('Generated cache key:', expect.any(String));
      expect(result).toBeNull();
    });
  });

  describe('clearAllCachedStats', () => {
    it('should log clear all attempt', async () => {
      await clearAllCachedStats();

      expect(consoleSpy).toHaveBeenCalledWith('clearAllCachedStats called');
    });
  });

  describe('clearCachedStatsForKey', () => {
    it('should log clear specific key attempt', async () => {
      const baseCacheKey = 'test-key';
      await clearCachedStatsForKey(baseCacheKey);

      expect(consoleSpy).toHaveBeenCalledWith('clearCachedStatsForKey called for:', baseCacheKey);
    });
  });
});