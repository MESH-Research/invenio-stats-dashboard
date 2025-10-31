// Part of the Invenio-Stats-Dashboard extension for InvenioRDM
// Copyright (C) 2025 Mesh Research
//
// Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
// it under the terms of the MIT License; see LICENSE file for more details.

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { StatsChart } from './StatsChart';
import { useStatsDashboard } from '../../context/StatsDashboardContext';
import { clearSubcountKeyMappingCache } from '../../constants';

// Mock the dependencies
jest.mock('../../context/StatsDashboardContext');
jest.mock('echarts-for-react', () => {
  return function MockReactECharts({ option, ...props }) {
    return (
      <div data-testid="mock-echarts" {...props}>
        <div data-testid="chart-option" data-option={JSON.stringify(option)} />
      </div>
    );
  };
});

const mockUseStatsDashboard = useStatsDashboard;

describe('StatsChart FilterSelector', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    clearSubcountKeyMappingCache();
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  const mockData = [{
    year: 2024,
    global: {
      records: [
        {
          id: 'records',
          name: 'Records',
          data: [
            { value: [new Date('2024-01-01T00:00:00.000Z'), 10] },
            { value: [new Date('2024-01-02T00:00:00.000Z'), 20] }
          ]
        }
      ]
    },
    resourceTypes: {
      records: [
        {
          id: 'resourceTypes',
          name: 'Resource Types',
          data: [
            { value: [new Date('2024-01-01T00:00:00.000Z'), 5] },
            { value: [new Date('2024-01-02T00:00:00.000Z'), 15] }
          ]
        }
      ]
    },
    subjects: {
      records: [
        {
          id: 'subjects',
          name: 'Subjects',
          data: [
            { value: [new Date('2024-01-01T00:00:00.000Z'), 3] },
            { value: [new Date('2024-01-02T00:00:00.000Z'), 7] }
          ]
        }
      ]
    },
    languages: {
      records: [
        {
          id: 'languages',
          name: 'Languages',
          data: [
            { value: [new Date('2024-01-01T00:00:00.000Z'), 2] },
            { value: [new Date('2024-01-02T00:00:00.000Z'), 8] }
          ]
        }
      ]
    }
  }];

  const mockSeriesSelectorOptions = [
    { value: 'records', text: 'Records', valueType: 'number' }
  ];

  describe('FilterSelector with global subcounts config', () => {
    beforeEach(() => {
      mockUseStatsDashboard.mockReturnValue({
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') },
        granularity: 'day',
        isLoading: false,
        ui_subcounts: {
          'by_resource_types': {},
          'by_subjects': {}
        }
      });
    });

    it('should only show allowed breakdown options in filter popup', () => {
      render(
        <StatsChart
          data={mockData}
          seriesSelectorOptions={mockSeriesSelectorOptions}
          title="Test Chart"
        />
      );

      // Click the filter button to open the popup
      const filterButton = screen.getByLabelText('Stats Chart Filter');
      fireEvent.click(filterButton);

      // Check that only allowed breakdown options are shown
      expect(screen.getByText('Top Work Types')).toBeInTheDocument(); // resourceTypes
      expect(screen.getByText('Top Subjects')).toBeInTheDocument(); // subjects

      // Check that disallowed options are not shown
      expect(screen.queryByText('Top Languages')).not.toBeInTheDocument(); // languages
    });
  });

  describe('FilterSelector with component-specific display_subcounts override', () => {
    beforeEach(() => {
      mockUseStatsDashboard.mockReturnValue({
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') },
        granularity: 'day',
        isLoading: false,
        ui_subcounts: {
          'by_resource_types': {},
          'by_subjects': {},
          'by_languages': {}
        }
      });
    });

    it('should use component-specific display_subcounts override', () => {
      render(
        <StatsChart
          data={mockData}
          seriesSelectorOptions={mockSeriesSelectorOptions}
          title="Test Chart"
          display_subcounts={{
            'by_languages': {}
          }}
        />
      );

      // Click the filter button to open the popup
      const filterButton = screen.getByLabelText('Stats Chart Filter');
      fireEvent.click(filterButton);

      // Check that only the component-specific allowed option is shown
      expect(screen.getByText('Top Languages')).toBeInTheDocument(); // languages

      // Check that global config options are not shown
      expect(screen.queryByText('Top Work Types')).not.toBeInTheDocument(); // resourceTypes
      expect(screen.queryByText('Top Subjects')).not.toBeInTheDocument(); // subjects
    });
  });

  describe('FilterSelector with no subcounts config', () => {
    beforeEach(() => {
      mockUseStatsDashboard.mockReturnValue({
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') },
        granularity: 'day',
        isLoading: false,
        ui_subcounts: {}
      });
    });

    it('should show all available breakdown options when no config is provided', () => {
      render(
        <StatsChart
          data={mockData}
          seriesSelectorOptions={mockSeriesSelectorOptions}
          title="Test Chart"
        />
      );

      // Click the filter button to open the popup
      const filterButton = screen.getByLabelText('Stats Chart Filter');
      fireEvent.click(filterButton);

      // Check that all available breakdown options are shown
      expect(screen.getByText('Top Work Types')).toBeInTheDocument(); // resourceTypes
      expect(screen.getByText('Top Subjects')).toBeInTheDocument(); // subjects
      expect(screen.getByText('Top Languages')).toBeInTheDocument(); // languages
    });
  });

  describe('FilterSelector with empty subcounts in data', () => {
    beforeEach(() => {
      mockUseStatsDashboard.mockReturnValue({
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') },
        granularity: 'day',
        isLoading: false,
        ui_subcounts: {
          'by_resource_types': {},
          'by_subjects': {},
          'by_funders': {}
        }
      });
    });

    it('should filter out empty subcounts from breakdown options', () => {
      const dataWithEmptySubcounts = [{
        year: 2024,
        global: {
          records: [
            {
              id: 'records',
              name: 'Records',
              data: [
                { value: [new Date('2024-01-01T00:00:00.000Z'), 10] },
                { value: [new Date('2024-01-02T00:00:00.000Z'), 20] }
              ]
            }
          ]
        },
        resourceTypes: {
          records: [
            {
              id: 'article',
              name: 'Article',
              data: [
                { value: [new Date('2024-01-01T00:00:00.000Z'), 5] }
              ]
            }
          ]
        },
        subjects: {
          records: [
            {
              id: 'science',
              name: 'Science',
              data: [
                { value: [new Date('2024-01-01T00:00:00.000Z'), 3] }
              ]
            }
          ]
        },
        // Empty subcount with empty metric arrays (new structure)
        funders: {
          records: [],
          parents: [],
          fileCount: [],
          dataVolume: []
        }
      }];

      render(
        <StatsChart
          data={dataWithEmptySubcounts}
          seriesSelectorOptions={mockSeriesSelectorOptions}
          title="Test Chart"
        />
      );

      // Click the filter button to open the popup
      const filterButton = screen.getByLabelText('Stats Chart Filter');
      fireEvent.click(filterButton);

      // Check that only subcounts with data are shown
      expect(screen.getByText('Top Work Types')).toBeInTheDocument(); // resourceTypes has data
      expect(screen.getByText('Top Subjects')).toBeInTheDocument(); // subjects has data
      // Empty funders subcount should not appear
      expect(screen.queryByText('Top Funders')).not.toBeInTheDocument();
    });
  });
});
