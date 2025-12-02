// Part of the Invenio-Stats-Dashboard extension for InvenioRDM
// Copyright (C) 2025 Mesh Research
//
// Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
// it under the terms of the MIT License; see LICENSE file for more details.

import React from 'react';
import { render, screen } from '@testing-library/react';
import { StatsDashboardPage } from './StatsDashboardPage';

// Mock i18next
jest.mock('@translations/invenio_stats_dashboard/i18next', () => ({
  i18next: {
    t: (key) => key
  }
}));

// Mock the StatsDashboard context
const mockUseStatsDashboard = jest.fn();
jest.mock('./context/StatsDashboardContext', () => ({
  useStatsDashboard: () => mockUseStatsDashboard()
}));

// Mock componentsMap
jest.mock('./components/components_map', () => ({
  componentsMap: {
    'SingleStatRecordCount': () => <div data-testid="single-stat-record-count">Record Count</div>,
    'SingleStatViews': () => <div data-testid="single-stat-views">Views</div>
  }
}));

describe('StatsDashboardPage', () => {
  const mockCommunity = {
    id: 'test-community',
    metadata: {
      title: 'Test Community'
    }
  };

  const baseDashboardConfig = {
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
                  component: 'SingleStatRecordCount',
                  width: 8
                }
              ]
            }
          ]
        }
      ]
    },
    dashboard_type: 'community'
  };

  beforeEach(() => {
    jest.clearAllMocks();
    // Default mock return value
    mockUseStatsDashboard.mockReturnValue({
      dateRange: { start: new Date('2024-01-01'), end: new Date('2024-01-31') },
      isLoading: false,
      isUpdating: false,
      error: null,
      stats: []
    });
  });

  describe('Loading State', () => {
    it('should show loading message when isLoading is true and no stats', () => {
      mockUseStatsDashboard.mockReturnValue({
        dateRange: { start: new Date('2024-01-01'), end: new Date('2024-01-31') },
        isLoading: true,
        isUpdating: false,
        error: null,
        stats: null
      });

      render(
        <StatsDashboardPage
          dashboardConfig={baseDashboardConfig}
          community={mockCommunity}
          variant="content"
        />
      );

      expect(screen.getByText('Loading statistics...')).toBeInTheDocument();
    });

    it('should not show loading message when stats are available', () => {
      mockUseStatsDashboard.mockReturnValue({
        dateRange: { start: new Date('2024-01-01'), end: new Date('2024-01-31') },
        isLoading: true,
        isUpdating: false,
        error: null,
        stats: [{ year: 2024 }]
      });

      render(
        <StatsDashboardPage
          dashboardConfig={baseDashboardConfig}
          community={mockCommunity}
          variant="content"
        />
      );

      expect(screen.queryByText('Loading statistics...')).not.toBeInTheDocument();
    });
  });

  describe('Error State', () => {
    it('should show error message when error is present', () => {
      const error = new Error('Test error message');
      mockUseStatsDashboard.mockReturnValue({
        dateRange: { start: new Date('2024-01-01'), end: new Date('2024-01-31') },
        isLoading: false,
        isUpdating: false,
        error: error,
        stats: null
      });

      render(
        <StatsDashboardPage
          dashboardConfig={baseDashboardConfig}
          community={mockCommunity}
          variant="content"
        />
      );

      expect(screen.getByText('Error Loading Statistics')).toBeInTheDocument();
      expect(screen.getByText('There was an error loading the statistics. Please try again later.')).toBeInTheDocument();
    });

    it('should show debug error message in development mode', () => {
      const originalEnv = process.env.NODE_ENV;
      process.env.NODE_ENV = 'development';

      const error = new Error('Test error message');
      mockUseStatsDashboard.mockReturnValue({
        dateRange: { start: new Date('2024-01-01'), end: new Date('2024-01-31') },
        isLoading: false,
        isUpdating: false,
        error: error,
        stats: null
      });

      render(
        <StatsDashboardPage
          dashboardConfig={baseDashboardConfig}
          community={mockCommunity}
          variant="content"
        />
      );

      expect(screen.getByText('Debug:')).toBeInTheDocument();
      expect(screen.getByText('Test error message')).toBeInTheDocument();

      process.env.NODE_ENV = originalEnv;
    });
  });

  describe('No Data Messages', () => {
    it('should show first_run_incomplete message when first_run_incomplete is true', () => {
      const dashboardConfig = {
        ...baseDashboardConfig,
        first_run_incomplete: true,
        agg_in_progress: false,
        caching_in_progress: false
      };

      mockUseStatsDashboard.mockReturnValue({
        dateRange: { start: new Date('2024-01-01'), end: new Date('2024-01-31') },
        isLoading: false,
        isUpdating: false,
        error: null,
        stats: null
      });

      render(
        <StatsDashboardPage
          dashboardConfig={dashboardConfig}
          community={mockCommunity}
          variant="content"
        />
      );

      expect(screen.getByText('No Data Available')).toBeInTheDocument();
      expect(screen.getByText('Initial calculation of statistics is still in progress. Check back again in a few hours.')).toBeInTheDocument();
    });

    it('should show agg_in_progress message when agg_in_progress is true', () => {
      const dashboardConfig = {
        ...baseDashboardConfig,
        first_run_incomplete: false,
        agg_in_progress: true,
        caching_in_progress: false
      };

      mockUseStatsDashboard.mockReturnValue({
        dateRange: { start: new Date('2024-01-01'), end: new Date('2024-01-31') },
        isLoading: false,
        isUpdating: false,
        error: null,
        stats: null
      });

      render(
        <StatsDashboardPage
          dashboardConfig={dashboardConfig}
          community={mockCommunity}
          variant="content"
        />
      );

      expect(screen.getByText('No Data Available')).toBeInTheDocument();
      expect(screen.getByText('A calculation operation is currently in progress. Check back again later.')).toBeInTheDocument();
    });

    it('should show caching_in_progress message when caching_in_progress is true', () => {
      const dashboardConfig = {
        ...baseDashboardConfig,
        first_run_incomplete: false,
        agg_in_progress: false,
        caching_in_progress: true
      };

      mockUseStatsDashboard.mockReturnValue({
        dateRange: { start: new Date('2024-01-01'), end: new Date('2024-01-31') },
        isLoading: false,
        isUpdating: false,
        error: null,
        stats: null
      });

      render(
        <StatsDashboardPage
          dashboardConfig={dashboardConfig}
          community={mockCommunity}
          variant="content"
        />
      );

      expect(screen.getByText('No Data Available')).toBeInTheDocument();
      expect(screen.getByText('A calculation operation is currently in progress. Check back again later.')).toBeInTheDocument();
    });

    it('should show default no data message when no flags are set', () => {
      const dashboardConfig = {
        ...baseDashboardConfig,
        first_run_incomplete: false,
        agg_in_progress: false,
        caching_in_progress: false
      };

      mockUseStatsDashboard.mockReturnValue({
        dateRange: { start: new Date('2024-01-01'), end: new Date('2024-01-31') },
        isLoading: false,
        isUpdating: false,
        error: null,
        stats: null
      });

      render(
        <StatsDashboardPage
          dashboardConfig={dashboardConfig}
          community={mockCommunity}
          variant="content"
        />
      );

      expect(screen.getByText('No Data Available')).toBeInTheDocument();
      expect(screen.getByText('No statistics data is available for the selected time period.')).toBeInTheDocument();
    });

    it('should prioritize first_run_incomplete over agg_in_progress', () => {
      const dashboardConfig = {
        ...baseDashboardConfig,
        first_run_incomplete: true,
        agg_in_progress: true,
        caching_in_progress: false
      };

      mockUseStatsDashboard.mockReturnValue({
        dateRange: { start: new Date('2024-01-01'), end: new Date('2024-01-31') },
        isLoading: false,
        isUpdating: false,
        error: null,
        stats: null
      });

      render(
        <StatsDashboardPage
          dashboardConfig={dashboardConfig}
          community={mockCommunity}
          variant="content"
        />
      );

      expect(screen.getByText('Initial calculation of statistics is still in progress. Check back again in a few hours.')).toBeInTheDocument();
      expect(screen.queryByText('A calculation operation is currently in progress. Check back again later.')).not.toBeInTheDocument();
    });

    it('should not show no data message when isLoading is true', () => {
      const dashboardConfig = {
        ...baseDashboardConfig,
        first_run_incomplete: true,
        agg_in_progress: false,
        caching_in_progress: false
      };

      mockUseStatsDashboard.mockReturnValue({
        dateRange: { start: new Date('2024-01-01'), end: new Date('2024-01-31') },
        isLoading: true,
        isUpdating: false,
        error: null,
        stats: null
      });

      render(
        <StatsDashboardPage
          dashboardConfig={dashboardConfig}
          community={mockCommunity}
          variant="content"
        />
      );

      expect(screen.queryByText('No Data Available')).not.toBeInTheDocument();
    });

    it('should not show no data message when isUpdating is true', () => {
      const dashboardConfig = {
        ...baseDashboardConfig,
        first_run_incomplete: true,
        agg_in_progress: false,
        caching_in_progress: false
      };

      mockUseStatsDashboard.mockReturnValue({
        dateRange: { start: new Date('2024-01-01'), end: new Date('2024-01-31') },
        isLoading: false,
        isUpdating: true,
        error: null,
        stats: null
      });

      render(
        <StatsDashboardPage
          dashboardConfig={dashboardConfig}
          community={mockCommunity}
          variant="content"
        />
      );

      expect(screen.queryByText('No Data Available')).not.toBeInTheDocument();
    });

    it('should not show no data message when error is present', () => {
      const dashboardConfig = {
        ...baseDashboardConfig,
        first_run_incomplete: true,
        agg_in_progress: false,
        caching_in_progress: false
      };

      mockUseStatsDashboard.mockReturnValue({
        dateRange: { start: new Date('2024-01-01'), end: new Date('2024-01-31') },
        isLoading: false,
        isUpdating: false,
        error: new Error('Test error'),
        stats: null
      });

      render(
        <StatsDashboardPage
          dashboardConfig={dashboardConfig}
          community={mockCommunity}
          variant="content"
        />
      );

      expect(screen.queryByText('No Data Available')).not.toBeInTheDocument();
    });

    it('should not show no data message when stats are available', () => {
      const dashboardConfig = {
        ...baseDashboardConfig,
        first_run_incomplete: true,
        agg_in_progress: false,
        caching_in_progress: false
      };

      mockUseStatsDashboard.mockReturnValue({
        dateRange: { start: new Date('2024-01-01'), end: new Date('2024-01-31') },
        isLoading: false,
        isUpdating: false,
        error: null,
        stats: [{ year: 2024 }]
      });

      render(
        <StatsDashboardPage
          dashboardConfig={dashboardConfig}
          community={mockCommunity}
          variant="content"
        />
      );

      expect(screen.queryByText('No Data Available')).not.toBeInTheDocument();
    });
  });

  describe('Component Rendering', () => {
    it('should render components from layout configuration', () => {
      mockUseStatsDashboard.mockReturnValue({
        dateRange: { start: new Date('2024-01-01'), end: new Date('2024-01-31') },
        isLoading: false,
        isUpdating: false,
        error: null,
        stats: [{ year: 2024 }]
      });

      render(
        <StatsDashboardPage
          dashboardConfig={baseDashboardConfig}
          community={mockCommunity}
          variant="content"
        />
      );

      expect(screen.getByTestId('single-stat-record-count')).toBeInTheDocument();
    });

    it('should return null when variant does not match any tab', () => {
      const consoleSpy = jest.spyOn(console, 'warn').mockImplementation(() => {});

      mockUseStatsDashboard.mockReturnValue({
        dateRange: { start: new Date('2024-01-01'), end: new Date('2024-01-31') },
        isLoading: false,
        isUpdating: false,
        error: null,
        stats: []
      });

      const { container } = render(
        <StatsDashboardPage
          dashboardConfig={baseDashboardConfig}
          community={mockCommunity}
          variant="nonexistent"
        />
      );

      expect(container.firstChild).toBeNull();
      expect(consoleSpy).toHaveBeenCalledWith('No tab found for variant: nonexistent');

      consoleSpy.mockRestore();
    });
  });

  describe('Aria Labels and Accessibility', () => {
    it('should have proper aria-label for community dashboard', () => {
      mockUseStatsDashboard.mockReturnValue({
        dateRange: { start: new Date('2024-01-01'), end: new Date('2024-01-31') },
        isLoading: false,
        isUpdating: false,
        error: null,
        stats: []
      });

      render(
        <StatsDashboardPage
          dashboardConfig={baseDashboardConfig}
          community={mockCommunity}
          variant="content"
        />
      );

      const grid = screen.getByRole('main');
      expect(grid).toHaveAttribute('aria-label', 'Test Community Statistics Dashboard');
    });

    it('should have proper aria-label for global dashboard', () => {
      const globalConfig = {
        ...baseDashboardConfig,
        dashboard_type: 'global'
      };

      mockUseStatsDashboard.mockReturnValue({
        dateRange: { start: new Date('2024-01-01'), end: new Date('2024-01-31') },
        isLoading: false,
        isUpdating: false,
        error: null,
        stats: []
      });

      render(
        <StatsDashboardPage
          dashboardConfig={globalConfig}
          community={null}
          variant="content"
        />
      );

      const grid = screen.getByRole('main');
      expect(grid).toHaveAttribute('aria-label', 'Global Statistics Dashboard');
    });

    it('should use custom title from dashboardConfig when provided', () => {
      const configWithTitle = {
        ...baseDashboardConfig,
        title: 'Custom Dashboard Title'
      };

      mockUseStatsDashboard.mockReturnValue({
        dateRange: { start: new Date('2024-01-01'), end: new Date('2024-01-31') },
        isLoading: false,
        isUpdating: false,
        error: null,
        stats: []
      });

      render(
        <StatsDashboardPage
          dashboardConfig={configWithTitle}
          community={mockCommunity}
          variant="content"
        />
      );

      const grid = screen.getByRole('main');
      expect(grid).toHaveAttribute('aria-label', 'Custom Dashboard Title');
    });
  });

  describe('Date Range Display', () => {
    it('should display date range phrase and display date range', () => {
      mockUseStatsDashboard.mockReturnValue({
        dateRange: { start: new Date('2024-01-01'), end: new Date('2024-01-31') },
        isLoading: false,
        isUpdating: false,
        error: null,
        stats: []
      });

      render(
        <StatsDashboardPage
          dashboardConfig={baseDashboardConfig}
          community={mockCommunity}
          variant="content"
          pageDateRangePhrase="Last 30 days"
          displayDateRange="Jan 1 - Jan 31, 2024"
        />
      );

      // The Label component should contain both the phrase and the date range
      const label = screen.getByText(/Last 30 days/);
      expect(label).toBeInTheDocument();
      expect(screen.getByText(/Jan 1 - Jan 31, 2024/)).toBeInTheDocument();
    });
  });
});

