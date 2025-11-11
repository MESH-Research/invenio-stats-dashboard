// Part of the Invenio-Stats-Dashboard extension for InvenioRDM
// Copyright (C) 2025 Mesh Research
//
// Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
// it under the terms of the MIT License; see LICENSE file for more details.

import React from 'react';
import { render, screen } from '@testing-library/react';
import { FileTypesMultiDisplayViews } from './FileTypesMultiDisplayViews';

// Mock only the external dependencies
jest.mock('@translations/invenio_stats_dashboard/i18next', () => ({
  i18next: {
    t: (key) => key
  }
}));

jest.mock('../../../context/StatsDashboardContext', () => ({
  useStatsDashboard: jest.fn()
}));

jest.mock('../../../constants', () => ({
  CHART_COLORS: {
    secondary: [
      ['#1f77b4', '#1f77b4'],
      ['#ff7f0e', '#ff7f0e'],
      ['#2ca02c', '#2ca02c'],
      ['#d62728', '#d62728'],
      ['#9467bd', '#9467bd']
    ],
    primary: [
      ['#1f77b4', '#1f77b4'],
      ['#ff7f0e', '#ff7f0e'],
      ['#2ca02c', '#2ca02c'],
      ['#d62728', '#d62728'],
      ['#9467bd', '#9467bd']
    ]
  },
  RECORD_START_BASES: {
    ADDED: "added",
    CREATED: "created",
    PUBLISHED: "published"
  }
}));

describe('FileTypesMultiDisplayViews', () => {
  const mockUseStatsDashboard = require('../../../context/StatsDashboardContext').useStatsDashboard;

  beforeEach(() => {
    mockUseStatsDashboard.mockReturnValue({
      stats: [{
        year: 2024,
        usageSnapshotData: {
          fileTypesByViews: {
            records: [
              {
                id: 'item-1',
                name: 'Item 1',
                year: 2024,
                data: [['01-01', 150]]
              },
              {
                id: 'item-2',
                name: 'Item 2',
                year: 2024,
                data: [['01-01', 75]]
              }
            ]
          }
        }
      }],
      dateRange: { start: new Date('2024-01-01'), end: new Date('2024-01-31') },
      isLoading: false
    });
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('Component rendering', () => {
    it('should render with default props (list view)', () => {
      render(<FileTypesMultiDisplayViews default_view="list" />);
      const statsDisplay = screen.getByRole('region');
      expect(statsDisplay).toBeInTheDocument();
    });

    it('should render with custom title and headers', () => {
      render(<FileTypesMultiDisplayViews title="Custom Title" headers={["Custom Header", "Custom Count"]} default_view="list" />);
      const statsDisplay = screen.getByRole('region');
      expect(statsDisplay).toBeInTheDocument();
      expect(statsDisplay).toHaveAttribute('aria-label', 'Custom Title');
    });

    it('should handle empty data', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: [{
          year: 2024,
          usageSnapshotData: {}
        }],
        dateRange: { start: new Date('2024-01-01'), end: new Date('2024-01-31') },
        isLoading: false
      });
      render(<FileTypesMultiDisplayViews default_view="list" />);
      const statsDisplay = screen.getByRole('region');
      expect(statsDisplay).toBeInTheDocument();
    });

    it('should handle missing data', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: [{
          year: 2024,
          usageSnapshotData: {}
        }],
        dateRange: { start: new Date('2024-01-01'), end: new Date('2024-01-31') },
        isLoading: false
      });
      render(<FileTypesMultiDisplayViews default_view="list" />);
      const statsDisplay = screen.getByRole('region');
      expect(statsDisplay).toBeInTheDocument();
    });
  });
});
