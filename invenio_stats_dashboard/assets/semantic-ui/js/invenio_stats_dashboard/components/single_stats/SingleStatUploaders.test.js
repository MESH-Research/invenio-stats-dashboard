import React from 'react';
import { render, screen } from '@testing-library/react';
import { SingleStatUploaders } from './SingleStatUploaders';
import { useStatsDashboard } from '../../context/StatsDashboardContext';

// Mock the dependencies
jest.mock('../../context/StatsDashboardContext');

const mockUseStatsDashboard = useStatsDashboard;

describe('SingleStatUploaders', () => {
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
          recordDeltaDataAdded: {
            global: {
              uploaders: [
                {
                  id: 'uploaders',
                  name: 'Uploaders',
                  data: [
                    { value: [new Date('2024-01-01T00:00:00.000Z'), 5] },
                    { value: [new Date('2024-01-02T00:00:00.000Z'), 3] }
                  ]
                }
              ]
            }
          }
        },
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') },
        recordStartBasis: 'added'
      });
    });

    it('should render with default title and value', () => {
      render(<SingleStatUploaders />);

      expect(screen.getByText('Uploaders')).toBeInTheDocument();
      expect(screen.getByText('8')).toBeInTheDocument(); // 5 + 3 = 8
    });

    it('should render with custom title', () => {
      render(<SingleStatUploaders title="Custom Uploaders" />);

      expect(screen.getByText('Custom Uploaders')).toBeInTheDocument();
    });

    it('should display description with date range', () => {
      render(<SingleStatUploaders />);

      // The description should contain the date range
      expect(screen.getByText(/from/)).toBeInTheDocument();
      expect(screen.getByText(/to/)).toBeInTheDocument();
    });
  });

  describe('HTML Structure and Accessibility', () => {
    beforeEach(() => {
      mockUseStatsDashboard.mockReturnValue({
        stats: {
          recordDeltaDataAdded: {
            global: {
              uploaders: [
                {
                  id: 'uploaders',
                  name: 'Uploaders',
                  data: [
                    { value: [new Date('2024-01-01T00:00:00.000Z'), 5] },
                    { value: [new Date('2024-01-02T00:00:00.000Z'), 3] }
                  ]
                }
              ]
            }
          }
        },
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') },
        recordStartBasis: 'added'
      });
    });

    it('should have correct container structure and CSS classes', () => {
      const { container } = render(<SingleStatUploaders />);

      // Check main container
      const mainContainer = container.querySelector('.ui.statistic.stats-single-stat-container.centered.rel-mb-2.rel-mt-2');
      expect(mainContainer).toBeInTheDocument();
      expect(mainContainer).toHaveAttribute('role', 'region');
      expect(mainContainer).toHaveAttribute('aria-describedby');
      expect(mainContainer).toHaveAttribute('aria-label', 'Uploaders');
    });

    it('should have correct value element structure', () => {
      const { container } = render(<SingleStatUploaders />);

      // Check value element
      const valueElement = container.querySelector('.value.stats-single-stat-value');
      expect(valueElement).toBeInTheDocument();
      expect(valueElement).toHaveAttribute('aria-label', '8 Uploaders');
      expect(valueElement).toHaveTextContent('8');
    });

    it('should have correct header structure with icon', () => {
      const { container } = render(<SingleStatUploaders />);

      // Check header element
      const headerElement = container.querySelector('.label.stats-single-stat-header.mt-5');
      expect(headerElement).toBeInTheDocument();
      expect(headerElement).toHaveTextContent('Uploaders');

      // Check icon
      const iconElement = headerElement.querySelector('.users.icon.mr-10');
      expect(iconElement).toBeInTheDocument();
      expect(iconElement).toHaveAttribute('aria-hidden', 'true');
    });

    it('should have correct description structure', () => {
      const { container } = render(<SingleStatUploaders />);

      // Check description element
      const descriptionElement = container.querySelector('.label.stats-single-stat-description.mt-5');
      expect(descriptionElement).toBeInTheDocument();
      expect(descriptionElement).toHaveAttribute('id');
      expect(descriptionElement).toHaveAttribute('aria-label');
      expect(descriptionElement).toHaveTextContent(/from/);
    });

    it('should have proper accessibility attributes', () => {
      const { container } = render(<SingleStatUploaders />);

      const mainContainer = container.querySelector('.ui.statistic');
      const descriptionElement = container.querySelector('.stats-single-stat-description');

      // Check that aria-describedby points to the description element
      const describedBy = mainContainer.getAttribute('aria-describedby');
      expect(describedBy).toBe(descriptionElement.getAttribute('id'));
    });

    it('should handle custom title in accessibility attributes', () => {
      const { container } = render(<SingleStatUploaders title="Custom Title" />);

      const mainContainer = container.querySelector('.ui.statistic');
      const valueElement = container.querySelector('.value');

      expect(mainContainer).toHaveAttribute('aria-label', 'Custom Title');
      expect(valueElement).toHaveAttribute('aria-label', '8 Custom Title');
    });

    it('should handle custom icon', () => {
      const { container } = render(<SingleStatUploaders icon="chart bar" />);

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
          recordDeltaDataAdded: {
            global: {
              uploaders: [
                {
                  id: 'uploaders',
                  name: 'Uploaders',
                  data: [
                    { value: [new Date('2023-12-31T00:00:00.000Z'), 2] },  // Outside range
                    { value: [new Date('2024-01-01T00:00:00.000Z'), 5] },  // Inside range
                    { value: [new Date('2024-01-02T00:00:00.000Z'), 3] },  // Inside range
                    { value: [new Date('2024-01-03T00:00:00.000Z'), 7] }   // Outside range
                  ]
                }
              ]
            }
          }
        },
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') },
        recordStartBasis: 'added'
      });

      render(<SingleStatUploaders />);

      // Should only sum values within the date range: 5 + 3 = 8
      expect(screen.getByText('8')).toBeInTheDocument();
    });

    it('should handle data completely outside date range', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: {
          recordDeltaDataAdded: {
            global: {
              uploaders: [
                {
                  id: 'uploaders',
                  name: 'Uploaders',
                  data: [
                    { value: [new Date('2023-12-30T00:00:00.000Z'), 2] },  // Outside range
                    { value: [new Date('2023-12-31T00:00:00.000Z'), 5] },  // Outside range
                    { value: [new Date('2024-01-03T00:00:00.000Z'), 3] },  // Outside range
                    { value: [new Date('2024-01-04T00:00:00.000Z'), 7] }   // Outside range
                  ]
                }
              ]
            }
          }
        },
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') },
        recordStartBasis: 'added'
      });

      render(<SingleStatUploaders />);

      // Should show 0 since no data is within the date range
      expect(screen.getByText('0')).toBeInTheDocument();
    });

    it('should handle partial date ranges (only start date)', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: {
          recordDeltaDataAdded: {
            global: {
              uploaders: [
                {
                  id: 'uploaders',
                  name: 'Uploaders',
                  data: [
                    { value: [new Date('2023-12-31T00:00:00.000Z'), 2] },  // Before start
                    { value: [new Date('2024-01-01T00:00:00.000Z'), 5] },  // On start date
                    { value: [new Date('2024-01-02T00:00:00.000Z'), 3] },  // After start
                    { value: [new Date('2024-01-03T00:00:00.000Z'), 7] }   // After start
                  ]
                }
              ]
            }
          }
        },
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: null },
        recordStartBasis: 'added'
      });

      render(<SingleStatUploaders />);

      // Should include all data from start date onwards: 5 + 3 + 7 = 15
      expect(screen.getByText('15')).toBeInTheDocument();
    });
  });

  describe('Different Record Bases', () => {
    it('should handle different record start basis correctly', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: {
          recordDeltaDataCreated: {
            global: {
              uploaders: [
                {
                  id: 'uploaders',
                  name: 'Uploaders',
                  data: [
                    { value: [new Date('2024-01-01T00:00:00.000Z'), 5] },
                    { value: [new Date('2024-01-02T00:00:00.000Z'), 3] }
                  ]
                }
              ]
            }
          }
        },
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') },
        recordStartBasis: 'created'
      });

      render(<SingleStatUploaders />);

      expect(screen.getByText('8')).toBeInTheDocument();
    });

    it('should handle published record basis', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: {
          recordDeltaDataPublished: {
            global: {
              uploaders: [
                {
                  id: 'uploaders',
                  name: 'Uploaders',
                  data: [
                    { value: [new Date('2024-01-01T00:00:00.000Z'), 3] },
                    { value: [new Date('2024-01-02T00:00:00.000Z'), 4] }
                  ]
                }
              ]
            }
          }
        },
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') },
        recordStartBasis: 'published'
      });

      render(<SingleStatUploaders />);

      expect(screen.getByText('7')).toBeInTheDocument(); // 3 + 4 = 7
    });
  });

  describe('Edge Cases and Error Handling', () => {
    it('should handle empty stats gracefully', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: null,
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') },
        recordStartBasis: 'added'
      });

      render(<SingleStatUploaders />);

      expect(screen.getByText('0')).toBeInTheDocument();
    });

    it('should handle empty data array', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: {
          recordDeltaDataAdded: {
            global: {
              uploaders: [
                {
                  id: 'uploaders',
                  name: 'Uploaders',
                  data: []
                }
              ]
            }
          }
        },
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') },
        recordStartBasis: 'added'
      });

      render(<SingleStatUploaders />);

      expect(screen.getByText('0')).toBeInTheDocument();
    });

    it('should handle missing data property', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: {
          recordDeltaDataAdded: {
            global: {
              uploaders: [
                {
                  id: 'uploaders',
                  name: 'Uploaders'
                  // Missing data property
                }
              ]
            }
          }
        },
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') },
        recordStartBasis: 'added'
      });

      render(<SingleStatUploaders />);

      expect(screen.getByText('0')).toBeInTheDocument();
    });

    it('should handle invalid data points', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: {
          recordDeltaDataAdded: {
            global: {
              uploaders: [
                {
                  id: 'uploaders',
                  name: 'Uploaders',
                  data: [
                    { value: [new Date('2024-01-01T00:00:00.000Z'), 5] },
                    { value: null }, // Invalid data point
                    { value: [new Date('2024-01-02T00:00:00.000Z'), 3] },
                    { value: [new Date('2024-01-03T00:00:00.000Z')] }, // Missing value
                    { value: ['not a date', 7] } // Invalid date
                  ]
                }
              ]
            }
          }
        },
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') },
        recordStartBasis: 'added'
      });

      render(<SingleStatUploaders />);

      // Should only sum valid data points within range: 5 + 3 = 8
      expect(screen.getByText('8')).toBeInTheDocument();
    });

    it('should handle no date range', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: {
          recordDeltaDataAdded: {
            global: {
              uploaders: [
                {
                  id: 'uploaders',
                  name: 'Uploaders',
                  data: [
                    { value: [new Date('2024-01-01T00:00:00.000Z'), 5] },
                    { value: [new Date('2024-01-02T00:00:00.000Z'), 3] }
                  ]
                }
              ]
            }
          }
        },
        dateRange: null,
        recordStartBasis: 'added'
      });

      render(<SingleStatUploaders />);

      // Should sum all data when no date range is provided: 5 + 3 = 8
      expect(screen.getByText('8')).toBeInTheDocument();
    });
  });
});