/**
 * Part of Invenio-Stats-Dashboard
 * Copyright (C) 2025 Mesh Research
 *
 * Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
 * it under the terms of the MIT License; see LICENSE file for more details.
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { GlobalStatsDashboardLayout } from './GlobalStatsDashboardLayout';

// Mock dependencies
jest.mock('./StatsDashboardLayout', () => ({
  StatsDashboardLayout: ({ dashboardType }) => (
    <div data-testid="stats-dashboard-layout">{dashboardType}</div>
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

describe('GlobalStatsDashboardLayout', () => {
  const mockStats = {
    recordDeltaDataCreated: {
      global: {
        records: [],
      },
    },
  };

  describe('When global dashboard is enabled', () => {
    it('should render StatsDashboardLayout', () => {
      const dashboardConfig = {
        dashboard_enabled: true,
        disabled_message: 'Global dashboard is disabled',
        layout: {
          tabs: [],
        },
      };

      render(
        <GlobalStatsDashboardLayout
          dashboardConfig={dashboardConfig}
          stats={mockStats}
        />
      );

      expect(screen.getByTestId('stats-dashboard-layout')).toBeInTheDocument();
      expect(
        screen.queryByTestId('stats-dashboard-disabled-message')
      ).not.toBeInTheDocument();
    });
  });

  describe('When global dashboard is disabled', () => {
    it('should render StatsDashboardDisabledMessage with correct message', () => {
      const disabledMessage = 'The global statistics dashboard must be enabled by the administrators.';
      const dashboardConfig = {
        dashboard_enabled: false,
        disabled_message: disabledMessage,
        layout: {
          tabs: [],
        },
      };

      render(
        <GlobalStatsDashboardLayout
          dashboardConfig={dashboardConfig}
          stats={mockStats}
        />
      );

      expect(
        screen.getByTestId('stats-dashboard-disabled-message')
      ).toBeInTheDocument();
      expect(screen.getByTestId('disabled-message')).toHaveTextContent(
        disabledMessage
      );
      expect(screen.getByTestId('disabled-dashboard-type')).toHaveTextContent(
        'global'
      );
      expect(
        screen.queryByTestId('stats-dashboard-layout')
      ).not.toBeInTheDocument();
    });

    it('should pass correct dashboardType to StatsDashboardDisabledMessage', () => {
      const dashboardConfig = {
        dashboard_enabled: false,
        disabled_message: 'Dashboard disabled',
        layout: {
          tabs: [],
        },
      };

      render(
        <GlobalStatsDashboardLayout
          dashboardConfig={dashboardConfig}
          stats={mockStats}
        />
      );

      const disabledMessageElement = screen.getByTestId('disabled-dashboard-type');
      expect(disabledMessageElement).toHaveTextContent('global');
    });
  });
});

