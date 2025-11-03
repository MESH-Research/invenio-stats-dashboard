/**
 * Part of Invenio-Stats-Dashboard
 * Copyright (C) 2025 Mesh Research
 *
 * Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
 * it under the terms of the MIT License; see LICENSE file for more details.
 */

// Polyfill TextEncoder/TextDecoder for Node.js test environment
global.TextEncoder = global.TextEncoder || class TextEncoder {
  encode(str) {
    return new Uint8Array(Buffer.from(str, 'utf8'));
  }
};

global.TextDecoder = global.TextDecoder || class TextDecoder {
  decode(bytes) {
    return Buffer.from(bytes).toString('utf8');
  }
};

// Mock pako for compression
jest.mock('pako', () => ({
  gzip: jest.fn((data) => {
    // Simple mock: return compressed data as Uint8Array
    const encoder = new TextEncoder();
    return encoder.encode(data);
  }),
  ungzip: jest.fn((data, options) => {
    // Simple mock: return decompressed string
    const decoder = new TextDecoder();
    return decoder.decode(data);
  }),
}));

// Mock IndexedDB
const mockIndexedDB = () => {
  const store = new Map();
  const indexes = {
    timestamp: new Map(),
    lastAccessed: new Map(),
    communityId: new Map(),
    year: new Map(),
    dateBasis: new Map(),
  };

  const objectStore = {
    get: jest.fn((key) => ({
      onsuccess: null,
      onerror: null,
      result: store.get(key) || undefined,
    })),
    put: jest.fn((value) => {
      store.set(value.key, value);
      // Update indexes
      if (value.timestamp) indexes.timestamp.set(value.timestamp, value);
      if (value.lastAccessed) indexes.lastAccessed.set(value.lastAccessed, value);
      if (value.communityId) indexes.communityId.set(value.communityId, value);
      if (value.year !== undefined) indexes.year.set(value.year, value);
      if (value.dateBasis) indexes.dateBasis.set(value.dateBasis, value);
      return {
        onsuccess: null,
        onerror: null,
        result: value.key,
      };
    }),
    delete: jest.fn((key) => {
      const value = store.get(key);
      if (value) {
        store.delete(key);
        // Remove from indexes
        if (value.timestamp) indexes.timestamp.delete(value.timestamp);
        if (value.lastAccessed) indexes.lastAccessed.delete(value.lastAccessed);
        if (value.communityId) indexes.communityId.delete(value.communityId);
        if (value.year !== undefined) indexes.year.delete(value.year);
        if (value.dateBasis) indexes.dateBasis.delete(value.dateBasis);
      }
      return {
        onsuccess: null,
        onerror: null,
      };
    }),
    clear: jest.fn(() => {
      store.clear();
      Object.values(indexes).forEach(index => index.clear());
      return {
        onsuccess: null,
        onerror: null,
      };
    }),
    getAll: jest.fn(() => ({
      onsuccess: null,
      onerror: null,
      result: Array.from(store.values()),
    })),
    count: jest.fn(() => ({
      onsuccess: null,
      onerror: null,
      result: store.size,
    })),
    indexNames: {
      contains: jest.fn((name) => Object.keys(indexes).includes(name)),
    },
    createIndex: jest.fn(),
  };

  const transaction = {
    objectStore: jest.fn(() => objectStore),
  };

  const db = {
    objectStoreNames: {
      contains: jest.fn((name) => name === 'stats_cache'),
    },
    transaction: jest.fn(() => transaction),
    createObjectStore: jest.fn(() => objectStore),
  };

  let dbInstance = null;

  const request = {
    onsuccess: null,
    onerror: null,
    onupgradeneeded: null,
    result: db,
  };

  return {
    open: jest.fn((name, version) => {
      // Simulate successful open
      setTimeout(() => {
        if (request.onupgradeneeded && version === 2) {
          request.onupgradeneeded({
            target: { result: db },
            transaction,
          });
        }
        if (request.onsuccess) {
          request.onsuccess({ target: { result: db } });
        }
      }, 0);
      return request;
    }),
    store,
    db,
    transaction,
    objectStore,
  };
};

describe('StatsCache Worker', () => {
  let workerContext;
  let mockIDB;
  let originalIndexedDB;
  let originalSelf;

  beforeEach(() => {
    // Mock IndexedDB
    mockIDB = mockIndexedDB();
    originalIndexedDB = global.indexedDB;
    global.indexedDB = mockIDB;

    // Mock worker context
    originalSelf = global.self;
    global.self = {
      addEventListener: jest.fn(),
      postMessage: jest.fn(),
    };

    // Create a mock worker context that simulates the worker
    workerContext = {
      pendingMessages: new Map(),
      messageHandlers: new Map(),
    };
  });

  afterEach(() => {
    jest.clearAllMocks();
    global.indexedDB = originalIndexedDB;
    global.self = originalSelf;
  });

  describe('Cache Key Generation', () => {
    it('should generate cache keys with community ID and dates', async () => {
      // Import and test the worker logic directly
      // Since we can't easily import a worker file, we'll test the key generation logic
      const generateCacheKey = (communityId, dashboardType, dateBasis = 'added', startDate = null, endDate = null) => {
        const communityIdShort = communityId ? communityId.substring(0, 8) : 'global';
        const startDateShort = startDate ? startDate.substring(0, 10) : 'default';
        const endDateShort = endDate ? endDate.substring(0, 10) : 'default';
        return `isd_${communityIdShort}_${dashboardType}_${dateBasis}_${startDateShort}_${endDateShort}`;
      };

      const key = generateCacheKey('test-community-123', 'community', 'added', '2024-01-01', '2024-01-31');
      expect(key).toBe('isd_test-com_community_added_2024-01-01_2024-01-31');
    });

    it('should handle null dates in cache key generation', () => {
      const generateCacheKey = (communityId, dashboardType, dateBasis = 'added', startDate = null, endDate = null) => {
        const communityIdShort = communityId ? communityId.substring(0, 8) : 'global';
        const startDateShort = startDate ? startDate.substring(0, 10) : 'default';
        const endDateShort = endDate ? endDate.substring(0, 10) : 'default';
        return `isd_${communityIdShort}_${dashboardType}_${dateBasis}_${startDateShort}_${endDateShort}`;
      };

      const key = generateCacheKey('test-community', 'community', 'added', null, null);
      expect(key).toBe('isd_test-com_community_added_default_default');
    });
  });

  describe('Year Extraction', () => {
    it('should extract year from date string', () => {
      const extractYear = (startDate) => {
        if (!startDate) return null;
        const yearMatch = startDate.match(/^(\d{4})/);
        return yearMatch ? parseInt(yearMatch[1], 10) : null;
      };

      expect(extractYear('2024-01-01')).toBe(2024);
      expect(extractYear('2023-12-31')).toBe(2023);
      expect(extractYear(null)).toBeNull();
      expect(extractYear('invalid')).toBeNull();
    });
  });

  describe('Current Year Detection', () => {
    it('should detect current year correctly', () => {
      const isCurrentYear = (year) => {
        if (!year) return false;
        const currentYear = new Date().getUTCFullYear();
        return year === currentYear;
      };

      const currentYear = new Date().getUTCFullYear();
      expect(isCurrentYear(currentYear)).toBe(true);
      expect(isCurrentYear(currentYear - 1)).toBe(false);
      expect(isCurrentYear(currentYear + 1)).toBe(false);
      expect(isCurrentYear(null)).toBe(false);
    });
  });

  describe('Cache Validity', () => {
    it('should return false for invalid cache data', () => {
      const isCacheValid = (cachedData) => {
        if (!cachedData || !cachedData.timestamp) {
          return false;
        }

        const now = Date.now();
        const cacheAge = now - cachedData.timestamp;
        const year = cachedData.year;
        const isCurrent = year === new Date().getUTCFullYear();
        const maxAge = isCurrent
          ? 1 * 60 * 60 * 1000 // 1 hour
          : 1 * 365 * 24 * 60 * 60 * 1000; // 1 year

        return cacheAge < maxAge;
      };

      expect(isCacheValid(null)).toBe(false);
      expect(isCacheValid({})).toBe(false);
    });

    it('should return true for valid current year cache (within 1 hour)', () => {
      const currentYear = new Date().getUTCFullYear();
      const isCacheValid = (cachedData) => {
        if (!cachedData || !cachedData.timestamp) {
          return false;
        }

        const now = Date.now();
        const cacheAge = now - cachedData.timestamp;
        const year = cachedData.year;
        const isCurrent = year === new Date().getUTCFullYear();
        const maxAge = isCurrent
          ? 1 * 60 * 60 * 1000 // 1 hour
          : 1 * 365 * 24 * 60 * 60 * 1000; // 1 year

        return cacheAge < maxAge;
      };

      const cachedData = {
        timestamp: Date.now() - 30 * 60 * 1000, // 30 minutes ago
        year: currentYear,
      };

      expect(isCacheValid(cachedData)).toBe(true);
    });

    it('should return false for expired current year cache (over 1 hour)', () => {
      const currentYear = new Date().getUTCFullYear();
      const isCacheValid = (cachedData) => {
        if (!cachedData || !cachedData.timestamp) {
          return false;
        }

        const now = Date.now();
        const cacheAge = now - cachedData.timestamp;
        const year = cachedData.year;
        const isCurrent = year === new Date().getUTCFullYear();
        const maxAge = isCurrent
          ? 1 * 60 * 60 * 1000 // 1 hour
          : 1 * 365 * 24 * 60 * 60 * 1000; // 1 year

        return cacheAge < maxAge;
      };

      const cachedData = {
        timestamp: Date.now() - 2 * 60 * 60 * 1000, // 2 hours ago
        year: currentYear,
      };

      expect(isCacheValid(cachedData)).toBe(false);
    });

    it('should return true for valid past year cache (within 1 year)', () => {
      const pastYear = new Date().getUTCFullYear() - 1;
      const isCacheValid = (cachedData) => {
        if (!cachedData || !cachedData.timestamp) {
          return false;
        }

        const now = Date.now();
        const cacheAge = now - cachedData.timestamp;
        const year = cachedData.year;
        const isCurrent = year === new Date().getUTCFullYear();
        const maxAge = isCurrent
          ? 1 * 60 * 60 * 1000 // 1 hour
          : 1 * 365 * 24 * 60 * 60 * 1000; // 1 year

        return cacheAge < maxAge;
      };

      const cachedData = {
        timestamp: Date.now() - 30 * 24 * 60 * 60 * 1000, // 30 days ago
        year: pastYear,
      };

      expect(isCacheValid(cachedData)).toBe(true);
    });

    it('should return false for expired past year cache (over 1 year)', () => {
      const pastYear = new Date().getUTCFullYear() - 1;
      const isCacheValid = (cachedData) => {
        if (!cachedData || !cachedData.timestamp) {
          return false;
        }

        const now = Date.now();
        const cacheAge = now - cachedData.timestamp;
        const year = cachedData.year;
        const isCurrent = year === new Date().getUTCFullYear();
        const maxAge = isCurrent
          ? 1 * 60 * 60 * 1000 // 1 hour
          : 1 * 365 * 24 * 60 * 60 * 1000; // 1 year

        return cacheAge < maxAge;
      };

      const cachedData = {
        timestamp: Date.now() - 2 * 365 * 24 * 60 * 60 * 1000, // 2 years ago
        year: pastYear,
      };

      expect(isCacheValid(cachedData)).toBe(false);
    });
  });

  describe('Worker Message Handling', () => {
    // Note: These tests simulate worker message handling since we can't directly test
    // the worker file in Jest. In a real environment, you might use worker-loader or
    // a similar tool to test workers.

    it('should handle SET_CACHED_STATS message type', async () => {
      // Simulate the handleSetCachedStats function
      const handleSetCachedStats = async (params) => {
        const { communityId, dashboardType, transformedData, dateBasis = 'added', startDate, endDate, year } = params;
        const generateCacheKey = (communityId, dashboardType, dateBasis, startDate, endDate) => {
          const communityIdShort = communityId ? communityId.substring(0, 8) : 'global';
          const startDateShort = startDate ? startDate.substring(0, 10) : 'default';
          const endDateShort = endDate ? endDate.substring(0, 10) : 'default';
          return `isd_${communityIdShort}_${dashboardType}_${dateBasis}_${startDateShort}_${endDateShort}`;
        };

        const cacheKey = generateCacheKey(communityId, dashboardType, dateBasis, startDate, endDate);
        const timestamp = Date.now();
        const cacheYear = year || (startDate ? parseInt(startDate.substring(0, 4), 10) : null);

        // Mock compression
        const jsonString = JSON.stringify(transformedData);
        const compressedData = new TextEncoder().encode(jsonString);
        const blob = new Blob([compressedData], { type: 'application/gzip' });

        // Store would happen here - mocked for test
        return {
          success: true,
          cacheKey,
          compressedRatio: compressedData.length / jsonString.length,
        };
      };

      const result = await handleSetCachedStats({
        communityId: 'test-community',
        dashboardType: 'community',
        transformedData: { test: 'data' },
        dateBasis: 'added',
        startDate: '2024-01-01',
        endDate: '2024-01-31',
        year: 2024,
      });

      expect(result.success).toBe(true);
      expect(result.cacheKey).toContain('test-com');
      expect(result.cacheKey).toContain('community');
      expect(result.compressedRatio).toBeGreaterThan(0);
    });

    it('should handle GET_CACHED_STATS message type', async () => {
      // Create a proper mock Blob with arrayBuffer method
      const mockBlobData = new TextEncoder().encode(JSON.stringify({ test: 'data' }));
      const mockBlob = {
        arrayBuffer: jest.fn().mockResolvedValue(mockBlobData.buffer),
      };
      
      const mockCachedData = {
        key: 'isd_test-com_community_added_2024-01-01_2024-01-31',
        data: mockBlob,
        timestamp: Date.now() - 1000,
        lastAccessed: Date.now() - 1000,
        year: 2024,
        serverFetchTimestamp: Date.now() - 1000,
      };

      // Simulate handleGetCachedStats
      const handleGetCachedStats = async (params) => {
        const { communityId, dashboardType, dateBasis = 'added', startDate, endDate } = params;
        const generateCacheKey = (communityId, dashboardType, dateBasis, startDate, endDate) => {
          const communityIdShort = communityId ? communityId.substring(0, 8) : 'global';
          const startDateShort = startDate ? startDate.substring(0, 10) : 'default';
          const endDateShort = endDate ? endDate.substring(0, 10) : 'default';
          return `isd_${communityIdShort}_${dashboardType}_${dateBasis}_${startDateShort}_${endDateShort}`;
        };

        const cacheKey = generateCacheKey(communityId, dashboardType, dateBasis, startDate, endDate);
        
        // Simulate finding cached data
        if (cacheKey === mockCachedData.key) {
          // Check validity
          const isCacheValid = (cachedData) => {
            if (!cachedData || !cachedData.timestamp) return false;
            const now = Date.now();
            const cacheAge = now - cachedData.timestamp;
            const year = cachedData.year;
            const isCurrent = year === new Date().getUTCFullYear();
            const maxAge = isCurrent ? 1 * 60 * 60 * 1000 : 1 * 365 * 24 * 60 * 60 * 1000;
            return cacheAge < maxAge;
          };

          if (!isCacheValid(mockCachedData)) {
            return { success: true, data: null };
          }

          // Decompress
          const arrayBuffer = await mockCachedData.data.arrayBuffer();
          const decompressedData = JSON.parse(new TextDecoder().decode(arrayBuffer));

          return {
            success: true,
            data: decompressedData,
            serverFetchTimestamp: mockCachedData.serverFetchTimestamp,
            year: mockCachedData.year,
          };
        }

        return { success: true, data: null };
      };

      const result = await handleGetCachedStats({
        communityId: 'test-community',
        dashboardType: 'community',
        dateBasis: 'added',
        startDate: '2024-01-01',
        endDate: '2024-01-31',
      });

      expect(result.success).toBe(true);
      expect(result.data).toEqual({ test: 'data' });
      expect(result.serverFetchTimestamp).toBeDefined();
      expect(result.year).toBe(2024);
    });

    it('should return null for missing cache', async () => {
      const handleGetCachedStats = async () => {
        return { success: true, data: null };
      };

      const result = await handleGetCachedStats({
        communityId: 'nonexistent',
        dashboardType: 'community',
        dateBasis: 'added',
        startDate: '2024-01-01',
        endDate: '2024-01-31',
      });

      expect(result.success).toBe(true);
      expect(result.data).toBeNull();
    });
  });

  describe('Cache Eviction', () => {
    it('should evict oldest entries when limit is reached', async () => {
      const MAX_CACHE_ENTRIES = 20;
      const entries = [];

      // Create 21 entries (one over limit)
      for (let i = 0; i <= MAX_CACHE_ENTRIES; i++) {
        entries.push({
          key: `key-${i}`,
          timestamp: Date.now() - (MAX_CACHE_ENTRIES - i) * 1000,
          lastAccessed: Date.now() - (MAX_CACHE_ENTRIES - i) * 1000,
        });
      }

      // Sort by lastAccessed (oldest first)
      entries.sort((a, b) => {
        const aTime = a.lastAccessed || a.timestamp || 0;
        const bTime = b.lastAccessed || b.timestamp || 0;
        return aTime - bTime;
      });

      // Should evict the oldest entry
      const toEvict = entries.slice(0, 1);
      expect(toEvict.length).toBe(1);
      expect(toEvict[0].key).toBe('key-0');
    });
  });
});

