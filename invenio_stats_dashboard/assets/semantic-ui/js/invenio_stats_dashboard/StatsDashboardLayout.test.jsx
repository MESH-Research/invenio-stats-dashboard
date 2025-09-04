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
import { transformApiData } from './api/dataTransformer';

// Mock dependencies
jest.mock('./utils/statsCache');
jest.mock('./api/api');
jest.mock('./api/dataTransformer');

const mockDashboardConfig = {
  layout: {
    tabs: [
      {
        name: 'content',
        label: 'Content',
        icon: 'file text'
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

const mockTransformedStats = {
  recordDeltaDataCreated: {},
  recordDeltaDataAdded: {},
  recordDeltaDataPublished: {},
  recordSnapshotDataCreated: {},
  recordSnapshotDataAdded: {},
  recordSnapshotDataPublished: {},
  usageDeltaData: {},
  usageSnapshotData: {}
};

describe('StatsDashboardLayout with caching', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    clearCachedStats.mockClear();
    getCachedStats.mockReturnValue(null);
    setCachedStats.mockClear();
    statsApiClient.getStats.mockResolvedValue(mockRawStats);
    transformApiData.mockReturnValue(mockTransformedStats);
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
        cachedStats: null,
        freshStats: mockTransformedStats,
        lastUpdated: Date.now(),
        error: null
      });
    });
  });

        it('should display cached data immediately when available', async () => {
    // Mock API to simulate cached data flow
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
        cachedStats: mockTransformedStats,
        freshStats: mockTransformedStats,
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
    expect(screen.queryByText('Loading statistics...')).not.toBeInTheDocument();

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
        cachedStats: mockTransformedStats,
        freshStats: mockTransformedStats,
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
    render(
      <StatsDashboardLayout
        dashboardConfig={mockDashboardConfig}
        dashboardType="global"
        community={null}
        containerClassNames=""
        sidebarClassNames=""
        bodyClassNames=""
      />
    );

    await waitFor(() => {
      expect(fetchStats).toHaveBeenCalledWith({
        communityId: undefined,
        dashboardType: 'global',
        getStatsParams: undefined,
        community: null,
        isMounted: expect.any(Function),
        onStateChange: expect.any(Function),
        useTestData: true
      });
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
      expect(fetchStats).toHaveBeenCalledWith({
        communityId: 'test-community',
        dashboardType: 'community',
        getStatsParams: undefined,
        community: mockCommunity,
        isMounted: expect.any(Function),
        onStateChange: expect.any(Function),
        useTestData: true
      });
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
      expect(fetchStats).toHaveBeenCalledWith({
        communityId: 'test-community',
        dashboardType: 'community',
        getStatsParams: undefined,
        community: mockCommunity,
        isMounted: expect.any(Function),
        onStateChange: expect.any(Function),
        useTestData: false
      });
    });
  });
});
