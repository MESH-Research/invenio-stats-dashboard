// Part of the Invenio-Stats-Dashboard extension for InvenioRDM
// Copyright (C) 2025 Mesh Research
//
// Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
// it under the terms of the MIT License; see LICENSE file for more details.

import React from 'react';
import { render, screen, within } from '@testing-library/react';
import { TopCountriesMultiDisplay } from './CountriesMultiDisplay';
import { filterSeriesArrayByDate } from '../../utils';
import { transformMultiDisplayData, assembleMultiDisplayRows } from '../../utils/multiDisplayHelpers';

// Mock only the external dependencies
jest.mock('@translations/invenio_stats_dashboard/i18next', () => ({
  i18next: {
    t: (key) => key
  }
}));

jest.mock('../../context/StatsDashboardContext', () => ({
  useStatsDashboard: jest.fn()
}));

jest.mock('../../constants', () => ({
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
    ADDED: 'added',
    CREATED: 'created',
    PUBLISHED: 'published'
  }
}));

describe('TopCountriesMultiDisplay', () => {
  const mockUseStatsDashboard = require('../../context/StatsDashboardContext').useStatsDashboard;

  beforeEach(() => {
    mockUseStatsDashboard.mockReturnValue({
      stats: {
        usageSnapshotData: {
          countriesByView: {
            views: [
              {
                id: 'united-states',
                name: 'United States',
                data: [{ value: [new Date('2024-01-01'), 150] }]
              },
              {
                id: 'germany',
                name: 'Germany',
                data: [{ value: [new Date('2024-01-01'), 75] }]
              },
              {
                id: 'france',
                name: 'France',
                data: [{ value: [new Date('2024-01-01'), 25] }]
              }
            ]
          }
        }
      },
      dateRange: { start: '2024-01-01', end: '2024-01-31' }
    });
  });

  describe('transformMultiDisplayData (helper function)', () => {
    it('should return empty data when input is null', () => {
      const result = transformMultiDisplayData(null, 10, 'metadata.country.id');

      expect(result).toEqual({
        transformedData: [],
        otherData: null,
        totalCount: 0
      });
    });

    it('should return empty data when input is undefined', () => {
      const result = transformMultiDisplayData(undefined, 10, 'metadata.country.id');

      expect(result).toEqual({
        transformedData: [],
        otherData: null,
        totalCount: 0
      });
    });

    it('should return empty data when input is not an array', () => {
      const result = transformMultiDisplayData('not an array', 10, 'metadata.country.id');

      expect(result).toEqual({
        transformedData: [],
        otherData: null,
        totalCount: 0
      });
    });

    it('should transform valid countries data correctly', () => {
      const mockData = [
        {
          id: 'united-states',
          name: 'United States',
          data: [{ value: [new Date('2024-01-01'), 150] }]
        },
        {
          id: 'germany',
          name: 'Germany',
          data: [{ value: [new Date('2024-01-01'), 75] }]
        },
        {
          id: 'france',
          name: 'France',
          data: [{ value: [new Date('2024-01-01'), 25] }]
        }
      ];

      const result = transformMultiDisplayData(mockData, 2, 'metadata.country.id');

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
          id: 'united-states',
          name: 'United States',
          data: [{ value: [new Date('2024-01-01'), 100] }]
        },
        {
          id: 'germany',
          name: 'Germany',
          data: [{ value: [new Date('2024-01-01'), 0] }] // Zero value
        },
        {
          id: 'france',
          name: 'France',
          data: [{ value: [new Date('2024-01-01'), 50] }]
        }
      ];

      const result = transformMultiDisplayData(mockData, 10, 'metadata.country.id');

      expect(result.totalCount).toBe(150); // 100 + 0 + 50
      expect(result.transformedData).toHaveLength(3);
      expect(result.transformedData[1].value).toBe(0);
      expect(result.transformedData[1].percentage).toBe(0);
    });

    it('should calculate percentages correctly', () => {
      const mockData = [
        {
          id: 'united-states',
          name: 'United States',
          data: [{ value: [new Date('2024-01-01'), 80] }]
        },
        {
          id: 'germany',
          name: 'Germany',
          data: [{ value: [new Date('2024-01-01'), 20] }]
        }
      ];

      const result = transformMultiDisplayData(mockData, 10, 'metadata.country.id');

      expect(result.totalCount).toBe(100);
      expect(result.transformedData[0].percentage).toBe(80); // 80/100 * 100
      expect(result.transformedData[1].percentage).toBe(20); // 20/100 * 100
    });

    it('should create correct links for each country', () => {
      const mockData = [
        {
          id: 'united-states',
          name: 'United States',
          data: [{ value: [new Date('2024-01-01'), 100] }]
        }
      ];

      const result = transformMultiDisplayData(mockData, 10, 'metadata.country.id');

      expect(result.transformedData[0].link).toBe('/search?q=metadata.country.id:united-states');
    });

    it('should create transformed data with all expected properties', () => {
      const mockData = [
        {
          id: 'united-states',
          name: 'United States',
          data: [{ value: [new Date('2024-01-01'), 100] }]
        },
        {
          id: 'germany',
          name: 'Germany',
          data: [{ value: [new Date('2024-01-01'), 50] }]
        }
      ];

      const result = transformMultiDisplayData(mockData, 10, 'metadata.country.id');

      expect(result.transformedData).toHaveLength(2);

      // Check first item properties
      const firstItem = result.transformedData[0];
      expect(firstItem).toHaveProperty('name', 'United States');
      expect(firstItem).toHaveProperty('value', 100);
      expect(firstItem).toHaveProperty('percentage', 67); // 100/150 * 100 rounded
      expect(firstItem).toHaveProperty('id', 'united-states');
      expect(firstItem).toHaveProperty('link', '/search?q=metadata.country.id:united-states');
      expect(firstItem).toHaveProperty('itemStyle');
      expect(firstItem.itemStyle).toHaveProperty('color');
      expect(typeof firstItem.itemStyle.color).toBe('string');

      // Check second item properties
      const secondItem = result.transformedData[1];
      expect(secondItem).toHaveProperty('name', 'Germany');
      expect(secondItem).toHaveProperty('value', 50);
      expect(secondItem).toHaveProperty('percentage', 33); // 50/150 * 100 rounded
      expect(secondItem).toHaveProperty('id', 'germany');
      expect(secondItem).toHaveProperty('link', '/search?q=metadata.country.id:germany');
      expect(secondItem).toHaveProperty('itemStyle');
      expect(secondItem.itemStyle).toHaveProperty('color');
      expect(typeof secondItem.itemStyle.color).toBe('string');
    });

    it('should create otherData with all expected properties when there are additional items', () => {
      const mockData = [
        {
          id: 'united-states',
          name: 'United States',
          data: [{ value: [new Date('2024-01-01'), 100] }]
        },
        {
          id: 'germany',
          name: 'Germany',
          data: [{ value: [new Date('2024-01-01'), 50] }]
        },
        {
          id: 'france',
          name: 'France',
          data: [{ value: [new Date('2024-01-01'), 25] }]
        }
      ];

      const result = transformMultiDisplayData(mockData, 2, 'metadata.country.id');

      expect(result.otherData).toBeTruthy();
      expect(result.otherData).toHaveProperty('id', 'other');
      expect(result.otherData).toHaveProperty('name', 'Other');
      expect(result.otherData).toHaveProperty('value', 25);
      expect(result.otherData).toHaveProperty('percentage', 14); // 25/175 * 100 rounded
      expect(result.otherData).toHaveProperty('itemStyle');
      expect(result.otherData.itemStyle).toHaveProperty('color');
      expect(typeof result.otherData.itemStyle.color).toBe('string');
    });

    it('should return null for otherData when there are no additional items', () => {
      const mockData = [
        {
          id: 'united-states',
          name: 'United States',
          data: [{ value: [new Date('2024-01-01'), 100] }]
        },
        {
          id: 'germany',
          name: 'Germany',
          data: [{ value: [new Date('2024-01-01'), 50] }]
        }
      ];

      const result = transformMultiDisplayData(mockData, 10, 'metadata.country.id');

      expect(result.otherData).toBeNull();
    });

    it('should handle zero total count', () => {
      const mockData = [
        {
          id: 'united-states',
          name: 'United States',
          data: [{ value: [new Date('2024-01-01'), 0] }]
        }
      ];

      const result = transformMultiDisplayData(mockData, 10, 'metadata.country.id');

      expect(result.totalCount).toBe(0);
      expect(result.transformedData[0].percentage).toBe(0);
    });
  });

  describe('assembleMultiDisplayRows (helper function)', () => {
    it('should assemble rows correctly with transformed data only', () => {
      const transformedData = [
        {
          name: 'United States',
          value: 100,
          percentage: 80,
          link: '/search?q=metadata.country.id:united-states'
        },
        {
          name: 'Germany',
          value: 25,
          percentage: 20,
          link: '/search?q=metadata.country.id:germany'
        }
      ];

      const rows = assembleMultiDisplayRows(transformedData, null);

      expect(rows).toHaveLength(2);
      expect(rows[0][0]).toBe(null);
      expect(rows[0][1].type).toBe('a');
      expect(rows[0][1].props.href).toBe('/search?q=metadata.country.id:united-states');
      expect(rows[0][1].props.children).toBe('United States');
      expect(rows[0][2]).toBe('100 (80%)');

      expect(rows[1][0]).toBe(null);
      expect(rows[1][1].type).toBe('a');
      expect(rows[1][1].props.href).toBe('/search?q=metadata.country.id:germany');
      expect(rows[1][1].props.children).toBe('Germany');
      expect(rows[1][2]).toBe('25 (20%)');
    });

    it('should include other data when provided', () => {
      const transformedData = [
        {
          name: 'United States',
          value: 100,
          percentage: 80,
          link: '/search?q=metadata.country.id:united-states'
        }
      ];

      const otherData = {
        name: 'Other',
        value: 25,
        percentage: 20
      };

      const rows = assembleMultiDisplayRows(transformedData, otherData);

      expect(rows).toHaveLength(2);
      expect(rows[0][0]).toBe(null);
      expect(rows[0][1].type).toBe('a');
      expect(rows[0][1].props.href).toBe('/search?q=metadata.country.id:united-states');
      expect(rows[0][1].props.children).toBe('United States');
      expect(rows[0][2]).toBe('100 (80%)');

      expect(rows[1][0]).toBe(null);
      expect(rows[1][1]).toBe('Other');
      expect(rows[1][2]).toBe('25 (20%)');
    });

    it('should handle data without links', () => {
      const transformedData = [
        {
          name: 'United States',
          value: 100,
          percentage: 100
        }
      ];

      const rows = assembleMultiDisplayRows(transformedData, null);

      expect(rows).toHaveLength(1);
      expect(rows[0][0]).toBe(null);
      expect(rows[0][1]).toBe('United States');
      expect(rows[0][2]).toBe('100 (100%)');
    });

    it('should handle empty transformed data', () => {
      const rows = assembleMultiDisplayRows([], null);

      expect(rows).toHaveLength(0);
    });
  });

  describe('filterSeriesArrayByDate integration', () => {
    it('should filter countries data by date range correctly', () => {
      const mockCountriesData = [
        {
          id: 'united-states',
          name: 'United States',
          data: [
            { value: [new Date('2024-01-01'), 100] },
            { value: [new Date('2024-01-15'), 150] },
            { value: [new Date('2024-01-30'), 200] }
          ]
        },
        {
          id: 'germany',
          name: 'Germany',
          data: [
            { value: [new Date('2024-01-05'), 50] },
            { value: [new Date('2024-01-20'), 75] },
            { value: [new Date('2024-02-01'), 100] } // Outside range
          ]
        }
      ];

      const dateRange = {
        start: new Date('2024-01-10'),
        end: new Date('2024-01-25')
      };

      const filteredData = filterSeriesArrayByDate(mockCountriesData, dateRange, true);

      // Should only include data points within the date range
      expect(filteredData).toHaveLength(2);

      // United States should have the latest data point within range (Jan 15)
      expect(filteredData[0].id).toBe('united-states');
      expect(filteredData[0].data).toHaveLength(1);
      expect(filteredData[0].data[0].value[1]).toBe(150);

      // Germany should have the latest data point within range (Jan 20)
      expect(filteredData[1].id).toBe('germany');
      expect(filteredData[1].data).toHaveLength(1);
      expect(filteredData[1].data[0].value[1]).toBe(75);
    });

    it('should handle empty date range by returning latest data when latestOnly is true', () => {
      const mockCountriesData = [
        {
          id: 'united-states',
          name: 'United States',
          data: [
            { value: [new Date('2024-01-01'), 100] },
            { value: [new Date('2024-01-15'), 150] }
          ]
        }
      ];

      const dateRange = {};

      const filteredData = filterSeriesArrayByDate(mockCountriesData, dateRange, true);

      // When latestOnly=true with empty date range, it returns only the latest data point
      expect(filteredData).toHaveLength(1);
      expect(filteredData[0].id).toBe('united-states');
      expect(filteredData[0].data).toHaveLength(1); // Returns only the latest
      expect(filteredData[0].data[0].value[1]).toBe(150);
    });

    it('should handle data outside the date range by returning empty data', () => {
      const mockCountriesData = [
        {
          id: 'united-states',
          name: 'United States',
          data: [
            { value: [new Date('2024-01-01'), 100] }, // Before range
            { value: [new Date('2024-02-01'), 200] }  // After range
          ]
        }
      ];

      const dateRange = {
        start: new Date('2024-01-15'),
        end: new Date('2024-01-20')
      };

      const filteredData = filterSeriesArrayByDate(mockCountriesData, dateRange, true);

      // Should return series with empty data when no points fall within range
      expect(filteredData).toHaveLength(1);
      expect(filteredData[0].id).toBe('united-states');
      expect(filteredData[0].data).toHaveLength(0);
    });

    it('should work with the actual component data flow', () => {
      const mockCountriesData = [
        {
          id: 'united-states',
          name: 'United States',
          data: [
            { value: [new Date('2024-01-01'), 100] },
            { value: [new Date('2024-01-15'), 150] }
          ]
        },
        {
          id: 'germany',
          name: 'Germany',
          data: [
            { value: [new Date('2024-01-10'), 50] },
            { value: [new Date('2024-01-20'), 75] }
          ]
        }
      ];

      const dateRange = {
        start: new Date('2024-01-10'),
        end: new Date('2024-01-20')
      };

      // Simulate the component's filtering step
      const filteredData = filterSeriesArrayByDate(mockCountriesData, dateRange, true);

      // Then transform the filtered data using our helper function
      const result = transformMultiDisplayData(filteredData, 10, 'metadata.country.id');

      expect(result.totalCount).toBe(225); // 150 + 75
      expect(result.transformedData).toHaveLength(2);
      expect(result.transformedData[0].value).toBe(150);
      expect(result.transformedData[0].percentage).toBe(67); // 150/225 * 100 rounded
      expect(result.transformedData[1].value).toBe(75);
      expect(result.transformedData[1].percentage).toBe(33); // 75/225 * 100 rounded
    });
  });

  describe('Component rendering with different display types', () => {
    beforeEach(() => {
      mockUseStatsDashboard.mockReturnValue({
        stats: {
          usageSnapshotData: {
            countriesByView: {
              views: [
                {
                  id: 'united-states',
                  name: 'United States',
                  data: [{ value: [new Date('2024-01-01'), 100] }]
                },
                {
                  id: 'germany',
                  name: 'Germany',
                  data: [{ value: [new Date('2024-01-01'), 50] }]
                },
                {
                  id: 'france',
                  name: 'France',
                  data: [{ value: [new Date('2024-01-01'), 25] }]
                }
              ]
            }
          }
        },
        dateRange: { start: '2024-01-01', end: '2024-01-31' }
      });
    });

    it('should render with list configuration', () => {
      render(<TopCountriesMultiDisplay default_view="list" />);

      const statsDisplay = screen.getByRole('region');
      expect(statsDisplay).toBeInTheDocument();

      // For list view, we can check for actual table content
      expect(screen.getByText('United States')).toBeInTheDocument();
      expect(screen.getByText('100 (57%)')).toBeInTheDocument();
      expect(screen.getByText('Germany')).toBeInTheDocument();
      expect(screen.getByText('50 (29%)')).toBeInTheDocument();
      expect(screen.getByText('France')).toBeInTheDocument();
      expect(screen.getByText('25 (14%)')).toBeInTheDocument();
    });

    it('should render with custom pageSize', () => {
      render(<TopCountriesMultiDisplay pageSize={2} default_view="list" />);

      const statsDisplay = screen.getByRole('region');
      expect(statsDisplay).toBeInTheDocument();

      // Should only show top 2 items plus "Other"
      expect(screen.getByText('United States')).toBeInTheDocument();
      expect(screen.getByText('100 (57%)')).toBeInTheDocument();
      expect(screen.getByText('Germany')).toBeInTheDocument();
      expect(screen.getByText('50 (29%)')).toBeInTheDocument();
      expect(screen.getByText('Other')).toBeInTheDocument();
      expect(screen.getByText('25 (14%)')).toBeInTheDocument();
    });

    it('should render with custom available_views', () => {
      render(<TopCountriesMultiDisplay available_views={["list"]} default_view="list" />);

      const statsDisplay = screen.getByRole('region');
      expect(statsDisplay).toBeInTheDocument();

      // Should still render the list view
      expect(screen.getByText('United States')).toBeInTheDocument();
      expect(screen.getByText('Germany')).toBeInTheDocument();
      expect(screen.getByText('France')).toBeInTheDocument();
    });

    it('should render with empty data', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: {
          usageSnapshotData: {
            countriesByView: {
              views: []
            }
          }
        },
        dateRange: { start: '2024-01-01', end: '2024-01-31' }
      });

      render(<TopCountriesMultiDisplay default_view="list" />);

      const statsDisplay = screen.getByRole('region');
      expect(statsDisplay).toBeInTheDocument();

      // Should render with no content when there's no data
      expect(screen.queryByText('United States')).not.toBeInTheDocument();
    });

    it('should render with custom title and icon', () => {
      render(<TopCountriesMultiDisplay title="Custom Title" icon="globe" default_view="list" />);

      const statsDisplay = screen.getByRole('region');
      expect(statsDisplay).toBeInTheDocument();
      expect(statsDisplay).toHaveAttribute('aria-label', 'Custom Title');
    });

    it('should render proper table structure with headers', () => {
      render(<TopCountriesMultiDisplay default_view="list" />);

      // Check that table exists
      const table = screen.getByRole('table');
      expect(table).toBeInTheDocument();

      // Check table headers - the header row doesn't have a name, so we check by role
      const headerRows = screen.getAllByRole('row');
      const headerRow = headerRows[0]; // First row should be header
      expect(headerRow).toBeInTheDocument();

      // Check header cells
      const headerCells = within(headerRow).getAllByRole('columnheader');
      expect(headerCells).toHaveLength(3); // icon column + 2 data columns

      // The header cells should contain the translated text
      expect(headerCells[1]).toHaveTextContent('Country');
      expect(headerCells[2]).toHaveTextContent('Visits');
    });

    it('should render table rows with proper structure', () => {
      render(<TopCountriesMultiDisplay default_view="list" />);

      // Check that we have the expected number of data rows
      const dataRows = screen.getAllByTestId(/^row-\d+$/);
      expect(dataRows).toHaveLength(3); // 3 countries

      // Check first row structure
      const firstRow = dataRows[0];
      const firstRowCells = within(firstRow).getAllByRole('cell');
      expect(firstRowCells).toHaveLength(3); // icon cell + 2 data cells

      // Check that the first data cell contains the country name
      expect(firstRowCells[1]).toHaveTextContent('United States');
      expect(firstRowCells[2]).toHaveTextContent('100 (57%)');
    });

    it('should render table cells with proper data', () => {
      render(<TopCountriesMultiDisplay default_view="list" />);

      // Check specific cell content
      const cells = screen.getAllByTestId(/^cell-\d+-\d+$/);
      expect(cells.length).toBeGreaterThan(0);

      // Check that we have the expected data in cells
      expect(screen.getByText('United States')).toBeInTheDocument();
      expect(screen.getByText('100 (57%)')).toBeInTheDocument();
      expect(screen.getByText('Germany')).toBeInTheDocument();
      expect(screen.getByText('50 (29%)')).toBeInTheDocument();
    });

    it('should have proper table accessibility attributes', () => {
      render(<TopCountriesMultiDisplay default_view="list" />);

      const table = screen.getByRole('table');
      expect(table).toHaveAttribute('aria-labelledby');

      // Check that table has proper structure - thead and tbody
      const rowgroups = screen.getAllByRole('rowgroup');
      expect(rowgroups).toHaveLength(2); // thead and tbody
    });

    it('should render with custom headers properly', () => {
      const customHeaders = ['Custom Country', 'Custom Count'];
      render(<TopCountriesMultiDisplay headers={customHeaders} default_view="list" />);

      // Check that custom headers are rendered in the header row
      const headerRows = screen.getAllByRole('row');
      const headerRow = headerRows[0]; // First row should be header

      const headerCells = within(headerRow).getAllByRole('columnheader');
      expect(headerCells).toHaveLength(3); // icon column + 2 custom headers
      expect(headerCells[1]).toHaveTextContent('Custom Country');
      expect(headerCells[2]).toHaveTextContent('Custom Count');
    });

    it('should maintain proper table structure with pagination', () => {
      render(<TopCountriesMultiDisplay pageSize={2} default_view="list" />);

      // Check table structure is maintained
      const table = screen.getByRole('table');
      expect(table).toBeInTheDocument();

      // Should have 3 rows (2 items + Other)
      const dataRows = screen.getAllByTestId(/^row-\d+$/);
      expect(dataRows).toHaveLength(3);
    });
  });
});