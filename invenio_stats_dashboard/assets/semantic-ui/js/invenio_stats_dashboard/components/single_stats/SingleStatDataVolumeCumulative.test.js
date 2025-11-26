// Part of the Invenio-Stats-Dashboard extension for InvenioRDM
// Copyright (C) 2025 Mesh Research
//
// Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
// it under the terms of the MIT License; see LICENSE file for more details.

import React from 'react';
import { render, screen } from '@testing-library/react';
import { SingleStatDataVolumeCumulative } from './SingleStatDataVolumeCumulative';
import { useStatsDashboard } from '../../context/StatsDashboardContext';

// Mock the dependencies
jest.mock('../../context/StatsDashboardContext');

const mockUseStatsDashboard = useStatsDashboard;

describe('SingleStatDataVolumeCumulative', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('Basic Rendering', () => {
    beforeEach(() => {
      mockUseStatsDashboard.mockReturnValue({
        stats: [{
          year: 2024,
          recordSnapshotDataAdded: {
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
        }],
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') },
        recordStartBasis: 'added',
        isLoading: false,
        binary_sizes: false // Use default setting
      });
    });

    it('should render with default title and value', () => {
      render(<SingleStatDataVolumeCumulative />);

      expect(screen.getByText('Cumulative Data Volume')).toBeInTheDocument();
      expect(screen.getByText('2 kB')).toBeInTheDocument(); // Latest value in range with decimal formatting
    });

    it('should render with custom title', () => {
      render(<SingleStatDataVolumeCumulative title="Custom Cumulative Data Volume" />);

      expect(screen.getByText('Custom Cumulative Data Volume')).toBeInTheDocument();
    });

    it('should display description with "as of" date', () => {
      render(<SingleStatDataVolumeCumulative />);

      // The description should contain "as of" and the end date
      expect(screen.getByText(/as of/)).toBeInTheDocument();
    });

    it('should use binary formatting when binary_sizes is true', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: [{
          year: 2024,
          recordSnapshotDataAdded: {
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
        }],
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') },
        recordStartBasis: 'added',
        isLoading: false,
        binary_sizes: true // Test binary formatting
      });

      render(<SingleStatDataVolumeCumulative />);

      expect(screen.getByText('2 KiB')).toBeInTheDocument(); // Binary formatting
    });
  });

  describe('HTML Structure and Accessibility', () => {
    beforeEach(() => {
      mockUseStatsDashboard.mockReturnValue({
        stats: [{
          year: 2024,
          recordSnapshotDataAdded: {
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
        }],
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') },
        recordStartBasis: 'added',
        isLoading: false,
        binary_sizes: false
      });
    });

    it('should have correct container structure and CSS classes', () => {
      const { container } = render(<SingleStatDataVolumeCumulative />);

      // Check main container
      const mainContainer = container.querySelector('.stats-single-stat-container');
      expect(mainContainer).toBeInTheDocument();
      expect(mainContainer).toHaveAttribute('role', 'region');
      expect(mainContainer).toHaveAttribute('aria-describedby');
      expect(mainContainer).toHaveAttribute('aria-label', 'Cumulative Data Volume');
    });

    it('should have correct value element structure', () => {
      const { container } = render(<SingleStatDataVolumeCumulative />);

      // Check value element
      const valueElement = container.querySelector('.value.stats-single-stat-value');
      expect(valueElement).toBeInTheDocument();
      expect(valueElement).toHaveAttribute('aria-label', '2 kB Cumulative Data Volume');
      expect(valueElement).toHaveTextContent('2 kB');
    });

    it('should have correct header structure with icon', () => {
      const { container } = render(<SingleStatDataVolumeCumulative />);

      // Check header element
      const headerElement = container.querySelector('.label.stats-single-stat-header.mt-5');
      expect(headerElement).toBeInTheDocument();
      expect(headerElement).toHaveTextContent('Cumulative Data Volume');

      // Check icon
      const iconElement = headerElement.querySelector('.database.icon.mr-10');
      expect(iconElement).toBeInTheDocument();
      expect(iconElement).toHaveAttribute('aria-hidden', 'true');
    });

    it('should have correct description structure', () => {
      const { container } = render(<SingleStatDataVolumeCumulative />);

      // Check description element
      const descriptionElement = container.querySelector('.label.stats-single-stat-description.mt-5');
      expect(descriptionElement).toBeInTheDocument();
      expect(descriptionElement).toHaveAttribute('id');
      expect(descriptionElement).toHaveAttribute('aria-label');
      expect(descriptionElement).toHaveTextContent(/as of/);
    });

    it('should have proper accessibility attributes', () => {
      const { container } = render(<SingleStatDataVolumeCumulative />);

      const mainContainer = container.querySelector('.stats-single-stat-container');
      const descriptionElement = container.querySelector('.stats-single-stat-description');

      // Check that aria-describedby points to the description element
      const describedBy = mainContainer.getAttribute('aria-describedby');
      expect(describedBy).toBe(descriptionElement.getAttribute('id'));
    });

    it('should handle custom title in accessibility attributes', () => {
      const { container } = render(<SingleStatDataVolumeCumulative title="Custom Title" />);

      const mainContainer = container.querySelector('.stats-single-stat-container');
      const valueElement = container.querySelector('.value');

      expect(mainContainer).toHaveAttribute('aria-label', 'Custom Title');
      expect(valueElement).toHaveAttribute('aria-label', '2 kB Custom Title');
    });

    it('should handle custom icon', () => {
      const { container } = render(<SingleStatDataVolumeCumulative icon="chart bar" />);

      const iconElement = container.querySelector('.chart.bar.icon.mr-10');
      expect(iconElement).toBeInTheDocument();
      expect(iconElement).toHaveAttribute('aria-hidden', 'true');
    });
  });

  describe('Snapshot Data Handling', () => {
    it('should get the latest snapshot value within date range', () => {
      // Test data with multiple snapshot values
      mockUseStatsDashboard.mockReturnValue({
        stats: [{
          year: 2024,
          recordSnapshotDataAdded: {
            global: {
              dataVolume: [
                {
                  id: 'global',
                  name: 'Global',
                  year: 2024,
                  data: [
                    ['12-31', 512],  // Before range (2023)
                    ['01-01', 1024], // In range
                    ['01-02', 2048], // In range (latest)
                    ['01-03', 4096]  // After range
                  ]
                }
              ]
            }
          }
        }],
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') },
        recordStartBasis: 'added',
        isLoading: false,
        binary_sizes: false // Use default setting
      });

      render(<SingleStatDataVolumeCumulative />);

      // Should show the latest snapshot value within the range: 2048 bytes = 2 kB (decimal)
      expect(screen.getByText('2 kB')).toBeInTheDocument();
    });

    it('should handle data completely outside date range', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: {
          recordSnapshotDataAdded: {
            global: {
              dataVolume: [
                {
                  id: 'dataVolume',
                  name: 'Data Volume',
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
        },
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') },
        recordStartBasis: 'added',
        isLoading: false,
        binary_sizes: false // Use default setting
      });

      render(<SingleStatDataVolumeCumulative />);

      // Should show 0 since no data is within the date range
      expect(screen.getByText('0 B')).toBeInTheDocument();
    });

    it('should handle partial date ranges (only start date)', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: [
          {
            year: 2023,
            recordSnapshotDataAdded: {
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
            recordSnapshotDataAdded: {
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
        recordStartBasis: 'added',
        isLoading: false,
        binary_sizes: false // Use default setting
      });

      render(<SingleStatDataVolumeCumulative />);

      // Should show the latest snapshot value from start date onwards: 4096 bytes = 4.1 kB (decimal)
      expect(screen.getByText('4.1 kB')).toBeInTheDocument();
    });

    it('should handle partial date ranges (only end date)', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: [{
          year: 2024,
          recordSnapshotDataAdded: {
            global: {
              dataVolume: [
                {
                  id: 'global',
                  name: 'Global',
                  year: 2024,
                  data: [
                    ['12-31', 512],  // Before end
                    ['01-01', 1024], // Before end
                    ['01-02', 2048], // On end date
                    ['01-03', 4096]  // After end
                  ]
                }
              ]
            }
          }
        }],
        dateRange: { start: null, end: new Date('2024-01-02T00:00:00.000Z') },
        recordStartBasis: 'added',
        isLoading: false,
        binary_sizes: false // Use default setting
      });

      render(<SingleStatDataVolumeCumulative />);

      // Should show the latest snapshot value up to and including end date: 2048 bytes = 2 kB (decimal)
      expect(screen.getByText('2 kB')).toBeInTheDocument();
    });

    it('should handle single data point in range', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: [{
          year: 2024,
          recordSnapshotDataAdded: {
            global: {
              dataVolume: [
                {
                  id: 'global',
                  name: 'Global',
                  year: 2024,
                  data: [
                    ['01-01', 1024]  // Only one point in range
                  ]
                }
              ]
            }
          }
        }],
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') },
        recordStartBasis: 'added',
        isLoading: false,
        binary_sizes: false // Use default setting
      });

      render(<SingleStatDataVolumeCumulative />);

      // Should show the single value: 1024 bytes = 1 kB (decimal)
      expect(screen.getByText('1 kB')).toBeInTheDocument();
    });
  });

  describe('Different Record Bases', () => {
    it('should handle different record start basis correctly', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: [{
          year: 2024,
          recordSnapshotDataCreated: {
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
        }],
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') },
        recordStartBasis: 'created',
        isLoading: false,
        binary_sizes: false // Use default setting
      });

      render(<SingleStatDataVolumeCumulative />);

      expect(screen.getByText('2 kB')).toBeInTheDocument();
    });

    it('should handle published record basis', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: [{
          year: 2024,
          recordSnapshotDataPublished: {
            global: {
              dataVolume: [
                {
                  id: 'global',
                  name: 'Global',
                  year: 2024,
                  data: [
                    ['01-01', 512],
                    ['01-02', 1024]
                  ]
                }
              ]
            }
          }
        }],
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') },
        recordStartBasis: 'published',
        isLoading: false,
        binary_sizes: false // Use default setting
      });

      render(<SingleStatDataVolumeCumulative />);

      expect(screen.getByText('1 kB')).toBeInTheDocument(); // 1024 bytes = 1 kB (decimal)
    });
  });

  describe('Edge Cases and Error Handling', () => {
    it('should handle empty stats gracefully', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: null,
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') },
        recordStartBasis: 'added',
        isLoading: false,
        binary_sizes: false // Use default setting
      });

      render(<SingleStatDataVolumeCumulative />);

      expect(screen.getByText('0 B')).toBeInTheDocument();
    });

    it('should handle empty data array', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: {
          recordSnapshotDataAdded: {
            global: {
              dataVolume: [
                {
                  id: 'dataVolume',
                  name: 'Data Volume',
                  data: []
                }
              ]
            }
          }
        },
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') },
        recordStartBasis: 'added',
        isLoading: false,
        binary_sizes: false // Use default setting
      });

      render(<SingleStatDataVolumeCumulative />);

      expect(screen.getByText('0 B')).toBeInTheDocument();
    });

    it('should handle missing data property', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: {
          recordSnapshotDataAdded: {
            global: {
              dataVolume: [
                {
                  id: 'dataVolume',
                  name: 'Data Volume'
                  // Missing data property
                }
              ]
            }
          }
        },
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') },
        recordStartBasis: 'added',
        isLoading: false,
        binary_sizes: false // Use default setting
      });

      render(<SingleStatDataVolumeCumulative />);

      expect(screen.getByText('0 B')).toBeInTheDocument();
    });

    it('should handle no date range', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: [{
          year: 2024,
          recordSnapshotDataAdded: {
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
        }],
        dateRange: null,
        recordStartBasis: 'added',
        isLoading: false,
        binary_sizes: false // Use default setting
      });

      render(<SingleStatDataVolumeCumulative />);

      // Should show the latest snapshot value when no date range is provided: 2048 bytes = 2 kB (decimal)
      expect(screen.getByText('2 kB')).toBeInTheDocument();
    });
  });
});