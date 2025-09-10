// Part of the Invenio-Stats-Dashboard extension for InvenioRDM
// Copyright (C) 2025 Mesh Research
//
// Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
// it under the terms of the MIT License; see LICENSE file for more details.

import React from 'react';
import { render, screen } from '@testing-library/react';
import { SingleStatViews } from './SingleStatViews';
import { useStatsDashboard } from '../../context/StatsDashboardContext';

// Mock the dependencies
jest.mock('../../context/StatsDashboardContext');

const mockUseStatsDashboard = useStatsDashboard;

describe('SingleStatViews', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('Basic Rendering', () => {
    beforeEach(() => {
      mockUseStatsDashboard.mockReturnValue({
        stats: {
          usageDeltaData: {
            global: {
              views: [
                {
                  id: 'views',
                  name: 'Views',
                  data: [
                    { value: [new Date('2024-01-01T00:00:00.000Z'), 10] },
                    { value: [new Date('2024-01-02T00:00:00.000Z'), 20] }
                  ]
                }
              ]
            }
          }
        },
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') }
      });
    });

    it('should render with default title and value', () => {
      render(<SingleStatViews />);

      expect(screen.getByText('Views')).toBeInTheDocument();
      expect(screen.getByText('30')).toBeInTheDocument(); // 10 + 20 = 30
    });

    it('should render with custom title', () => {
      render(<SingleStatViews title="Custom Views" />);

      expect(screen.getByText('Custom Views')).toBeInTheDocument();
    });

    it('should display description with date range', () => {
      render(<SingleStatViews />);

      // The description should contain the date range
      expect(screen.getByText(/from/)).toBeInTheDocument();
      expect(screen.getByText(/to/)).toBeInTheDocument();
    });
  });

  describe('HTML Structure and Accessibility', () => {
    beforeEach(() => {
      mockUseStatsDashboard.mockReturnValue({
        stats: {
          usageDeltaData: {
            global: {
              views: [
                {
                  id: 'views',
                  name: 'Views',
                  data: [
                    { value: [new Date('2024-01-01T00:00:00.000Z'), 10] },
                    { value: [new Date('2024-01-02T00:00:00.000Z'), 20] }
                  ]
                }
              ]
            }
          }
        },
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') }
      });
    });

    it('should have correct container structure and CSS classes', () => {
      const { container } = render(<SingleStatViews />);

      // Check main container
      const mainContainer = container.querySelector('.ui.statistic.stats-single-stat-container.centered.rel-mb-2.rel-mt-2');
      expect(mainContainer).toBeInTheDocument();
      expect(mainContainer).toHaveAttribute('role', 'region');
      expect(mainContainer).toHaveAttribute('aria-describedby');
      expect(mainContainer).toHaveAttribute('aria-label', 'Views');
    });

    it('should have correct value element structure', () => {
      const { container } = render(<SingleStatViews />);

      // Check value element
      const valueElement = container.querySelector('.value.stats-single-stat-value');
      expect(valueElement).toBeInTheDocument();
      expect(valueElement).toHaveAttribute('aria-label', '30 Views');
      expect(valueElement).toHaveTextContent('30');
    });

    it('should have correct header structure with icon', () => {
      const { container } = render(<SingleStatViews />);

      // Check header element
      const headerElement = container.querySelector('.label.stats-single-stat-header.mt-5');
      expect(headerElement).toBeInTheDocument();
      expect(headerElement).toHaveTextContent('Views');

      // Check icon
      const iconElement = headerElement.querySelector('.eye.icon.mr-10');
      expect(iconElement).toBeInTheDocument();
      expect(iconElement).toHaveAttribute('aria-hidden', 'true');
    });

    it('should have correct description structure', () => {
      const { container } = render(<SingleStatViews />);

      // Check description element
      const descriptionElement = container.querySelector('.label.stats-single-stat-description.mt-5');
      expect(descriptionElement).toBeInTheDocument();
      expect(descriptionElement).toHaveAttribute('id');
      expect(descriptionElement).toHaveAttribute('aria-label');
      expect(descriptionElement).toHaveTextContent(/from/);
    });

    it('should have proper accessibility attributes', () => {
      const { container } = render(<SingleStatViews />);

      const mainContainer = container.querySelector('.ui.statistic');
      const descriptionElement = container.querySelector('.stats-single-stat-description');

      // Check that aria-describedby points to the description element
      const describedBy = mainContainer.getAttribute('aria-describedby');
      expect(describedBy).toBe(descriptionElement.getAttribute('id'));
    });

    it('should handle custom title in accessibility attributes', () => {
      const { container } = render(<SingleStatViews title="Custom Title" />);

      const mainContainer = container.querySelector('.ui.statistic');
      const valueElement = container.querySelector('.value');

      expect(mainContainer).toHaveAttribute('aria-label', 'Custom Title');
      expect(valueElement).toHaveAttribute('aria-label', '30 Custom Title');
    });

    it('should handle custom icon', () => {
      const { container } = render(<SingleStatViews icon="chart bar" />);

      const iconElement = container.querySelector('.chart.bar.icon.mr-10');
      expect(iconElement).toBeInTheDocument();
      expect(iconElement).toHaveAttribute('aria-hidden', 'true');
    });
  });

  describe('Date Filtering and Cumulative Totaling', () => {
    it('should filter data by date range and sum values correctly', () => {
      // Test data with values inside and outside the date range
      mockUseStatsDashboard.mockReturnValue({
        stats: {
          usageDeltaData: {
            global: {
              views: [
                {
                  id: 'views',
                  name: 'Views',
                  data: [
                    { value: [new Date('2023-12-31T00:00:00.000Z'), 5] },  // Outside range
                    { value: [new Date('2024-01-01T00:00:00.000Z'), 10] }, // Inside range
                    { value: [new Date('2024-01-02T00:00:00.000Z'), 15] }, // Inside range
                    { value: [new Date('2024-01-03T00:00:00.000Z'), 20] }  // Outside range
                  ]
                }
              ]
            }
          }
        },
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') }
      });

      render(<SingleStatViews />);

      // Should only sum values within the date range: 10 + 15 = 25
      expect(screen.getByText('25')).toBeInTheDocument();
    });

    it('should handle data completely outside date range', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: {
          usageDeltaData: {
            global: {
              views: [
                {
                  id: 'views',
                  name: 'Views',
                  data: [
                    { value: [new Date('2023-12-30T00:00:00.000Z'), 5] },  // Outside range
                    { value: [new Date('2023-12-31T00:00:00.000Z'), 10] }, // Outside range
                    { value: [new Date('2024-01-03T00:00:00.000Z'), 15] }, // Outside range
                    { value: [new Date('2024-01-04T00:00:00.000Z'), 20] }  // Outside range
                  ]
                }
              ]
            }
          }
        },
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') }
      });

      render(<SingleStatViews />);

      // Should show 0 since no data is within the date range
      expect(screen.getByText('0')).toBeInTheDocument();
    });

    it('should handle partial date ranges (only start date)', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: {
          usageDeltaData: {
            global: {
              views: [
                {
                  id: 'views',
                  name: 'Views',
                  data: [
                    { value: [new Date('2023-12-31T00:00:00.000Z'), 5] },  // Before start
                    { value: [new Date('2024-01-01T00:00:00.000Z'), 10] }, // On start date
                    { value: [new Date('2024-01-02T00:00:00.000Z'), 15] }, // After start
                    { value: [new Date('2024-01-03T00:00:00.000Z'), 20] }  // After start
                  ]
                }
              ]
            }
          }
        },
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: null }
      });

      render(<SingleStatViews />);

      // Should include all data from start date onwards: 10 + 15 + 20 = 45
      expect(screen.getByText('45')).toBeInTheDocument();
    });

    it('should handle partial date ranges (only end date)', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: {
          usageDeltaData: {
            global: {
              views: [
                {
                  id: 'views',
                  name: 'Views',
                  data: [
                    { value: [new Date('2023-12-31T00:00:00.000Z'), 5] },  // Before end
                    { value: [new Date('2024-01-01T00:00:00.000Z'), 10] }, // Before end
                    { value: [new Date('2024-01-02T00:00:00.000Z'), 15] }, // On end date
                    { value: [new Date('2024-01-03T00:00:00.000Z'), 20] }  // After end
                  ]
                }
              ]
            }
          }
        },
        dateRange: { start: null, end: new Date('2024-01-02T00:00:00.000Z') }
      });

      render(<SingleStatViews />);

      // Should include all data up to and including end date: 5 + 10 + 15 = 30
      expect(screen.getByText('30')).toBeInTheDocument();
    });
  });

  describe('Edge Cases and Error Handling', () => {
    it('should handle empty stats gracefully', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: null,
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') }
      });

      render(<SingleStatViews />);

      expect(screen.getByText('0')).toBeInTheDocument();
    });

    it('should handle empty data array', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: {
          usageDeltaData: {
            global: {
              views: [
                {
                  id: 'views',
                  name: 'Views',
                  data: []
                }
              ]
            }
          }
        },
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') }
      });

      render(<SingleStatViews />);

      expect(screen.getByText('0')).toBeInTheDocument();
    });

    it('should handle missing data property', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: {
          usageDeltaData: {
            global: {
              views: [
                {
                  id: 'views',
                  name: 'Views'
                  // Missing data property
                }
              ]
            }
          }
        },
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') }
      });

      render(<SingleStatViews />);

      expect(screen.getByText('0')).toBeInTheDocument();
    });

    it('should handle invalid data points', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: {
          usageDeltaData: {
            global: {
              views: [
                {
                  id: 'views',
                  name: 'Views',
                  data: [
                    { value: [new Date('2024-01-01T00:00:00.000Z'), 10] },
                    { value: null }, // Invalid data point
                    { value: [new Date('2024-01-02T00:00:00.000Z'), 20] },
                    { value: [new Date('2024-01-03T00:00:00.000Z')] }, // Missing value
                    { value: ['not a date', 30] } // Invalid date
                  ]
                }
              ]
            }
          }
        },
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') }
      });

      render(<SingleStatViews />);

      // Should only sum valid data points within range: 10 + 20 = 30
      expect(screen.getByText('30')).toBeInTheDocument();
    });

    it('should handle no date range', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: {
          usageDeltaData: {
            global: {
              views: [
                {
                  id: 'views',
                  name: 'Views',
                  data: [
                    { value: [new Date('2024-01-01T00:00:00.000Z'), 10] },
                    { value: [new Date('2024-01-02T00:00:00.000Z'), 20] }
                  ]
                }
              ]
            }
          }
        },
        dateRange: null
      });

      render(<SingleStatViews />);

      // Should sum all data when no date range is provided: 10 + 20 = 30
      expect(screen.getByText('30')).toBeInTheDocument();
    });
  });
});