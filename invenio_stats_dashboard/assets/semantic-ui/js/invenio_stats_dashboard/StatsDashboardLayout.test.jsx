/**
 * Part of Invenio-Stats-Dashboard
 * Copyright (C) 2025 Mesh Research
 *
 * Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
 * it under the terms of the MIT License; see LICENSE file for more details.
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { StatsDashboardLayout } from './StatsDashboardLayout';
import { getCachedStats, setCachedStats, clearCachedStats } from './utils/statsCache';
import { fetchStats } from './api/api';
import { statsApiClient } from './api/api';

// Mock dependencies
jest.mock('./utils/statsCache', () => ({
  getCachedStats: jest.fn(),
  setCachedStats: jest.fn(),
  clearCachedStats: jest.fn(),
  formatCacheTimestamp: jest.fn((timestamp) => timestamp ? new Date(timestamp).toLocaleString() : 'Unknown')
}));

jest.mock('./api/api', () => ({
  fetchStats: jest.fn(),
  statsApiClient: {
    getStats: jest.fn()
  }
}));

const mockDashboardConfig = {
  layout: {
    tabs: [
      {
        name: 'content',
        label: 'Content',
        icon: 'file text',
        rows: [
          {
            name: 'test-row',
            components: [
              {
                type: 'SingleStatRecordCount',
                title: 'Records',
                icon: 'file'
              }
            ]
          }
        ]
      }
    ]
  },
  show_title: true,
  show_description: false,
  max_history_years: 15,
  default_granularity: 'day',
  default_record_start_basis: 'added'
};

const mockCommunity = {
  id: 'test-community',
  metadata: {
    title: 'Test Community'
  }
};

const mockRawStats = {
  record_deltas_created: [],
  record_deltas_added: [],
  record_deltas_published: [],
  record_snapshots_created: [],
  record_snapshots_added: [],
  record_snapshots_published: [],
  usage_deltas: [],
  usage_snapshots: []
};

const mockTransformedStats = [
  {
    year: 2024,
    recordDeltaDataCreated: {
      global: {
        records: [
          {
            id: 'global',
            name: 'Global',
            data: [
              { value: [new Date('2024-01-01T00:00:00.000Z'), 10] },
              { value: [new Date('2024-01-02T00:00:00.000Z'), 20] }
            ]
          }
        ]
      }
    },
    recordDeltaDataAdded: {
      global: {
        records: [
          {
            id: 'global',
            name: 'Global',
            data: [
              { value: [new Date('2024-01-01T00:00:00.000Z'), 5] },
              { value: [new Date('2024-01-02T00:00:00.000Z'), 15] }
            ]
          }
        ]
      }
    },
    recordDeltaDataPublished: {
      global: {
        records: [
          {
            id: 'global',
            name: 'Global',
            data: [
              { value: [new Date('2024-01-01T00:00:00.000Z'), 8] },
              { value: [new Date('2024-01-02T00:00:00.000Z'), 12] }
            ]
          }
        ]
      }
    },
    recordSnapshotDataCreated: {
      global: {
        records: [
          {
            id: 'global',
            name: 'Global',
            data: [
              { value: [new Date('2024-01-01T00:00:00.000Z'), 100] },
              { value: [new Date('2024-01-02T00:00:00.000Z'), 120] }
            ]
          }
        ]
      }
    },
    recordSnapshotDataAdded: {
      global: {
        records: [
          {
            id: 'global',
            name: 'Global',
            data: [
              { value: [new Date('2024-01-01T00:00:00.000Z'), 95] },
              { value: [new Date('2024-01-02T00:00:00.000Z'), 110] }
            ]
          }
        ]
      }
    },
    recordSnapshotDataPublished: {
      global: {
        records: [
          {
            id: 'global',
            name: 'Global',
            data: [
              { value: [new Date('2024-01-01T00:00:00.000Z'), 90] },
              { value: [new Date('2024-01-02T00:00:00.000Z'), 102] }
            ]
          }
        ]
      }
    },
    usageDeltaData: {
      global: {
        downloads: [
          {
            id: 'global',
            name: 'Global',
            data: [
              { value: [new Date('2024-01-01T00:00:00.000Z'), 50] },
              { value: [new Date('2024-01-02T00:00:00.000Z'), 75] }
            ]
          }
        ]
      }
    },
    usageSnapshotData: {
      global: {
        downloads: [
          {
            id: 'global',
            name: 'Global',
            data: [
              { value: [new Date('2024-01-01T00:00:00.000Z'), 500] },
              { value: [new Date('2024-01-02T00:00:00.000Z'), 575] }
            ]
          }
        ]
      }
    }
  }
];

describe('StatsDashboardLayout with caching', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    clearCachedStats.mockClear();
    getCachedStats.mockReturnValue(null);
    setCachedStats.mockClear();
    statsApiClient.getStats.mockResolvedValue(mockRawStats);
    fetchStats.mockImplementation(({ onStateChange, isMounted, useTestData }) => {
      // Simulate the API behavior
      if (onStateChange) {
        onStateChange({
          type: 'loading_started',
          stats: null,
          isLoading: true,
          isUpdating: false,
          error: null
        });

        setTimeout(() => {
          if (isMounted && isMounted()) {
            onStateChange({
              type: 'fresh_data_loaded',
              stats: mockTransformedStats,
              isLoading: false,
              isUpdating: false,
              lastUpdated: Date.now(),
              error: null
            });
          }
        }, 100);
      }

      return Promise.resolve({
        stats: mockTransformedStats,
        lastUpdated: Date.now(),
        error: null
      });
    });
  });

  it('should display data when loaded', async () => {
    // Mock API to simulate data loading flow
    fetchStats.mockImplementation(({ onStateChange, isMounted }) => {
      // Simulate loading state
      if (onStateChange && isMounted && isMounted()) {
        onStateChange({
          type: 'loading_started',
          stats: null,
          isLoading: true,
          isUpdating: false,
          error: null
        });
      }

      // Simulate data loaded callback
      setTimeout(() => {
        if (onStateChange && isMounted && isMounted()) {
          onStateChange({
            type: 'data_loaded',
            stats: mockTransformedStats,
            isLoading: false,
            isUpdating: false,
            lastUpdated: Date.now(),
            error: null
          });
        }
      }, 100);

      return Promise.resolve({
        stats: mockTransformedStats,
        lastUpdated: Date.now(),
        error: null
      });
    });

    render(
      <StatsDashboardLayout
        dashboardConfig={mockDashboardConfig}
        dashboardType="community"
        community={mockCommunity}
        containerClassNames=""
        sidebarClassNames=""
        bodyClassNames=""
      />
    );

    // Should not show loading state when cached data is available
    await waitFor(() => {
      expect(screen.queryByText('Loading statistics...')).not.toBeInTheDocument();
    });

    // Should call the API function
    await waitFor(() => {
      expect(fetchStats).toHaveBeenCalled();
    });
  });

        it('should show loading state when no cached data is available', async () => {
    // Use the default mock implementation which shows loading state
    render(
      <StatsDashboardLayout
        dashboardConfig={mockDashboardConfig}
        dashboardType="community"
        community={mockCommunity}
        containerClassNames=""
        sidebarClassNames=""
        bodyClassNames=""
      />
    );

    // Should show loading state initially
    expect(screen.getByText('Loading statistics...')).toBeInTheDocument();

    // Should call the API function
    await waitFor(() => {
      expect(fetchStats).toHaveBeenCalled();
    });
  });

        it('should show update status message', async () => {
    // Mock API to simulate cached data with updating flow
    fetchStats.mockImplementation(({ onStateChange, isMounted }) => {
      // Simulate cached data callback
      if (onStateChange && isMounted && isMounted()) {
        onStateChange({
          type: 'cached_data_loaded',
          stats: mockTransformedStats,
          isLoading: false,
          isUpdating: true,
          error: null
        });
      }

      // Simulate fresh data callback
      setTimeout(() => {
        if (onStateChange && isMounted && isMounted()) {
          onStateChange({
            type: 'fresh_data_loaded',
            stats: mockTransformedStats,
            isLoading: false,
            isUpdating: false,
            lastUpdated: Date.now(),
            error: null
          });
        }
      }, 100);

      return Promise.resolve({
        stats: mockTransformedStats,
        lastUpdated: Date.now(),
        error: null
      });
    });

    render(
      <StatsDashboardLayout
        dashboardConfig={mockDashboardConfig}
        dashboardType="community"
        community={mockCommunity}
        containerClassNames=""
        sidebarClassNames=""
        bodyClassNames=""
      />
    );

    // Should show updating message initially
    expect(screen.getByText('Updating data...')).toBeInTheDocument();

    // After fetch completes, should show last updated message
    await waitFor(() => {
      expect(screen.getByText(/Last updated:/)).toBeInTheDocument();
    });
  });

        it('should handle global dashboard type', async () => {
    // Use the default mock implementation
    const globalDashboardConfig = {
      ...mockDashboardConfig,
      dashboard_type: "global"
    };
    
    render(
      <StatsDashboardLayout
        dashboardConfig={globalDashboardConfig}
        dashboardType="global"
        community={null}
        containerClassNames=""
        sidebarClassNames=""
        bodyClassNames=""
      />
    );

    await waitFor(() => {
      expect(fetchStats).toHaveBeenCalledWith(
        expect.objectContaining({
          communityId: undefined,
          dashboardType: 'global',
          useTestData: true,
        })
      );
    });
  });

  it('should use test data when configured', async () => {
    const testDataConfig = {
      ...mockDashboardConfig,
      use_test_data: true
    };

    render(
      <StatsDashboardLayout
        dashboardConfig={testDataConfig}
        dashboardType="community"
        community={mockCommunity}
        containerClassNames=""
        sidebarClassNames=""
        bodyClassNames=""
      />
    );

    await waitFor(() => {
      expect(fetchStats).toHaveBeenCalledWith(
        expect.objectContaining({
          communityId: 'test-community',
          dashboardType: 'community',
          community: mockCommunity,
          useTestData: true
        })
      );
    });
  });

  it('should use production data when test data is disabled', async () => {
    const productionConfig = {
      ...mockDashboardConfig,
      use_test_data: false
    };

    render(
      <StatsDashboardLayout
        dashboardConfig={productionConfig}
        dashboardType="community"
        community={mockCommunity}
        containerClassNames=""
        sidebarClassNames=""
        bodyClassNames=""
      />
    );

    await waitFor(() => {
      expect(fetchStats).toHaveBeenCalledWith(
        expect.objectContaining({
          communityId: 'test-community',
          dashboardType: 'community',
          community: mockCommunity,
          useTestData: false
        })
      );
    });
  });
});
