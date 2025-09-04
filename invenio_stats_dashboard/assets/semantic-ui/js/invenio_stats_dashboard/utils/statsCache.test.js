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
  clearCachedStats,
  getCacheInfo,
  formatCacheTimestamp
} from './statsCache';

// Mock localStorage
const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
  key: jest.fn(),
  length: 0
};

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock
});

describe('statsCache', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorageMock.getItem.mockReturnValue(null);
  });

  describe('setCachedStats', () => {
    it('should store data in localStorage with correct key format', () => {
      const mockData = { test: 'data' };
      const communityId = 'test-community';
      const dashboardType = 'community';

      setCachedStats(communityId, dashboardType, mockData);

      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        expect.stringContaining('invenio_stats_dashboard_1.0_'),
        expect.stringContaining('"data":{"test":"data"}')
      );
    });

    it('should handle global dashboard type', () => {
      const mockData = { test: 'data' };
      const dashboardType = 'global';

      setCachedStats(null, dashboardType, mockData);

      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        expect.stringContaining('"communityId":"global"'),
        expect.any(String)
      );
    });

    it('should include date parameters in cache key', () => {
      const mockData = { test: 'data' };
      const communityId = 'test-community';
      const dashboardType = 'community';
      const startDate = '2023-01-01';
      const endDate = '2023-12-31';

      setCachedStats(communityId, dashboardType, mockData, startDate, endDate);

      const setItemCall = localStorageMock.setItem.mock.calls[0];
      const cacheKey = setItemCall[0];
      const cacheData = JSON.parse(setItemCall[1]);

      expect(cacheKey).toContain('"startDate":"2023-01-01"');
      expect(cacheKey).toContain('"endDate":"2023-12-31"');
      expect(cacheData.timestamp).toBeDefined();
      expect(cacheData.version).toBe('1.0');
    });
  });

  describe('getCachedStats', () => {
    it('should return cached data when valid', () => {
      const mockData = { test: 'data' };
      const cacheData = {
        data: mockData,
        timestamp: Date.now(),
        version: '1.0'
      };

      localStorageMock.getItem.mockReturnValue(JSON.stringify(cacheData));

      const result = getCachedStats('test-community', 'community');

      expect(result).toEqual(mockData);
    });

    it('should return null when no cached data exists', () => {
      localStorageMock.getItem.mockReturnValue(null);

      const result = getCachedStats('test-community', 'community');

      expect(result).toBeNull();
    });

    it('should return null and remove expired cache', () => {
      const expiredCacheData = {
        data: { test: 'data' },
        timestamp: Date.now() - (8 * 24 * 60 * 60 * 1000), // 8 days ago
        version: '1.0'
      };

      localStorageMock.getItem.mockReturnValue(JSON.stringify(expiredCacheData));

      const result = getCachedStats('test-community', 'community');

      expect(result).toBeNull();
      expect(localStorageMock.removeItem).toHaveBeenCalled();
    });
  });

  describe('clearCachedStats', () => {
    it('should remove all stats cache entries', () => {
      // Mock localStorage keys
      Object.defineProperty(localStorageMock, 'length', { value: 3 });
      localStorageMock.key
        .mockReturnValueOnce('invenio_stats_dashboard_1.0_test1')
        .mockReturnValueOnce('other_key')
        .mockReturnValueOnce('invenio_stats_dashboard_1.0_test2');

      clearCachedStats();

      expect(localStorageMock.removeItem).toHaveBeenCalledWith('invenio_stats_dashboard_1.0_test1');
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('invenio_stats_dashboard_1.0_test2');
      expect(localStorageMock.removeItem).not.toHaveBeenCalledWith('other_key');
    });
  });

  describe('formatCacheTimestamp', () => {
    it('should format timestamp correctly', () => {
      const timestamp = 1640995200000; // 2022-01-01 00:00:00 UTC
      const result = formatCacheTimestamp(timestamp);

      expect(result).toMatch(/2022/);
      expect(result).toMatch(/Jan/);
    });
  });

  describe('getCacheInfo', () => {
    it('should return cache information', () => {
      Object.defineProperty(localStorageMock, 'length', { value: 1 });
      localStorageMock.key.mockReturnValue('invenio_stats_dashboard_1.0_test');

      const cacheData = {
        data: { test: 'data' },
        timestamp: Date.now(),
        version: '1.0'
      };
      localStorageMock.getItem.mockReturnValue(JSON.stringify(cacheData));

      const result = getCacheInfo();

      expect(result.totalEntries).toBe(1);
      expect(result.entries).toHaveLength(1);
      expect(result.entries[0].isValid).toBe(true);
    });
  });
});
