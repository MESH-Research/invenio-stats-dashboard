/**
 * Part of Invenio-Stats-Dashboard
 * Copyright (C) 2025 Mesh Research
 *
 * Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
 * it under the terms of the MIT License; see LICENSE file for more details.
 *
 * Integration tests for GlobalStatsDashboardLayout using real StatsDashboardDisabledMessage
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { GlobalStatsDashboardLayout } from './GlobalStatsDashboardLayout';

// Mock only StatsDashboardLayout, not StatsDashboardDisabledMessage
jest.mock('./StatsDashboardLayout', () => ({
  StatsDashboardLayout: ({ dashboardType }) => (
    <div data-testid="stats-dashboard-layout">{dashboardType}</div>
  ),
}));

// Mock i18next
jest.mock('@translations/invenio_stats_dashboard/i18next', () => ({
  i18next: {
    t: jest.fn((key) => key),
  },
}));

describe('GlobalStatsDashboardLayout Integration Tests', () => {
  const mockStats = {
    recordDeltaDataCreated: {
      global: {
        records: [],
      },
    },
  };

  describe('Integration with real StatsDashboardDisabledMessage', () => {
    it('should render real StatsDashboardDisabledMessage when dashboard is disabled', () => {
      const disabledMessage = 'The global statistics dashboard must be enabled by the administrators.';
      const dashboardConfig = {
        dashboard_enabled: false,
        disabled_message: disabledMessage,
        layout: {
          tabs: [],
        },
      };

      const { container } = render(
        <GlobalStatsDashboardLayout
          dashboardConfig={dashboardConfig}
          stats={mockStats}
        />
      );

      // Verify the real component is rendered with semantic-ui classes
      expect(container.querySelector('.ui.container')).toBeInTheDocument();
      expect(container.querySelector('.ui.info.message')).toBeInTheDocument();
      expect(container.querySelector('#global-stats-dashboard')).toBeInTheDocument();
      
      // Verify the message content
      expect(screen.getByText(disabledMessage)).toBeInTheDocument();
      
      // Verify correct classes are applied
      const containerElement = container.querySelector('.ui.container');
      expect(containerElement).toHaveClass('global-stats-dashboard');
      expect(containerElement).toHaveClass('rel-mb-2');
      expect(containerElement).toHaveClass('stats-dashboard-container');
      
      // Verify StatsDashboardLayout is not rendered
      expect(
        screen.queryByTestId('stats-dashboard-layout')
      ).not.toBeInTheDocument();
    });

    it('should pass correct props to real StatsDashboardDisabledMessage', () => {
      const disabledMessage = 'Global dashboard is disabled.';
      const dashboardConfig = {
        dashboard_enabled: false,
        disabled_message: disabledMessage,
        layout: {
          tabs: [],
        },
      };

      const { container } = render(
        <GlobalStatsDashboardLayout
          dashboardConfig={dashboardConfig}
          stats={mockStats}
        />
      );

      // Verify the component receives correct dashboardType
      const containerElement = container.querySelector('#global-stats-dashboard');
      expect(containerElement).toBeInTheDocument();
      expect(containerElement).toHaveClass('global-stats-dashboard');
      
      // Verify the message is passed correctly
      expect(screen.getByText(disabledMessage)).toBeInTheDocument();
      
      // Verify the info message type is applied
      const messageElement = container.querySelector('.ui.info.message');
      expect(messageElement).toBeInTheDocument();
    });
  });
});

