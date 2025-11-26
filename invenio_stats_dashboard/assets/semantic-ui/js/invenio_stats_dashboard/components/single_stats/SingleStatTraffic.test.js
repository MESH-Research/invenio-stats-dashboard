// Part of the Invenio-Stats-Dashboard extension for InvenioRDM
// Copyright (C) 2025 Mesh Research
//
// Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
// it under the terms of the MIT License; see LICENSE file for more details.

import React from 'react';
import { render, screen } from '@testing-library/react';
import { SingleStatTraffic } from './SingleStatTraffic';
import { useStatsDashboard } from '../../context/StatsDashboardContext';

// Mock the dependencies
jest.mock('../../context/StatsDashboardContext');

const mockUseStatsDashboard = useStatsDashboard;

describe('SingleStatTraffic', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('Basic Rendering', () => {
    beforeEach(() => {
      mockUseStatsDashboard.mockReturnValue({
        stats: [
          {
            year: 2024,
            usageDeltaData: {
              global: {
                dataVolume: [
                {
                  id: 'global',
                  name: 'Global',
                  year: 2024,
                  data: [
                    ['01-01', 1024],
                    ['01-02', 2048]
                  ]
                }
                ]
              }
            }
          }
        ],
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') },
        binary_sizes: false,
        isLoading: false // Use default setting
      });
    });

    it('should render with default title and value', () => {
      render(<SingleStatTraffic />);

      expect(screen.getByText('Traffic')).toBeInTheDocument();
      expect(screen.getByText('3.1 kB')).toBeInTheDocument(); // 1024 + 2048 = 3072 bytes = 3.1 kB
    });

    it('should render with custom title', () => {
      render(<SingleStatTraffic title="Custom Traffic" />);

      expect(screen.getByText('Custom Traffic')).toBeInTheDocument();
    });

    it('should display description with date range', () => {
      render(<SingleStatTraffic />);

      // The description should contain the date range
      expect(screen.getByText(/from/)).toBeInTheDocument();
      expect(screen.getByText(/–/)).toBeInTheDocument();
    });

    it('should use binary formatting when binary_sizes is true', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: [
          {
            year: 2024,
            usageDeltaData: {
              global: {
                dataVolume: [
                {
                  id: 'global',
                  name: 'Global',
                  year: 2024,
                  data: [
                    ['01-01', 1024],
                    ['01-02', 2048]
                  ]
                }
                ]
              }
            }
          }
        ],
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') },
        binary_sizes: true // Test binary formatting
      });

      render(<SingleStatTraffic />);

      expect(screen.getByText('3 KiB')).toBeInTheDocument(); // Binary formatting
    });
  });

  describe('HTML Structure and Accessibility', () => {
    beforeEach(() => {
      mockUseStatsDashboard.mockReturnValue({
        stats: [
          {
            year: 2024,
            usageDeltaData: {
              global: {
                dataVolume: [
                {
                  id: 'global',
                  name: 'Global',
                  year: 2024,
                  data: [
                    ['01-01', 1024],
                    ['01-02', 2048]
                  ]
                }
                ]
              }
            }
          }
        ],
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') },
        binary_sizes: false,
        isLoading: false,
        isLoading: false
      });
    });

    it('should have correct container structure and CSS classes', () => {
      const { container } = render(<SingleStatTraffic />);

      // Check main container
      const mainContainer = container.querySelector('.stats-single-stat-container');
      expect(mainContainer).toBeInTheDocument();
      expect(mainContainer).toHaveAttribute('role', 'region');
      expect(mainContainer).toHaveAttribute('aria-describedby');
      expect(mainContainer).toHaveAttribute('aria-label', 'Traffic');
    });

    it('should have correct value element structure', () => {
      const { container } = render(<SingleStatTraffic />);

      // Check value element
      const valueElement = container.querySelector('.value.stats-single-stat-value');
      expect(valueElement).toBeInTheDocument();
      expect(valueElement).toHaveAttribute('aria-label', '3.1 kB Traffic');
      expect(valueElement).toHaveTextContent('3.1 kB');
    });

    it('should have correct header structure with icon', () => {
      const { container } = render(<SingleStatTraffic />);

      // Check header element
      const headerElement = container.querySelector('.label.stats-single-stat-header.mt-5');
      expect(headerElement).toBeInTheDocument();
      expect(headerElement).toHaveTextContent('Traffic');

      // Check icon
      const iconElement = headerElement.querySelector('.chart.line.icon.mr-10');
      expect(iconElement).toBeInTheDocument();
      expect(iconElement).toHaveAttribute('aria-hidden', 'true');
    });

    it('should have correct description structure', () => {
      const { container } = render(<SingleStatTraffic />);

      // Check description element
      const descriptionElement = container.querySelector('.label.stats-single-stat-description.mt-5');
      expect(descriptionElement).toBeInTheDocument();
      expect(descriptionElement).toHaveAttribute('id');
      expect(descriptionElement).toHaveAttribute('aria-label');
      expect(descriptionElement).toHaveTextContent(/from/);
    });

    it('should have proper accessibility attributes', () => {
      const { container } = render(<SingleStatTraffic />);

      const mainContainer = container.querySelector('.stats-single-stat-container');
      const descriptionElement = container.querySelector('.stats-single-stat-description');

      // Check that aria-describedby points to the description element
      const describedBy = mainContainer.getAttribute('aria-describedby');
      expect(describedBy).toBe(descriptionElement.getAttribute('id'));
    });

    it('should handle custom title in accessibility attributes', () => {
      const { container } = render(<SingleStatTraffic title="Custom Title" />);

      const mainContainer = container.querySelector('.stats-single-stat-container');
      const valueElement = container.querySelector('.value');

      expect(mainContainer).toHaveAttribute('aria-label', 'Custom Title');
      expect(valueElement).toHaveAttribute('aria-label', '3.1 kB Custom Title');
    });

    it('should handle custom icon', () => {
      const { container } = render(<SingleStatTraffic icon="chart bar" />);

      const iconElement = container.querySelector('.chart.bar.icon.mr-10');
      expect(iconElement).toBeInTheDocument();
      expect(iconElement).toHaveAttribute('aria-hidden', 'true');
    });
  });

  describe('Date Filtering and Cumulative Totaling', () => {
    it('should filter data by date range and sum values correctly', () => {
      // Test data with values inside and outside the date range
      mockUseStatsDashboard.mockReturnValue({
        stats: [
          {
            year: 2024,
            usageDeltaData: {
              global: {
                dataVolume: [
                  {
                    id: 'global',
                    name: 'Global',
                  year: 2024,
                  data: [
                    ['12-31', 512],  // Outside range (2023)
                    ['01-01', 1024], // Inside range
                    ['01-02', 2048], // Inside range
                    ['01-03', 4096]  // Outside range
                  ]
                }
                ]
              }
            }
          }
        ],
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') },
        binary_sizes: false,
        isLoading: false
      });

      render(<SingleStatTraffic />);

      // Should only sum values within the date range: 1024 + 2048 = 3072 bytes = 3.1 kB
      expect(screen.getByText('3.1 kB')).toBeInTheDocument();
    });

    it('should handle data completely outside date range', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: [
          {
            year: 2024,
            usageDeltaData: {
              global: {
                dataVolume: [
                  {
                    id: 'global',
                    name: 'Global',
                  year: 2024,
                  data: [
                    ['12-30', 512],  // Outside range
                    ['12-31', 1024], // Outside range
                    ['01-03', 2048], // Outside range
                    ['01-04', 4096]  // Outside range
                  ]
                }
                ]
              }
            }
          }
        ],
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') },
        binary_sizes: false,
        isLoading: false
      });

      render(<SingleStatTraffic />);

      // Should show 0 since no data is within the date range
      expect(screen.getByText('0 B')).toBeInTheDocument();
    });

    it('should handle partial date ranges (only start date)', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: [
          {
            year: 2023,
            usageDeltaData: {
              global: {
                dataVolume: [
                  {
                    id: 'global',
                    name: 'Global',
                    year: 2023,
                    data: [
                      ['12-31', 512]  // Before start
                    ]
                  }
                ]
              }
            }
          },
          {
            year: 2024,
            usageDeltaData: {
              global: {
                dataVolume: [
                  {
                    id: 'global',
                    name: 'Global',
                    year: 2024,
                    data: [
                      ['01-01', 1024], // On start date
                      ['01-02', 2048], // After start
                      ['01-03', 4096]  // After start
                    ]
                  }
                ]
              }
            }
          }
        ],
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: null },
        binary_sizes: false,
        isLoading: false
      });

      render(<SingleStatTraffic />);

      // Should include all data from start date onwards: 1024 + 2048 + 4096 = 7168 bytes = 7.2 kB
      expect(screen.getByText('7.2 kB')).toBeInTheDocument();
    });

    it('should handle partial date ranges (only end date)', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: [
          {
            year: 2023,
            usageDeltaData: {
              global: {
                dataVolume: [
                  {
                    id: 'global',
                    name: 'Global',
                    year: 2023,
                    data: [
                      ['12-31', 512]  // Before end
                    ]
                  }
                ]
              }
            }
          },
          {
            year: 2024,
            usageDeltaData: {
              global: {
                dataVolume: [
                  {
                    id: 'global',
                    name: 'Global',
                    year: 2024,
                    data: [
                      ['01-01', 1024], // Before end
                      ['01-02', 2048], // On end date
                      ['01-03', 4096]  // After end
                    ]
                  }
                ]
              }
            }
          }
        ],
        dateRange: { start: null, end: new Date('2024-01-02T00:00:00.000Z') },
        binary_sizes: false,
        isLoading: false
      });

      render(<SingleStatTraffic />);

      // Should include all data up to and including end date: 512 + 1024 + 2048 = 3584 bytes = 3.6 kB
      expect(screen.getByText('3.6 kB')).toBeInTheDocument();
    });
  });

  describe('Edge Cases and Error Handling', () => {
    it('should handle empty stats gracefully', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: null,
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') },
        binary_sizes: false,
        isLoading: false
      });

      render(<SingleStatTraffic />);

      expect(screen.getByText('0 B')).toBeInTheDocument();
    });

    it('should handle empty data array', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: [
          {
            year: 2024,
            usageDeltaData: {
              global: {
                dataVolume: [
                  {
                    id: 'global',
                    name: 'Global',
                  data: []
                }
                ]
              }
            }
          }
        ],
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') },
        binary_sizes: false,
        isLoading: false
      });

      render(<SingleStatTraffic />);

      expect(screen.getByText('0 B')).toBeInTheDocument();
    });

    it('should handle missing data property', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: [
          {
            year: 2024,
            usageDeltaData: {
              global: {
                dataVolume: [
                  {
                    id: 'global',
                    name: 'Global'
                    // Missing data property
                  }
                ]
              }
            }
          }
        ],
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') },
        binary_sizes: false,
        isLoading: false
      });

      render(<SingleStatTraffic />);

      expect(screen.getByText('0 B')).toBeInTheDocument();
    });

    it('should handle no date range', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: [
          {
            year: 2024,
            usageDeltaData: {
              global: {
                dataVolume: [
                {
                  id: 'global',
                  name: 'Global',
                  year: 2024,
                  data: [
                    ['01-01', 1024],
                    ['01-02', 2048]
                  ]
                }
                ]
              }
            }
          }
        ],
        dateRange: null,
        binary_sizes: false,
        isLoading: false
      });

      render(<SingleStatTraffic />);

      // Should sum all data when no date range is provided: 1024 + 2048 = 3072 bytes = 3.1 kB
      expect(screen.getByText('3.1 kB')).toBeInTheDocument();
    });
  });
});