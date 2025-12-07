/**
 * Part of Invenio-Stats-Dashboard
 * Copyright (C) 2025 Mesh Research
 *
 * Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
 * it under the terms of the MIT License; see LICENSE file for more details.
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { CommunityStatsDashboardLayout } from './CommunityStatsDashboardLayout';

// Mock dependencies
jest.mock('./StatsDashboardLayout', () => ({
  StatsDashboardLayout: ({ dashboardType, community }) => (
    <div data-testid="stats-dashboard-layout">
      <div data-testid="dashboard-type">{dashboardType}</div>
      <div data-testid="community-id">{community?.id}</div>
    </div>
  ),
}));

jest.mock('./StatsDashboardDisabledMessage', () => ({
  StatsDashboardDisabledMessage: ({ msg, dashboardType }) => (
    <div data-testid="stats-dashboard-disabled-message">
      <div data-testid="disabled-message">{msg}</div>
      <div data-testid="disabled-dashboard-type">{dashboardType}</div>
    </div>
  ),
}));

jest.mock('@translations/invenio_stats_dashboard/i18next', () => ({
  i18next: {
    t: jest.fn((key) => key),
  },
}));

describe('CommunityStatsDashboardLayout', () => {
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

  describe('When community dashboard is enabled', () => {
    it('should render StatsDashboardLayout when dashboard_enabled is true', () => {
      const community = {
        ...mockCommunity,
        custom_fields: {
          'stats:dashboard_enabled': true,
        },
      };

      const dashboardConfig = {
        dashboard_enabled_communities: true,
        dashboard_enabled_global: true,
        disabled_message: 'Community dashboard is disabled',
        disabled_message_global: 'Global community dashboard is disabled',
        layout: {
          tabs: [],
        },
      };

      render(
        <CommunityStatsDashboardLayout
          community={community}
          dashboardConfig={dashboardConfig}
          stats={mockStats}
        />
      );

      expect(screen.getByTestId('stats-dashboard-layout')).toBeInTheDocument();
      expect(screen.getByTestId('community-id')).toHaveTextContent(
        'test-community-id'
      );
      expect(
        screen.queryByTestId('stats-dashboard-disabled-message')
      ).not.toBeInTheDocument();
    });
  });

  describe('When global community dashboard is disabled', () => {
    it('should render StatsDashboardDisabledMessage with global disabled message', () => {
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
        dashboard_enabled_global: false, // Global feature disabled
        disabled_message: 'Community dashboard is disabled',
        disabled_message_global: globalDisabledMessage,
        layout: {
          tabs: [],
        },
      };

      render(
        <CommunityStatsDashboardLayout
          community={community}
          dashboardConfig={dashboardConfig}
          stats={mockStats}
        />
      );

      expect(
        screen.getByTestId('stats-dashboard-disabled-message')
      ).toBeInTheDocument();
      expect(screen.getByTestId('disabled-message')).toHaveTextContent(
        globalDisabledMessage
      );
      expect(screen.getByTestId('disabled-dashboard-type')).toHaveTextContent(
        'community'
      );
      expect(
        screen.queryByTestId('stats-dashboard-layout')
      ).not.toBeInTheDocument();
    });
  });

  describe('When community dashboard is disabled (opt-in scenario)', () => {
    it('should render StatsDashboardDisabledMessage when dashboard_enabled_communities is true but community dashboard is disabled', () => {
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
        dashboard_enabled_global: true, // Both global features enabled
        disabled_message: communityDisabledMessage,
        disabled_message_global:
          'The global statistics dashboard must be enabled by the administrators.',
        layout: {
          tabs: [],
        },
      };

      render(
        <CommunityStatsDashboardLayout
          community={community}
          dashboardConfig={dashboardConfig}
          stats={mockStats}
        />
      );

      expect(
        screen.getByTestId('stats-dashboard-disabled-message')
      ).toBeInTheDocument();
      expect(screen.getByTestId('disabled-message')).toHaveTextContent(
        communityDisabledMessage
      );
      expect(screen.getByTestId('disabled-dashboard-type')).toHaveTextContent(
        'community'
      );
      expect(
        screen.queryByTestId('stats-dashboard-layout')
      ).not.toBeInTheDocument();
    });

    it('should use community disabled message when dashboard_enabled_communities is true', () => {
      const community = {
        ...mockCommunity,
        custom_fields: {
          'stats:dashboard_enabled': false,
        },
      };

      const communityDisabledMessage = 'Enable dashboard from settings';
      const globalDisabledMessage = 'Global dashboard disabled';
      const dashboardConfig = {
        dashboard_enabled_communities: true,
        dashboard_enabled_global: true, // Both global features enabled
        disabled_message: communityDisabledMessage,
        disabled_message_global: globalDisabledMessage,
        layout: {
          tabs: [],
        },
      };

      render(
        <CommunityStatsDashboardLayout
          community={community}
          dashboardConfig={dashboardConfig}
          stats={mockStats}
        />
      );

      // Should use disabled_message (community message), not disabled_message_global
      expect(screen.getByTestId('disabled-message')).toHaveTextContent(
        communityDisabledMessage
      );
      expect(screen.getByTestId('disabled-message')).not.toHaveTextContent(
        globalDisabledMessage
      );
    });

    it('should use global disabled message when dashboard_enabled_communities is true but dashboard_enabled_global is false', () => {
      const community = {
        ...mockCommunity,
        custom_fields: {
          'stats:dashboard_enabled': false,
        },
      };

      const communityDisabledMessage = 'Enable dashboard from settings';
      const globalDisabledMessage = 'Global dashboard disabled';
      const dashboardConfig = {
        dashboard_enabled_communities: true,
        dashboard_enabled_global: false, // Global dashboard disabled
        disabled_message: communityDisabledMessage,
        disabled_message_global: globalDisabledMessage,
        layout: {
          tabs: [],
        },
      };

      render(
        <CommunityStatsDashboardLayout
          community={community}
          dashboardConfig={dashboardConfig}
          stats={mockStats}
        />
      );

      // Should use disabled_message_global when global dashboard is disabled
      expect(screen.getByTestId('disabled-message')).toHaveTextContent(
        globalDisabledMessage
      );
      expect(screen.getByTestId('disabled-message')).not.toHaveTextContent(
        communityDisabledMessage
      );
    });
  });

  describe('Edge cases', () => {
    it('should handle missing custom_fields gracefully', () => {
      const community = {
        ...mockCommunity,
        custom_fields: {},
      };

      const dashboardConfig = {
        dashboard_enabled_communities: true,
        dashboard_enabled_global: true,
        disabled_message: 'Community dashboard is disabled',
        disabled_message_global: 'Global community dashboard is disabled',
        layout: {
          tabs: [],
        },
      };

      render(
        <CommunityStatsDashboardLayout
          community={community}
          dashboardConfig={dashboardConfig}
          stats={mockStats}
        />
      );

      // When custom_fields is empty, dashboardEnabled will be falsy
      expect(
        screen.getByTestId('stats-dashboard-disabled-message')
      ).toBeInTheDocument();
    });

    it('should handle null dashboard_enabled value', () => {
      const community = {
        ...mockCommunity,
        custom_fields: {
          'stats:dashboard_enabled': null,
        },
      };

      const dashboardConfig = {
        dashboard_enabled_communities: true,
        dashboard_enabled_global: true,
        disabled_message: 'Community dashboard is disabled',
        disabled_message_global: 'Global community dashboard is disabled',
        layout: {
          tabs: [],
        },
      };

      render(
        <CommunityStatsDashboardLayout
          community={community}
          dashboardConfig={dashboardConfig}
          stats={mockStats}
        />
      );

      // null should be treated as falsy
      expect(
        screen.getByTestId('stats-dashboard-disabled-message')
      ).toBeInTheDocument();
    });

    it('should handle empty string dashboard_enabled value', () => {
      const community = {
        ...mockCommunity,
        custom_fields: {
          'stats:dashboard_enabled': '',
        },
      };

      const dashboardConfig = {
        dashboard_enabled_communities: true,
        dashboard_enabled_global: true,
        disabled_message: 'Community dashboard is disabled',
        disabled_message_global: 'Global community dashboard is disabled',
        layout: {
          tabs: [],
        },
      };

      render(
        <CommunityStatsDashboardLayout
          community={community}
          dashboardConfig={dashboardConfig}
          stats={mockStats}
        />
      );

      // Empty string should be treated as falsy
      expect(
        screen.getByTestId('stats-dashboard-disabled-message')
      ).toBeInTheDocument();
    });
  });
});
