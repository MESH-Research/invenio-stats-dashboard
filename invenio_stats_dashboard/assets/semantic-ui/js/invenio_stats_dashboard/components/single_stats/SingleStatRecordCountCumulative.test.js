import React from 'react';
import { render, screen } from '@testing-library/react';
import { SingleStatRecordCountCumulative } from './SingleStatRecordCountCumulative';
import { useStatsDashboard } from '../../context/StatsDashboardContext';

// Mock the dependencies
jest.mock('../../context/StatsDashboardContext');

const mockUseStatsDashboard = useStatsDashboard;

describe('SingleStatRecordCountCumulative', () => {
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
          recordSnapshotDataAdded: {
            global: {
              records: [
                {
                  id: 'records',
                  name: 'Records',
                  data: [
                    { value: [new Date('2024-01-01T00:00:00.000Z'), 100] },
                    { value: [new Date('2024-01-02T00:00:00.000Z'), 150] }
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
      render(<SingleStatRecordCountCumulative />);

      expect(screen.getByText('Cumulative Records')).toBeInTheDocument();
      expect(screen.getByText('150')).toBeInTheDocument(); // Latest value in range
    });

    it('should render with custom title', () => {
      render(<SingleStatRecordCountCumulative title="Custom Cumulative Records" />);

      expect(screen.getByText('Custom Cumulative Records')).toBeInTheDocument();
    });

    it('should display description with "as of" date', () => {
      render(<SingleStatRecordCountCumulative />);

      // The description should contain "as of" and the end date
      expect(screen.getByText(/as of/)).toBeInTheDocument();
    });
  });

  describe('HTML Structure and Accessibility', () => {
    beforeEach(() => {
      mockUseStatsDashboard.mockReturnValue({
        stats: {
          recordSnapshotDataAdded: {
            global: {
              records: [
                {
                  id: 'records',
                  name: 'Records',
                  data: [
                    { value: [new Date('2024-01-01T00:00:00.000Z'), 100] },
                    { value: [new Date('2024-01-02T00:00:00.000Z'), 150] }
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
      const { container } = render(<SingleStatRecordCountCumulative />);

      // Check main container
      const mainContainer = container.querySelector('.ui.statistic.stats-single-stat-container.centered.rel-mb-2.rel-mt-2');
      expect(mainContainer).toBeInTheDocument();
      expect(mainContainer).toHaveAttribute('role', 'region');
      expect(mainContainer).toHaveAttribute('aria-describedby');
      expect(mainContainer).toHaveAttribute('aria-label', 'Cumulative Records');
    });

    it('should have correct value element structure', () => {
      const { container } = render(<SingleStatRecordCountCumulative />);

      // Check value element
      const valueElement = container.querySelector('.value.stats-single-stat-value');
      expect(valueElement).toBeInTheDocument();
      expect(valueElement).toHaveAttribute('aria-label', '150 Cumulative Records');
      expect(valueElement).toHaveTextContent('150');
    });

    it('should have correct header structure with icon', () => {
      const { container } = render(<SingleStatRecordCountCumulative />);

      // Check header element
      const headerElement = container.querySelector('.label.stats-single-stat-header.mt-5');
      expect(headerElement).toBeInTheDocument();
      expect(headerElement).toHaveTextContent('Cumulative Records');

      // Check icon
      const iconElement = headerElement.querySelector('.file.alternate.icon.mr-10');
      expect(iconElement).toBeInTheDocument();
      expect(iconElement).toHaveAttribute('aria-hidden', 'true');
    });

    it('should have correct description structure', () => {
      const { container } = render(<SingleStatRecordCountCumulative />);

      // Check description element
      const descriptionElement = container.querySelector('.label.stats-single-stat-description.mt-5');
      expect(descriptionElement).toBeInTheDocument();
      expect(descriptionElement).toHaveAttribute('id');
      expect(descriptionElement).toHaveAttribute('aria-label');
      expect(descriptionElement).toHaveTextContent(/as of/);
    });

    it('should have proper accessibility attributes', () => {
      const { container } = render(<SingleStatRecordCountCumulative />);

      const mainContainer = container.querySelector('.ui.statistic');
      const descriptionElement = container.querySelector('.stats-single-stat-description');

      // Check that aria-describedby points to the description element
      const describedBy = mainContainer.getAttribute('aria-describedby');
      expect(describedBy).toBe(descriptionElement.getAttribute('id'));
    });

    it('should handle custom title in accessibility attributes', () => {
      const { container } = render(<SingleStatRecordCountCumulative title="Custom Title" />);

      const mainContainer = container.querySelector('.ui.statistic');
      const valueElement = container.querySelector('.value');

      expect(mainContainer).toHaveAttribute('aria-label', 'Custom Title');
      expect(valueElement).toHaveAttribute('aria-label', '150 Custom Title');
    });

    it('should handle custom icon', () => {
      const { container } = render(<SingleStatRecordCountCumulative icon="chart bar" />);

      const iconElement = container.querySelector('.chart.bar.icon.mr-10');
      expect(iconElement).toBeInTheDocument();
      expect(iconElement).toHaveAttribute('aria-hidden', 'true');
    });
  });

  describe('Snapshot Data Handling', () => {
    it('should get the latest snapshot value within date range', () => {
      // Test data with multiple snapshot values
      mockUseStatsDashboard.mockReturnValue({
        stats: {
          recordSnapshotDataAdded: {
            global: {
              records: [
                {
                  id: 'records',
                  name: 'Records',
                  data: [
                    { value: [new Date('2023-12-31T00:00:00.000Z'), 50] },  // Before range
                    { value: [new Date('2024-01-01T00:00:00.000Z'), 100] }, // In range
                    { value: [new Date('2024-01-02T00:00:00.000Z'), 150] }, // In range (latest)
                    { value: [new Date('2024-01-03T00:00:00.000Z'), 200] }  // After range
                  ]
                }
              ]
            }
          }
        },
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') },
        recordStartBasis: 'added'
      });

      render(<SingleStatRecordCountCumulative />);

      // Should show the latest snapshot value within the range: 150
      expect(screen.getByText('150')).toBeInTheDocument();
    });

    it('should handle data completely outside date range', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: {
          recordSnapshotDataAdded: {
            global: {
              records: [
                {
                  id: 'records',
                  name: 'Records',
                  data: [
                    { value: [new Date('2023-12-30T00:00:00.000Z'), 50] },  // Outside range
                    { value: [new Date('2023-12-31T00:00:00.000Z'), 100] }, // Outside range
                    { value: [new Date('2024-01-03T00:00:00.000Z'), 150] }, // Outside range
                    { value: [new Date('2024-01-04T00:00:00.000Z'), 200] }  // Outside range
                  ]
                }
              ]
            }
          }
        },
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') },
        recordStartBasis: 'added'
      });

      render(<SingleStatRecordCountCumulative />);

      // Should show 0 since no data is within the date range
      expect(screen.getByText('0')).toBeInTheDocument();
    });

    it('should handle partial date ranges (only end date)', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: {
          recordSnapshotDataAdded: {
            global: {
              records: [
                {
                  id: 'records',
                  name: 'Records',
                  data: [
                    { value: [new Date('2023-12-31T00:00:00.000Z'), 50] },  // Before end
                    { value: [new Date('2024-01-01T00:00:00.000Z'), 100] }, // Before end
                    { value: [new Date('2024-01-02T00:00:00.000Z'), 150] }, // On end date (latest)
                    { value: [new Date('2024-01-03T00:00:00.000Z'), 200] }  // After end
                  ]
                }
              ]
            }
          }
        },
        dateRange: { start: null, end: new Date('2024-01-02T00:00:00.000Z') },
        recordStartBasis: 'added'
      });

      render(<SingleStatRecordCountCumulative />);

      // Should show the latest value up to and including end date: 150
      expect(screen.getByText('150')).toBeInTheDocument();
    });

    it('should handle single data point in range', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: {
          recordSnapshotDataAdded: {
            global: {
              records: [
                {
                  id: 'records',
                  name: 'Records',
                  data: [
                    { value: [new Date('2024-01-01T00:00:00.000Z'), 100] }  // Only one point in range
                  ]
                }
              ]
            }
          }
        },
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') },
        recordStartBasis: 'added'
      });

      render(<SingleStatRecordCountCumulative />);

      // Should show the single value: 100
      expect(screen.getByText('100')).toBeInTheDocument();
    });
  });

  describe('Different Record Bases', () => {
    it('should handle different record start basis correctly', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: {
          recordSnapshotDataCreated: {
            global: {
              records: [
                {
                  id: 'records',
                  name: 'Records',
                  data: [
                    { value: [new Date('2024-01-01T00:00:00.000Z'), 100] },
                    { value: [new Date('2024-01-02T00:00:00.000Z'), 150] }
                  ]
                }
              ]
            }
          }
        },
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') },
        recordStartBasis: 'created'
      });

      render(<SingleStatRecordCountCumulative />);

      expect(screen.getByText('150')).toBeInTheDocument();
    });

    it('should handle published record basis', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: {
          recordSnapshotDataPublished: {
            global: {
              records: [
                {
                  id: 'records',
                  name: 'Records',
                  data: [
                    { value: [new Date('2024-01-01T00:00:00.000Z'), 75] },
                    { value: [new Date('2024-01-02T00:00:00.000Z'), 125] }
                  ]
                }
              ]
            }
          }
        },
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') },
        recordStartBasis: 'published'
      });

      render(<SingleStatRecordCountCumulative />);

      expect(screen.getByText('125')).toBeInTheDocument();
    });
  });

  describe('Edge Cases and Error Handling', () => {
    it('should handle empty stats gracefully', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: null,
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') },
        recordStartBasis: 'added'
      });

      render(<SingleStatRecordCountCumulative />);

      expect(screen.getByText('0')).toBeInTheDocument();
    });

    it('should handle empty data array', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: {
          recordSnapshotDataAdded: {
            global: {
              records: [
                {
                  id: 'records',
                  name: 'Records',
                  data: []
                }
              ]
            }
          }
        },
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') },
        recordStartBasis: 'added'
      });

      render(<SingleStatRecordCountCumulative />);

      expect(screen.getByText('0')).toBeInTheDocument();
    });

    it('should handle missing data property', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: {
          recordSnapshotDataAdded: {
            global: {
              records: [
                {
                  id: 'records',
                  name: 'Records'
                  // Missing data property
                }
              ]
            }
          }
        },
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') },
        recordStartBasis: 'added'
      });

      render(<SingleStatRecordCountCumulative />);

      expect(screen.getByText('0')).toBeInTheDocument();
    });

    it('should handle invalid data points', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: {
          recordSnapshotDataAdded: {
            global: {
              records: [
                {
                  id: 'records',
                  name: 'Records',
                  data: [
                    { value: [new Date('2024-01-01T00:00:00.000Z'), 100] },
                    { value: null }, // Invalid data point
                    { value: [new Date('2024-01-02T00:00:00.000Z'), 150] },
                    { value: [new Date('2024-01-03T00:00:00.000Z')] }, // Missing value
                    { value: ['not a date', 200] } // Invalid date
                  ]
                }
              ]
            }
          }
        },
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') },
        recordStartBasis: 'added'
      });

      render(<SingleStatRecordCountCumulative />);

      // Should show the latest valid data point within range: 150
      expect(screen.getByText('150')).toBeInTheDocument();
    });

    it('should handle no date range', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: {
          recordSnapshotDataAdded: {
            global: {
              records: [
                {
                  id: 'records',
                  name: 'Records',
                  data: [
                    { value: [new Date('2024-01-01T00:00:00.000Z'), 100] },
                    { value: [new Date('2024-01-02T00:00:00.000Z'), 150] }
                  ]
                }
              ]
            }
          }
        },
        dateRange: null,
        recordStartBasis: 'added'
      });

      render(<SingleStatRecordCountCumulative />);

      // Should show the latest value when no date range is provided: 150
      expect(screen.getByText('150')).toBeInTheDocument();
    });

    it('should handle no end date in range', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: {
          recordSnapshotDataAdded: {
            global: {
              records: [
                {
                  id: 'records',
                  name: 'Records',
                  data: [
                    { value: [new Date('2024-01-01T00:00:00.000Z'), 100] },
                    { value: [new Date('2024-01-02T00:00:00.000Z'), 150] }
                  ]
                }
              ]
            }
          }
        },
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: null },
        recordStartBasis: 'added'
      });

      render(<SingleStatRecordCountCumulative />);

      // When end date is null, it should use the end of current day
      // and show the latest value within the range: 150
      expect(screen.getByText('150')).toBeInTheDocument();
    });
  });
});