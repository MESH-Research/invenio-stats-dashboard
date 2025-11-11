// Part of the Invenio-Stats-Dashboard extension for InvenioRDM
// Copyright (C) 2025 Mesh Research
//
// Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
// it under the terms of the MIT License; see LICENSE file for more details.

import React from 'react';
import { render, screen } from '@testing-library/react';
import { SingleStatDownloadsCumulative } from './SingleStatDownloadsCumulative';
import { useStatsDashboard } from '../../context/StatsDashboardContext';

// Mock the dependencies
jest.mock('../../context/StatsDashboardContext');

const mockUseStatsDashboard = useStatsDashboard;

describe('SingleStatDownloadsCumulative', () => {
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
            usageSnapshotData: {
              global: {
                downloads: [
                  {
                    id: 'global',
                    name: 'Global',
                    year: 2024,
                    data: [
                      ['01-02', 30]
                    ]
                  }
                ]
              }
            }
          }
        ],
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') },
        isLoading: false
      });
    });

    it('should render with default title and value', () => {
      render(<SingleStatDownloadsCumulative />);

      expect(screen.getByText('Cumulative Downloads')).toBeInTheDocument();
      expect(screen.getByText('30')).toBeInTheDocument();
    });

    it('should render with custom title', () => {
      render(<SingleStatDownloadsCumulative title="Custom Cumulative Downloads" />);

      expect(screen.getByText('Custom Cumulative Downloads')).toBeInTheDocument();
    });

    it('should display description with "as of" date', () => {
      render(<SingleStatDownloadsCumulative />);

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
            usageSnapshotData: {
              global: {
                downloads: [
                  {
                    id: 'global',
                    name: 'Global',
                    year: 2024,
                    data: [
                      ['01-02', 30]
                    ]
                  }
                ]
              }
            }
          }
        ],
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') },
        isLoading: false
      });
    });

    it('should have correct container structure and CSS classes', () => {
      const { container } = render(<SingleStatDownloadsCumulative />);

      // Check main container
      const mainContainer = container.querySelector('.stats-single-stat-container');
      expect(mainContainer).toBeInTheDocument();
      expect(mainContainer).toHaveAttribute('role', 'region');
      expect(mainContainer).toHaveAttribute('aria-describedby');
      expect(mainContainer).toHaveAttribute('aria-label', 'Cumulative Downloads');
    });

    it('should have correct value element structure', () => {
      const { container } = render(<SingleStatDownloadsCumulative />);

      // Check value element
      const valueElement = container.querySelector('.value.stats-single-stat-value');
      expect(valueElement).toBeInTheDocument();
      expect(valueElement).toHaveAttribute('aria-label', '30 Cumulative Downloads');
      expect(valueElement).toHaveTextContent('30');
    });

    it('should have correct header structure with icon', () => {
      const { container } = render(<SingleStatDownloadsCumulative />);

      // Check header element
      const headerElement = container.querySelector('.label.stats-single-stat-header.mt-5');
      expect(headerElement).toBeInTheDocument();
      expect(headerElement).toHaveTextContent('Cumulative Downloads');

      // Check icon
      const iconElement = headerElement.querySelector('.download.icon.mr-10');
      expect(iconElement).toBeInTheDocument();
      expect(iconElement).toHaveAttribute('aria-hidden', 'true');
    });

    it('should have correct description structure', () => {
      const { container } = render(<SingleStatDownloadsCumulative />);

      // Check description element
      const descriptionElement = container.querySelector('.label.stats-single-stat-description.mt-5');
      expect(descriptionElement).toBeInTheDocument();
      expect(descriptionElement).toHaveAttribute('id');
      expect(descriptionElement).toHaveAttribute('aria-label');
      expect(descriptionElement).toHaveTextContent(/as of/);
    });

    it('should have proper accessibility attributes', () => {
      const { container } = render(<SingleStatDownloadsCumulative />);

      const mainContainer = container.querySelector('.stats-single-stat-container');
      const descriptionElement = container.querySelector('.stats-single-stat-description');

      // Check that aria-describedby points to the description element
      const describedBy = mainContainer.getAttribute('aria-describedby');
      expect(describedBy).toBe(descriptionElement.getAttribute('id'));
    });

    it('should handle custom title in accessibility attributes', () => {
      const { container } = render(<SingleStatDownloadsCumulative title="Custom Title" />);

      const mainContainer = container.querySelector('.stats-single-stat-container');
      const valueElement = container.querySelector('.value');

      expect(mainContainer).toHaveAttribute('aria-label', 'Custom Title');
      expect(valueElement).toHaveAttribute('aria-label', '30 Custom Title');
    });

    it('should handle custom icon', () => {
      const { container } = render(<SingleStatDownloadsCumulative icon="chart bar" />);

      const iconElement = container.querySelector('.chart.bar.icon.mr-10');
      expect(iconElement).toBeInTheDocument();
      expect(iconElement).toHaveAttribute('aria-hidden', 'true');
    });
  });

  describe('Date Filtering and Snapshot Values', () => {
    it('should get the latest value within the date range', () => {
      // Test data with multiple values, should get the latest one within range
      mockUseStatsDashboard.mockReturnValue({
        stats: [
          {
            year: 2023,
            usageSnapshotData: {
              global: {
                downloads: [
                  {
                    id: 'global',
                    name: 'Global',
                    year: 2024,
                    data: [
                      ['12-31', 10]
                    ]
                  }
                ]
              }
            }
          },
          {
            year: 2024,
            usageSnapshotData: {
              global: {
                downloads: [
                  {
                    id: 'global',
                    name: 'Global',
                    year: 2024,
                    data: [
                      ['01-01', 20],
                      ['01-02', 30],
                      ['01-03', 40]
                    ]
                  }
                ]
              }
            }
          }
        ],
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') },
        isLoading: false
      });

      render(<SingleStatDownloadsCumulative />);

      // Should get the latest value within the date range: 30
      expect(screen.getByText('30')).toBeInTheDocument();
    });

    it('should handle data completely outside date range', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: [
          {
            year: 2023,
            usageSnapshotData: {
              global: {
                downloads: [
                  {
                    id: 'global',
                    name: 'Global',
                    year: 2024,
                    data: [
                      ['12-30', 10],
                      ['12-31', 20]
                    ]
                  }
                ]
              }
            }
          },
          {
            year: 2024,
            usageSnapshotData: {
              global: {
                downloads: [
                  {
                    id: 'global',
                    name: 'Global',
                    data: [
                      ['01-03', 30],
                      ['01-04', 40]
                    ]
                  }
                ]
              }
            }
          }
        ],
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') },
        isLoading: false
      });

      render(<SingleStatDownloadsCumulative />);

      // Should show 0 since no data is within the date range
      expect(screen.getByText('0')).toBeInTheDocument();
    });

    it('should handle partial date ranges (only start date)', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: [
          {
            year: 2023,
            usageSnapshotData: {
              global: {
                downloads: [
                  {
                    id: 'global',
                    name: 'Global',
                    year: 2024,
                    data: [
                      ['12-31', 10]
                    ]
                  }
                ]
              }
            }
          },
          {
            year: 2024,
            usageSnapshotData: {
              global: {
                downloads: [
                  {
                    id: 'global',
                    name: 'Global',
                    year: 2024,
                    data: [
                      ['01-01', 20],
                      ['01-02', 30],
                      ['01-03', 40]
                    ]
                  }
                ]
              }
            }
          }
        ],
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: null },
        isLoading: false
      });

      render(<SingleStatDownloadsCumulative />);

      // Should get the latest value from start date onwards: 40
      expect(screen.getByText('40')).toBeInTheDocument();
    });

    it('should handle partial date ranges (only end date)', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: [
          {
            year: 2023,
            usageSnapshotData: {
              global: {
                downloads: [
                  {
                    id: 'global',
                    name: 'Global',
                    year: 2024,
                    data: [
                      ['12-31', 10]
                    ]
                  }
                ]
              }
            }
          },
          {
            year: 2024,
            usageSnapshotData: {
              global: {
                downloads: [
                  {
                    id: 'global',
                    name: 'Global',
                    year: 2024,
                    data: [
                      ['01-01', 20],
                      ['01-02', 30],
                      ['01-03', 40]
                    ]
                  }
                ]
              }
            }
          }
        ],
        dateRange: { start: null, end: new Date('2024-01-02T00:00:00.000Z') },
        isLoading: false
      });

      render(<SingleStatDownloadsCumulative />);

      // Should get the latest value up to and including end date: 30
      expect(screen.getByText('30')).toBeInTheDocument();
    });
  });

  describe('Edge Cases and Error Handling', () => {
    it('should handle empty stats gracefully', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: null,
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') },
        isLoading: false
      });

      render(<SingleStatDownloadsCumulative />);

      expect(screen.getByText('0')).toBeInTheDocument();
    });

    it('should handle empty data array', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: {
          usageSnapshotData: {
            global: {
              downloads: [
                {
                  id: 'global',
                  name: 'Global',
                  data: []
                }
              ]
            }
          }
        },
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') },
        isLoading: false
      });

      render(<SingleStatDownloadsCumulative />);

      expect(screen.getByText('0')).toBeInTheDocument();
    });

    it('should handle missing data property', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: {
          usageSnapshotData: {
            global: {
              downloads: [
                {
                  id: 'downloads',
                  name: 'Downloads'
                  // Missing data property
                }
              ]
            }
          }
        },
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') },
        isLoading: false
      });

      render(<SingleStatDownloadsCumulative />);

      expect(screen.getByText('0')).toBeInTheDocument();
    });

    it('should handle no date range', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: [
          {
            year: 2024,
            usageSnapshotData: {
              global: {
                downloads: [
                  {
                    id: 'global',
                    name: 'Global',
                    year: 2024,
                    data: [
                      ['01-01', 10],
                      ['01-02', 20]
                    ]
                  }
                ]
              }
            }
          }
        ],
        dateRange: null,
        isLoading: false
      });

      render(<SingleStatDownloadsCumulative />);

      // Should get the latest value when no date range is provided: 20
      expect(screen.getByText('20')).toBeInTheDocument();
    });
  });
});