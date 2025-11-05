// Part of the Invenio-Stats-Dashboard extension for InvenioRDM
// Copyright (C) 2025 Mesh Research
//
// Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
// it under the terms of the MIT License; see LICENSE file for more details.

import React from 'react';
import { render, screen, within } from '@testing-library/react';
import { FileTypesMultiDisplay } from './FileTypesMultiDisplay';
import { filterSeriesArrayByDate } from '../../../utils';
import { transformMultiDisplayData, assembleMultiDisplayRows } from '../../../utils/multiDisplayHelpers';

// Mock only the external dependencies
jest.mock('@translations/invenio_stats_dashboard/i18next', () => ({
  i18next: {
    t: (key) => key
  }
}));

// Mock the StatsDashboard context
const mockUseStatsDashboard = jest.fn();
jest.mock('../../../context/StatsDashboardContext', () => ({
  useStatsDashboard: () => mockUseStatsDashboard()
}));

describe('FileTypesMultiDisplay', () => {
  beforeEach(() => {
    mockUseStatsDashboard.mockReturnValue({
      stats: [{
        year: 2024,
        recordSnapshotDataAdded: {
          fileTypes: {
            records: [
              {
                id: 'pdf',
                name: 'PDF',
                data: [{ value: [new Date('2024-01-01'), 150] }]
              },
              {
                id: 'csv',
                name: 'CSV',
                data: [{ value: [new Date('2024-01-01'), 75] }]
              },
              {
                id: 'txt',
                name: 'Text',
                data: [{ value: [new Date('2024-01-01'), 25] }]
              }
            ]
          }
        }
      }],
      recordStartBasis: 'added',
      dateRange: { start: '2024-01-01', end: '2024-01-31' },
      isLoading: false
    });
  });

  describe('transformMultiDisplayData (helper function)', () => {
    it('should return empty data when input is null', () => {
      const result = transformMultiDisplayData(null, 10, 'files.entries.ext');

      expect(result).toEqual({
        transformedData: [],
        otherData: null,
        originalOtherData: null,
        totalCount: 0,
        otherPercentage: 0
      });
    });

    it('should return empty data when input is undefined', () => {
      const result = transformMultiDisplayData(undefined, 10, 'files.entries.ext');

      expect(result).toEqual({
        transformedData: [],
        otherData: null,
        originalOtherData: null,
        totalCount: 0,
        otherPercentage: 0
      });
    });

    it('should return empty data when input is not an array', () => {
      const result = transformMultiDisplayData('not an array', 10, 'files.entries.ext');

      expect(result).toEqual({
        transformedData: [],
        otherData: null,
        originalOtherData: null,
        totalCount: 0,
        otherPercentage: 0
      });
    });

    it('should transform valid file types data correctly', () => {
      const mockData = [
        {
          id: 'pdf',
          name: 'PDF',
          data: [{ value: [new Date('2024-01-01'), 150] }]
        },
        {
          id: 'csv',
          name: 'CSV',
          data: [{ value: [new Date('2024-01-01'), 75] }]
        },
        {
          id: 'txt',
          name: 'Text',
          data: [{ value: [new Date('2024-01-01'), 25] }]
        }
      ];

      const result = transformMultiDisplayData(mockData, 2, 'files.entries.ext');

      expect(result.totalCount).toBe(250);
      expect(result.transformedData).toHaveLength(2);
      expect(result.otherData).toBeTruthy();
      expect(result.otherData.name).toBe('Other');
      expect(result.otherData.value).toBe(25);
      expect(result.otherData.percentage).toBe(10); // 25/250 * 100
    });

    it('should handle data with missing or invalid values', () => {
      const mockData = [
        {
          id: 'pdf',
          name: 'PDF',
          data: [{ value: [new Date('2024-01-01'), 100] }]
        },
        {
          id: 'csv',
          name: 'CSV',
          data: [{ value: [new Date('2024-01-01'), 0] }] // Zero value
        },
        {
          id: 'txt',
          name: 'Text',
          data: [{ value: [new Date('2024-01-01'), 50] }]
        }
      ];

      const result = transformMultiDisplayData(mockData, 10, 'files.entries.ext');

      expect(result.totalCount).toBe(150);
      expect(result.transformedData).toHaveLength(2); // Zero value items are filtered out
      expect(result.transformedData[0].value).toBe(100); // PDF
      expect(result.transformedData[1].value).toBe(50); // Text
    });

    it('should calculate percentages correctly', () => {
      const mockData = [
        {
          id: 'pdf',
          name: 'PDF',
          data: [{ value: [new Date('2024-01-01'), 100] }]
        },
        {
          id: 'csv',
          name: 'CSV',
          data: [{ value: [new Date('2024-01-01'), 50] }]
        }
      ];

      const result = transformMultiDisplayData(mockData, 10, 'files.entries.ext');

      expect(result.transformedData[0].percentage).toBe(67); // 100/150 * 100
      expect(result.transformedData[1].percentage).toBe(33); // 50/150 * 100
    });

    it('should create correct links for each file type', () => {
      const mockData = [
        {
          id: 'pdf',
          name: 'PDF',
          data: [{ value: [new Date('2024-01-01'), 100] }]
        }
      ];

      const result = transformMultiDisplayData(mockData, 10, 'files.entries.ext');

      expect(result.transformedData[0].link).toContain('files.entries.ext:"pdf"');
    });

    it('should create transformed data with all expected properties', () => {
      const mockData = [
        {
          id: 'pdf',
          name: 'PDF',
          data: [{ value: [new Date('2024-01-01'), 100] }]
        }
      ];

      const result = transformMultiDisplayData(mockData, 10, 'files.entries.ext');

      expect(result.transformedData[0]).toHaveProperty('id');
      expect(result.transformedData[0]).toHaveProperty('name');
      expect(result.transformedData[0]).toHaveProperty('value');
      expect(result.transformedData[0]).toHaveProperty('percentage');
      expect(result.transformedData[0]).toHaveProperty('link');
      expect(result.transformedData[0]).toHaveProperty('itemStyle');
    });

    it('should create otherData with all expected properties when there are additional items', () => {
      const mockData = [
        { id: 'pdf', name: 'PDF', data: [{ value: [new Date('2024-01-01'), 100] }] },
        { id: 'csv', name: 'CSV', data: [{ value: [new Date('2024-01-01'), 50] }] },
        { id: 'txt', name: 'Text', data: [{ value: [new Date('2024-01-01'), 25] }] }
      ];

      const result = transformMultiDisplayData(mockData, 2, 'files.entries.ext');

      expect(result.otherData).toHaveProperty('id');
      expect(result.otherData).toHaveProperty('name');
      expect(result.otherData).toHaveProperty('value');
      expect(result.otherData).toHaveProperty('percentage');
      expect(result.otherData).toHaveProperty('itemStyle');
    });

    it('should return null for otherData when there are no additional items', () => {
      const mockData = [
        { id: 'pdf', name: 'PDF', data: [{ value: [new Date('2024-01-01'), 100] }] },
        { id: 'csv', name: 'CSV', data: [{ value: [new Date('2024-01-01'), 50] }] }
      ];

      const result = transformMultiDisplayData(mockData, 10, 'files.entries.ext');

      expect(result.otherData).toBeNull();
    });

    it('should handle zero total count', () => {
      const mockData = [
        { id: 'pdf', name: 'PDF', data: [{ value: [new Date('2024-01-01'), 0] }] },
        { id: 'csv', name: 'CSV', data: [{ value: [new Date('2024-01-01'), 0] }] }
      ];

      const result = transformMultiDisplayData(mockData, 10, 'files.entries.ext');

      expect(result.totalCount).toBe(0);
      expect(result.transformedData).toHaveLength(0); // Zero value items are filtered out
    });
  });

  describe('assembleMultiDisplayRows (helper function)', () => {
    it('should assemble rows correctly with transformed data only', () => {
      const transformedData = [
        { id: 'pdf', name: 'PDF', value: 100, percentage: 67, link: '/search?q=files.entries.ext:pdf' },
        { id: 'csv', name: 'CSV', value: 50, percentage: 33, link: '/search?q=files.entries.ext:csv' }
      ];

      const rows = assembleMultiDisplayRows(transformedData, null);

      expect(rows).toHaveLength(2);
      expect(rows[0][0]).toBe(null);
      expect(rows[0][1].type).toBe('a');
      expect(rows[0][1].props.href).toBe('/search?q=files.entries.ext:pdf');
      expect(rows[0][1].props.children).toBe('PDF');
      expect(rows[0][2]).toBe('100 (67%)');
    });

    it('should include other data when provided', () => {
      const transformedData = [
        { id: 'pdf', name: 'PDF', value: 100, percentage: 67, link: '/search?q=files.entries.ext:pdf' }
      ];
      const otherData = { id: 'other', name: 'Other', value: 25, percentage: 17 };

      const rows = assembleMultiDisplayRows(transformedData, otherData);

      expect(rows).toHaveLength(2);
      expect(rows[1][0]).toBe(null);
      expect(rows[1][1]).toBe('Other');
      expect(rows[1][2]).toBe('25 (17%)');
    });

    it('should handle data without links', () => {
      const transformedData = [
        { id: 'pdf', name: 'PDF', value: 100, percentage: 67 }
      ];

      const rows = assembleMultiDisplayRows(transformedData, null);

      expect(rows).toHaveLength(1);
      expect(rows[0][0]).toBe(null);
      expect(rows[0][1]).toBe('PDF');
      expect(rows[0][2]).toBe('100 (67%)');
    });

    it('should handle empty transformed data', () => {
      const rows = assembleMultiDisplayRows([], null);

      expect(rows).toHaveLength(0);
    });
  });

  describe('filterSeriesArrayByDate integration', () => {
    it('should filter file types data by date range correctly', () => {
      const mockData = [
        {
          id: 'pdf',
          name: 'PDF',
          data: [
            { value: [new Date('2024-01-01'), 100] },
            { value: [new Date('2024-01-15'), 150] }
          ]
        }
      ];

      const filteredData = filterSeriesArrayByDate(mockData, { start: '2024-01-10', end: '2024-01-20' }, true);

      expect(filteredData).toHaveLength(1);
      expect(filteredData[0].data).toHaveLength(1);
      expect(filteredData[0].data[0].value[1]).toBe(150);
    });

    it('should handle empty date range by returning latest data when latestOnly is true', () => {
      const mockData = [
        {
          id: 'pdf',
          name: 'PDF',
          data: [
            { value: [new Date('2024-01-01'), 100] },
            { value: [new Date('2024-01-15'), 150] }
          ]
        }
      ];

      const filteredData = filterSeriesArrayByDate(mockData, null, true);

      expect(filteredData).toHaveLength(1);
      expect(filteredData[0].data).toHaveLength(1);
      expect(filteredData[0].data[0].value[1]).toBe(150);
    });

    it('should handle data outside the date range by returning empty data', () => {
      const mockData = [
        {
          id: 'pdf',
          name: 'PDF',
          data: [{ value: [new Date('2024-01-01'), 100] }]
        }
      ];

      const filteredData = filterSeriesArrayByDate(mockData, { start: '2024-02-01', end: '2024-02-28' }, true);

      expect(filteredData).toHaveLength(1);
      expect(filteredData[0].data).toHaveLength(0);
    });

    it('should work with the actual component data flow', () => {
      const mockData = [
        {
          id: 'pdf',
          name: 'PDF',
          data: [{ value: [new Date('2024-01-01'), 100] }]
        }
      ];

      const filteredData = filterSeriesArrayByDate(mockData, { start: '2024-01-01', end: '2024-01-31' }, true);
      const result = transformMultiDisplayData(filteredData, 10, 'files.entries.ext');

      expect(result.totalCount).toBe(100);
      expect(result.transformedData).toHaveLength(1);
    });
  });

  describe('Component rendering with different display types', () => {
    it('should render with list configuration', () => {
      render(<FileTypesMultiDisplay default_view="list" />);

      // Check that the component renders
      const statsDisplay = screen.getByRole('region');
      expect(statsDisplay).toBeInTheDocument();

      // For list view, we can check for actual table content
      expect(screen.getByText('PDF')).toBeInTheDocument();
      expect(screen.getByText('150 (60%)')).toBeInTheDocument();
      expect(screen.getByText('CSV')).toBeInTheDocument();
      expect(screen.getByText('75 (30%)')).toBeInTheDocument();
    });

    it('should render with custom pageSize', () => {
      render(<FileTypesMultiDisplay pageSize={2} default_view="list" />);

      // Should only show top 2 items plus "Other"
      expect(screen.getByText('PDF')).toBeInTheDocument();
      expect(screen.getByText('150 (60%)')).toBeInTheDocument();
      expect(screen.getByText('CSV')).toBeInTheDocument();
      expect(screen.getByText('75 (30%)')).toBeInTheDocument();
      expect(screen.getByText('Other')).toBeInTheDocument();
      expect(screen.getByText('25 (10%)')).toBeInTheDocument();
    });

    it('should render with custom available_views', () => {
      render(<FileTypesMultiDisplay available_views={["list"]} default_view="list" />);

      // Should still render the list view
      expect(screen.getByText('PDF')).toBeInTheDocument();
      expect(screen.getByText('CSV')).toBeInTheDocument();
      expect(screen.getByText('Text')).toBeInTheDocument();
    });

    it('should render with empty data', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: [{
          year: 2024,
          recordSnapshotDataAdded: {
            fileTypes: {
              records: []
            }
          }
        }],
        recordStartBasis: 'added',
        dateRange: { start: '2024-01-01', end: '2024-01-31' },
        isLoading: false
      });

      render(<FileTypesMultiDisplay default_view="list" />);

      const statsDisplay = screen.getByRole('region');
      expect(statsDisplay).toBeInTheDocument();
    });

    it('should render with custom title and icon', () => {
      render(<FileTypesMultiDisplay title="Custom Title" icon="file" default_view="list" />);

      const statsDisplay = screen.getByRole('region');
      expect(statsDisplay).toBeInTheDocument();
      expect(statsDisplay).toHaveAttribute('aria-label', 'Custom Title');
    });

    it('should render proper table structure with headers', () => {
      render(<FileTypesMultiDisplay default_view="list" />);

      // Check that table exists
      const table = screen.getByRole('table');
      expect(table).toBeInTheDocument();

      // Check table headers - the header row doesn't have a role, so we check the th elements
      const headerCells = screen.getAllByRole('columnheader');
      expect(headerCells).toHaveLength(3); // Icon column, File Type, Works

      // The header cells should contain the translated text
      expect(headerCells[1]).toHaveTextContent('File Type');
      expect(headerCells[2]).toHaveTextContent('Works');
    });

    it('should render table rows with proper structure', () => {
      render(<FileTypesMultiDisplay default_view="list" />);

      // Check that we have the expected number of data rows
      const dataRows = screen.getAllByTestId(/^row-\d+$/);
      expect(dataRows).toHaveLength(3); // 3 file types

      // Check first row structure
      const firstRow = dataRows[0];
      const firstRowCells = within(firstRow).getAllByRole('cell');
      expect(firstRowCells).toHaveLength(3); // icon cell + 2 data cells

      // Check that the first data cell contains the file type name
      expect(firstRowCells[1]).toHaveTextContent('PDF');
      expect(firstRowCells[2]).toHaveTextContent('150 (60%)');
    });

    it('should render table cells with proper data', () => {
      render(<FileTypesMultiDisplay default_view="list" />);

      // Check specific cell content
      const cells = screen.getAllByTestId(/^cell-\d+-\d+$/);
      expect(cells.length).toBeGreaterThan(0);

      // Check that we have the expected data in cells
      expect(screen.getByText('PDF')).toBeInTheDocument();
      expect(screen.getByText('150 (60%)')).toBeInTheDocument();
    });

    it('should have proper table accessibility attributes', () => {
      render(<FileTypesMultiDisplay default_view="list" />);

      const table = screen.getByRole('table');
      expect(table).toHaveAttribute('aria-labelledby');

      // Check for proper rowgroup roles
      const rowgroups = screen.getAllByRole('rowgroup');
      expect(rowgroups).toHaveLength(2); // thead and tbody
    });

    it('should render with custom headers properly', () => {
      const customHeaders = ['Custom File Type', 'Custom Count'];
      render(<FileTypesMultiDisplay headers={customHeaders} default_view="list" />);

      const headerCells = screen.getAllByRole('columnheader');
      expect(headerCells[1]).toHaveTextContent('Custom File Type');
      expect(headerCells[2]).toHaveTextContent('Custom Count');
    });

    it('should maintain proper table structure with pagination', () => {
      render(<FileTypesMultiDisplay pageSize={2} default_view="list" />);

      // Should have 3 rows (2 items + Other)
      const dataRows = screen.getAllByTestId(/^row-\d+$/);
      expect(dataRows).toHaveLength(3);
    });
  });
});