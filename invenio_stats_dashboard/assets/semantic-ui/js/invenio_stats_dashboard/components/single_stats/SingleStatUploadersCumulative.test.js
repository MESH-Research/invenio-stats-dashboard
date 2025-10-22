// Part of the Invenio-Stats-Dashboard extension for InvenioRDM
// Copyright (C) 2025 Mesh Research
//
// Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
// it under the terms of the MIT License; see LICENSE file for more details.

import React from 'react';
import { render, screen } from '@testing-library/react';
import { SingleStatUploadersCumulative } from './SingleStatUploadersCumulative';
import { useStatsDashboard } from '../../context/StatsDashboardContext';

// Mock the dependencies
jest.mock('../../context/StatsDashboardContext');

const mockUseStatsDashboard = useStatsDashboard;

describe('SingleStatUploadersCumulative', () => {
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
            recordSnapshotDataAdded: {
              global: {
                uploaders: [
                  {
                    id: 'global',
                    name: 'Global',
                  data: [
                    { value: [new Date('2024-01-01T00:00:00.000Z'), 10] },
                    { value: [new Date('2024-01-02T00:00:00.000Z'), 15] }
                  ]
                }
                ]
              }
            }
          }
        ],
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') },
        isLoading: false,
        recordStartBasis: 'added'
      });
    });

    it('should render with default title and value', () => {
      render(<SingleStatUploadersCumulative />);

      expect(screen.getByText('Cumulative Uploaders')).toBeInTheDocument();
      expect(screen.getByText('15')).toBeInTheDocument(); // Latest value in range
    });

    it('should render with custom title', () => {
      render(<SingleStatUploadersCumulative title="Custom Cumulative Uploaders" />);

      expect(screen.getByText('Custom Cumulative Uploaders')).toBeInTheDocument();
    });

    it('should display description with "as of" date', () => {
      render(<SingleStatUploadersCumulative />);

      // The description should contain "as of" and the end date
      expect(screen.getByText(/as of/)).toBeInTheDocument();
    });
  });

  describe('HTML Structure and Accessibility', () => {
    beforeEach(() => {
      mockUseStatsDashboard.mockReturnValue({
        stats: [
          {
            year: 2024,
            recordSnapshotDataAdded: {
              global: {
                uploaders: [
                  {
                    id: 'global',
                    name: 'Global',
                  data: [
                    { value: [new Date('2024-01-01T00:00:00.000Z'), 10] },
                    { value: [new Date('2024-01-02T00:00:00.000Z'), 15] }
                  ]
                }
                ]
              }
            }
          }
        ],
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') },
        isLoading: false,
        recordStartBasis: 'added'
      });
    });

    it('should have correct container structure and CSS classes', () => {
      const { container } = render(<SingleStatUploadersCumulative />);

      // Check main container
      const mainContainer = container.querySelector('.stats-single-stat-container');
      expect(mainContainer).toBeInTheDocument();
      expect(mainContainer).toHaveAttribute('role', 'region');
      expect(mainContainer).toHaveAttribute('aria-describedby');
      expect(mainContainer).toHaveAttribute('aria-label', 'Cumulative Uploaders');
    });

    it('should have correct value element structure', () => {
      const { container } = render(<SingleStatUploadersCumulative />);

      // Check value element
      const valueElement = container.querySelector('.value.stats-single-stat-value');
      expect(valueElement).toBeInTheDocument();
      expect(valueElement).toHaveAttribute('aria-label', '15 Cumulative Uploaders');
      expect(valueElement).toHaveTextContent('15');
    });

    it('should have correct header structure with icon', () => {
      const { container } = render(<SingleStatUploadersCumulative />);

      // Check header element
      const headerElement = container.querySelector('.label.stats-single-stat-header.mt-5');
      expect(headerElement).toBeInTheDocument();
      expect(headerElement).toHaveTextContent('Cumulative Uploaders');

      // Check icon
      const iconElement = headerElement.querySelector('.users.icon.mr-10');
      expect(iconElement).toBeInTheDocument();
      expect(iconElement).toHaveAttribute('aria-hidden', 'true');
    });

    it('should have correct description structure', () => {
      const { container } = render(<SingleStatUploadersCumulative />);

      // Check description element
      const descriptionElement = container.querySelector('.label.stats-single-stat-description.mt-5');
      expect(descriptionElement).toBeInTheDocument();
      expect(descriptionElement).toHaveAttribute('id');
      expect(descriptionElement).toHaveAttribute('aria-label');
      expect(descriptionElement).toHaveTextContent(/as of/);
    });

    it('should have proper accessibility attributes', () => {
      const { container } = render(<SingleStatUploadersCumulative />);

      const mainContainer = container.querySelector('.stats-single-stat-container');
      const descriptionElement = container.querySelector('.stats-single-stat-description');

      // Check that aria-describedby points to the description element
      const describedBy = mainContainer.getAttribute('aria-describedby');
      expect(describedBy).toBe(descriptionElement.getAttribute('id'));
    });

    it('should handle custom title in accessibility attributes', () => {
      const { container } = render(<SingleStatUploadersCumulative title="Custom Title" />);

      const mainContainer = container.querySelector('.stats-single-stat-container');
      const valueElement = container.querySelector('.value');

      expect(mainContainer).toHaveAttribute('aria-label', 'Custom Title');
      expect(valueElement).toHaveAttribute('aria-label', '15 Custom Title');
    });

    it('should handle custom icon', () => {
      const { container } = render(<SingleStatUploadersCumulative icon="chart bar" />);

      const iconElement = container.querySelector('.chart.bar.icon.mr-10');
      expect(iconElement).toBeInTheDocument();
      expect(iconElement).toHaveAttribute('aria-hidden', 'true');
    });
  });

  describe('Snapshot Data Handling', () => {
    it('should get the latest snapshot value within date range', () => {
      // Test data with multiple snapshot values
      mockUseStatsDashboard.mockReturnValue({
        stats: [
          {
            year: 2024,
            recordSnapshotDataAdded: {
              global: {
                uploaders: [
                  {
                    id: 'global',
                    name: 'Global',
                  data: [
                    { value: [new Date('2023-12-31T00:00:00.000Z'), 5] },   // Before range
                    { value: [new Date('2024-01-01T00:00:00.000Z'), 10] },  // In range
                    { value: [new Date('2024-01-02T00:00:00.000Z'), 15] },  // In range (latest)
                    { value: [new Date('2024-01-03T00:00:00.000Z'), 20] }   // After range
                  ]
                }
                ]
              }
            }
          }
        ],
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') },
        isLoading: false,
        recordStartBasis: 'added'
      });

      render(<SingleStatUploadersCumulative />);

      // Should show the latest snapshot value within the range: 15
      expect(screen.getByText('15')).toBeInTheDocument();
    });

    it('should handle data completely outside date range', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: [
          {
            year: 2024,
            recordSnapshotDataAdded: {
              global: {
                uploaders: [
                  {
                    id: 'global',
                    name: 'Global',
                  data: [
                    { value: [new Date('2023-12-30T00:00:00.000Z'), 5] },   // Outside range
                    { value: [new Date('2023-12-31T00:00:00.000Z'), 10] },  // Outside range
                    { value: [new Date('2024-01-03T00:00:00.000Z'), 15] },  // Outside range
                    { value: [new Date('2024-01-04T00:00:00.000Z'), 20] }   // Outside range
                  ]
                }
                ]
              }
            }
          }
        ],
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') },
        isLoading: false,
        recordStartBasis: 'added'
      });

      render(<SingleStatUploadersCumulative />);

      // Should show 0 since no data is within the date range
      expect(screen.getByText('0')).toBeInTheDocument();
    });

    it('should handle partial date ranges (only end date)', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: [
          {
            year: 2024,
            recordSnapshotDataAdded: {
              global: {
                uploaders: [
                  {
                    id: 'global',
                    name: 'Global',
                  data: [
                    { value: [new Date('2023-12-31T00:00:00.000Z'), 5] },   // Before end
                    { value: [new Date('2024-01-01T00:00:00.000Z'), 10] },  // Before end
                    { value: [new Date('2024-01-02T00:00:00.000Z'), 15] },  // On end date (latest)
                    { value: [new Date('2024-01-03T00:00:00.000Z'), 20] }   // After end
                  ]
                }
                ]
              }
            }
          }
        ],
        dateRange: { start: null, end: new Date('2024-01-02T00:00:00.000Z') },
        isLoading: false,
        recordStartBasis: 'added'
      });

      render(<SingleStatUploadersCumulative />);

      // Should show the latest value up to and including end date: 15
      expect(screen.getByText('15')).toBeInTheDocument();
    });

    it('should handle single data point in range', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: [
          {
            year: 2024,
            recordSnapshotDataAdded: {
              global: {
                uploaders: [
                  {
                    id: 'global',
                    name: 'Global',
                  data: [
                    { value: [new Date('2024-01-01T00:00:00.000Z'), 10] }  // Only one point in range
                  ]
                }
                ]
              }
            }
          }
        ],
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') },
        isLoading: false,
        recordStartBasis: 'added'
      });

      render(<SingleStatUploadersCumulative />);

      // Should show the single value: 10
      expect(screen.getByText('10')).toBeInTheDocument();
    });
  });

  describe('Different Record Bases', () => {
    it('should handle different record start basis correctly', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: [
          {
            year: 2024,
            recordSnapshotDataCreated: {
              global: {
                uploaders: [
                  {
                    id: 'global',
                    name: 'Global',
                  data: [
                    { value: [new Date('2024-01-01T00:00:00.000Z'), 10] },
                    { value: [new Date('2024-01-02T00:00:00.000Z'), 15] }
                  ]
                }
                ]
              }
            }
          }
        ],
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') },
        isLoading: false,
        recordStartBasis: 'created'
      });

      render(<SingleStatUploadersCumulative />);

      expect(screen.getByText('15')).toBeInTheDocument();
    });

    it('should handle published record basis', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: [
          {
            year: 2024,
            recordSnapshotDataPublished: {
              global: {
                uploaders: [
                  {
                    id: 'global',
                    name: 'Global',
                  data: [
                    { value: [new Date('2024-01-01T00:00:00.000Z'), 8] },
                    { value: [new Date('2024-01-02T00:00:00.000Z'), 12] }
                  ]
                }
                ]
              }
            }
          }
        ],
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') },
        isLoading: false,
        recordStartBasis: 'published'
      });

      render(<SingleStatUploadersCumulative />);

      expect(screen.getByText('12')).toBeInTheDocument();
    });
  });

  describe('Edge Cases and Error Handling', () => {
    it('should handle empty stats gracefully', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: null,
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') },
        isLoading: false,
        recordStartBasis: 'added'
      });

      render(<SingleStatUploadersCumulative />);

      expect(screen.getByText('0')).toBeInTheDocument();
    });

    it('should handle empty data array', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: [
          {
            year: 2024,
            recordSnapshotDataAdded: {
              global: {
                uploaders: [
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
        isLoading: false,
        recordStartBasis: 'added'
      });

      render(<SingleStatUploadersCumulative />);

      expect(screen.getByText('0')).toBeInTheDocument();
    });

    it('should handle missing data property', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: [
          {
            year: 2024,
            recordSnapshotDataAdded: {
              global: {
                uploaders: [
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
        isLoading: false,
        recordStartBasis: 'added'
      });

      render(<SingleStatUploadersCumulative />);

      expect(screen.getByText('0')).toBeInTheDocument();
    });

    it('should handle invalid data points', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: [
          {
            year: 2024,
            recordSnapshotDataAdded: {
              global: {
                uploaders: [
                  {
                    id: 'global',
                    name: 'Global',
                  data: [
                    { value: [new Date('2024-01-01T00:00:00.000Z'), 10] },
                    { value: null }, // Invalid data point
                    { value: [new Date('2024-01-02T00:00:00.000Z'), 15] },
                    { value: [new Date('2024-01-03T00:00:00.000Z')] }, // Missing value
                    { value: ['not a date', 20] } // Invalid date
                  ]
                }
                ]
              }
            }
          }
        ],
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') },
        isLoading: false,
        recordStartBasis: 'added'
      });

      render(<SingleStatUploadersCumulative />);

      // Should show the latest valid data point within range: 15
      expect(screen.getByText('15')).toBeInTheDocument();
    });

    it('should handle no date range', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: [
          {
            year: 2024,
            recordSnapshotDataAdded: {
              global: {
                uploaders: [
                  {
                    id: 'global',
                    name: 'Global',
                  data: [
                    { value: [new Date('2024-01-01T00:00:00.000Z'), 10] },
                    { value: [new Date('2024-01-02T00:00:00.000Z'), 15] }
                  ]
                }
                ]
              }
            }
          }
        ],
        dateRange: null,
        isLoading: false,
        recordStartBasis: 'added'
      });

      render(<SingleStatUploadersCumulative />);

      // Should show the latest value when no date range is provided: 15
      expect(screen.getByText('15')).toBeInTheDocument();
    });

    it('should handle no end date in range', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: [
          {
            year: 2024,
            recordSnapshotDataAdded: {
              global: {
                uploaders: [
                  {
                    id: 'global',
                    name: 'Global',
                  data: [
                    { value: [new Date('2024-01-01T00:00:00.000Z'), 10] },
                    { value: [new Date('2024-01-02T00:00:00.000Z'), 15] }
                  ]
                }
                ]
              }
            }
          }
        ],
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: null },
        recordStartBasis: 'added'
      });

      render(<SingleStatUploadersCumulative />);

      // Should show the latest value when no end date is provided: 15
      expect(screen.getByText('15')).toBeInTheDocument();
    });
  });
});