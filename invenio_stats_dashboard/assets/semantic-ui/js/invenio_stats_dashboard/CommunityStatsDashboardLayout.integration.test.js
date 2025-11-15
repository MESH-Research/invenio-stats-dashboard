/**
 * Part of Invenio-Stats-Dashboard
 * Copyright (C) 2025 Mesh Research
 *
 * Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
 * it under the terms of the MIT License; see LICENSE file for more details.
 *
 * Integration tests for CommunityStatsDashboardLayout using real StatsDashboardDisabledMessage
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { CommunityStatsDashboardLayout } from './CommunityStatsDashboardLayout';

// Mock only StatsDashboardLayout, not StatsDashboardDisabledMessage
jest.mock('./StatsDashboardLayout', () => ({
  StatsDashboardLayout: ({ dashboardType, community }) => (
    <div data-testid="stats-dashboard-layout">
      <div data-testid="dashboard-type">{dashboardType}</div>
      <div data-testid="community-id">{community?.id}</div>
    </div>
  ),
}));

// Mock i18next
jest.mock('@translations/invenio_stats_dashboard/i18next', () => ({
  i18next: {
    t: jest.fn((key) => key),
  },
}));

describe('CommunityStatsDashboardLayout Integration Tests', () => {
  const mockCommunity = {
    id: 'test-community-id',
    slug: 'test-community',
    metadata: {
      title: 'Test Community',
    },
    custom_fields: {},
  };

  const mockStats = {
    recordDeltaDataCreated: {
      global: {
        records: [],
      },
    },
  };

  describe('Integration with real StatsDashboardDisabledMessage', () => {
    it('should render real StatsDashboardDisabledMessage when global community dashboard is disabled', () => {
      const community = {
        ...mockCommunity,
        custom_fields: {
          'stats:dashboard_enabled': false,
        },
      };

      const globalDisabledMessage =
        'The global statistics dashboard must be enabled by the administrators.';
      const dashboardConfig = {
        dashboard_enabled_communities: false,
        disabled_message: 'Community dashboard is disabled',
        disabled_message_global: globalDisabledMessage,
        layout: {
          tabs: [],
        },
      };

      const { container } = render(
        <CommunityStatsDashboardLayout
          community={community}
          dashboardConfig={dashboardConfig}
          stats={mockStats}
        />
      );

      // Verify the real component is rendered with semantic-ui classes
      expect(container.querySelector('.ui.container')).toBeInTheDocument();
      expect(container.querySelector('.ui.info.message')).toBeInTheDocument();
      expect(container.querySelector('#community-stats-dashboard')).toBeInTheDocument();
      
      // Verify the global disabled message is shown
      expect(screen.getByText(globalDisabledMessage)).toBeInTheDocument();
      
      // Verify correct classes are applied for community
      const containerElement = container.querySelector('.ui.container');
      expect(containerElement).toHaveClass('community-stats-dashboard');
      expect(containerElement).toHaveClass('rel-m-2');
      expect(containerElement).toHaveClass('stats-dashboard-container');
      
      // Verify StatsDashboardLayout is not rendered
      expect(
        screen.queryByTestId('stats-dashboard-layout')
      ).not.toBeInTheDocument();
    });

    it('should render real StatsDashboardDisabledMessage when community dashboard is disabled (opt-in)', () => {
      const community = {
        ...mockCommunity,
        custom_fields: {
          'stats:dashboard_enabled': false,
        },
      };

      const communityDisabledMessage =
        'Community managers and administrators can enable the dashboard from the community settings page';
      const dashboardConfig = {
        dashboard_enabled_communities: true,
        disabled_message: communityDisabledMessage,
        disabled_message_global:
          'The global statistics dashboard must be enabled by the administrators.',
        layout: {
          tabs: [],
        },
      };

      const { container } = render(
        <CommunityStatsDashboardLayout
          community={community}
          dashboardConfig={dashboardConfig}
          stats={mockStats}
        />
      );

      // Verify the real component is rendered
      expect(container.querySelector('.ui.container')).toBeInTheDocument();
      expect(container.querySelector('.ui.info.message')).toBeInTheDocument();
      expect(container.querySelector('#community-stats-dashboard')).toBeInTheDocument();
      
      // Verify the community disabled message is shown (not the global one)
      expect(screen.getByText(communityDisabledMessage)).toBeInTheDocument();
      expect(screen.queryByText('The global statistics dashboard must be enabled by the administrators.')).not.toBeInTheDocument();
      
      // Verify correct classes are applied
      const containerElement = container.querySelector('.ui.container');
      expect(containerElement).toHaveClass('community-stats-dashboard');
      expect(containerElement).toHaveClass('rel-m-2');
    });

    it('should pass correct props to real StatsDashboardDisabledMessage', () => {
      const community = {
        ...mockCommunity,
        custom_fields: {
          'stats:dashboard_enabled': false,
        },
      };

      const dashboardConfig = {
        dashboard_enabled_communities: true,
        disabled_message: 'Enable dashboard from settings',
        disabled_message_global: 'Global dashboard disabled',
        layout: {
          tabs: [],
        },
      };

      const { container } = render(
        <CommunityStatsDashboardLayout
          community={community}
          dashboardConfig={dashboardConfig}
          stats={mockStats}
        />
      );

      // Verify the component receives correct dashboardType
      const containerElement = container.querySelector('#community-stats-dashboard');
      expect(containerElement).toBeInTheDocument();
      expect(containerElement).toHaveClass('community-stats-dashboard');
      
      // Verify the correct message is passed (community message, not global)
      expect(screen.getByText('Enable dashboard from settings')).toBeInTheDocument();
      expect(screen.queryByText('Global dashboard disabled')).not.toBeInTheDocument();
      
      // Verify the info message type is applied
      const messageElement = container.querySelector('.ui.info.message');
      expect(messageElement).toBeInTheDocument();
    });
  });
});

