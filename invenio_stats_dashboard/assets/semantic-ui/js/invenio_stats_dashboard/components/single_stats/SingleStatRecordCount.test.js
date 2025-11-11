// Part of the Invenio-Stats-Dashboard extension for InvenioRDM
// Copyright (C) 2025 Mesh Research
//
// Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
// it under the terms of the MIT License; see LICENSE file for more details.

import React from 'react';
import { render, screen } from '@testing-library/react';
import { SingleStatRecordCount } from './SingleStatRecordCount';
import { useStatsDashboard } from '../../context/StatsDashboardContext';

// Mock the dependencies
jest.mock('../../context/StatsDashboardContext');

const mockUseStatsDashboard = useStatsDashboard;

describe('SingleStatRecordCount', () => {
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
            recordDeltaDataAdded: {
              global: {
                records: [
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
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') },
        recordStartBasis: 'added',
        isLoading: false,
        isLoading: false
      });
    });

    it('should render with default title and value', () => {
      render(<SingleStatRecordCount />);

      expect(screen.getByText('Records')).toBeInTheDocument();
      expect(screen.getByText('30')).toBeInTheDocument();
    });

    it('should render with custom title', () => {
      render(<SingleStatRecordCount title="Custom Records" />);

      expect(screen.getByText('Custom Records')).toBeInTheDocument();
    });

    it('should display description with date range', () => {
      render(<SingleStatRecordCount />);

      // The description should contain the date range
      expect(screen.getByText(/from/)).toBeInTheDocument();
      expect(screen.getByText(/–/)).toBeInTheDocument();
    });
  });

  describe('HTML Structure and Accessibility', () => {
    beforeEach(() => {
      mockUseStatsDashboard.mockReturnValue({
        stats: [
          {
            year: 2024,
            recordDeltaDataAdded: {
              global: {
                records: [
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
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') },
        recordStartBasis: 'added',
        isLoading: false,
        isLoading: false
      });
    });

    it('should have correct container structure and CSS classes', () => {
      const { container } = render(<SingleStatRecordCount />);

      // Check main container
      const mainContainer = container.querySelector('.stats-single-stat-container');
      expect(mainContainer).toBeInTheDocument();
      expect(mainContainer).toHaveAttribute('role', 'region');
      expect(mainContainer).toHaveAttribute('aria-describedby');
      expect(mainContainer).toHaveAttribute('aria-label', 'Records');
    });

    it('should have correct value element structure', () => {
      const { container } = render(<SingleStatRecordCount />);

      // Check value element
      const valueElement = container.querySelector('.value.stats-single-stat-value');
      expect(valueElement).toBeInTheDocument();
      expect(valueElement).toHaveAttribute('aria-label', '30 Records');
      expect(valueElement).toHaveTextContent('30');
    });

    it('should have correct header structure with icon', () => {
      const { container } = render(<SingleStatRecordCount />);

      // Check header element
      const headerElement = container.querySelector('.label.stats-single-stat-header.mt-5');
      expect(headerElement).toBeInTheDocument();
      expect(headerElement).toHaveTextContent('Records');

      // Check icon
      const iconElement = headerElement.querySelector('.file.icon.mr-10');
      expect(iconElement).toBeInTheDocument();
      expect(iconElement).toHaveAttribute('aria-hidden', 'true');
    });

    it('should have correct description structure', () => {
      const { container } = render(<SingleStatRecordCount />);

      // Check description element
      const descriptionElement = container.querySelector('.label.stats-single-stat-description.mt-5');
      expect(descriptionElement).toBeInTheDocument();
      expect(descriptionElement).toHaveAttribute('id');
      expect(descriptionElement).toHaveAttribute('aria-label');
      expect(descriptionElement).toHaveTextContent(/from/);
    });

    it('should have proper accessibility attributes', () => {
      const { container } = render(<SingleStatRecordCount />);

      const mainContainer = container.querySelector('.stats-single-stat-container');
      const descriptionElement = container.querySelector('.stats-single-stat-description');

      // Check that aria-describedby points to the description element
      const describedBy = mainContainer.getAttribute('aria-describedby');
      expect(describedBy).toBe(descriptionElement.getAttribute('id'));
    });

    it('should handle custom title in accessibility attributes', () => {
      const { container } = render(<SingleStatRecordCount title="Custom Title" />);

      const mainContainer = container.querySelector('.stats-single-stat-container');
      const valueElement = container.querySelector('.value');

      expect(mainContainer).toHaveAttribute('aria-label', 'Custom Title');
      expect(valueElement).toHaveAttribute('aria-label', '30 Custom Title');
    });

    it('should handle custom icon', () => {
      const { container } = render(<SingleStatRecordCount icon="chart bar" />);

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
            recordDeltaDataAdded: {
              global: {
                records: [
                  {
                    id: 'global',
                    name: 'Global',
                    year: 2024,
                    data: [
                      ['12-31', 5],  // Outside range (2023)
                      ['01-01', 10], // Inside range
                      ['01-02', 15], // Inside range
                      ['01-03', 20]  // Outside range
                    ]
                  }
                ]
              }
            }
          }
        ],
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') },
        recordStartBasis: 'added',
        isLoading: false,
        isLoading: false
      });

      render(<SingleStatRecordCount />);

      // Should only sum values within the date range: 10 + 15 = 25
      expect(screen.getByText('25')).toBeInTheDocument();
    });

    it('should handle data completely outside date range', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: [
          {
            year: 2024,
            recordDeltaDataAdded: {
              global: {
                records: [
                  {
                    id: 'global',
                    name: 'Global',
                    year: 2024,
                    data: [
                      ['12-30', 5],  // Outside range
                      ['12-31', 10], // Outside range
                      ['01-03', 15], // Outside range
                      ['01-04', 20]  // Outside range
                    ]
                  }
                ]
              }
            }
          }
        ],
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') },
        recordStartBasis: 'added',
        isLoading: false,
        isLoading: false
      });

      render(<SingleStatRecordCount />);

      // Should show 0 since no data is within the date range
      expect(screen.getByText('0')).toBeInTheDocument();
    });

    it('should handle partial date ranges (only start date)', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: [
          {
            year: 2023,
            recordDeltaDataAdded: {
              global: {
                records: [
                  {
                    id: 'global',
                    name: 'Global',
                    year: 2023,
                    data: [
                      ['12-31', 5]  // Before start
                    ]
                  }
                ]
              }
            }
          },
          {
            year: 2024,
            recordDeltaDataAdded: {
              global: {
                records: [
                  {
                    id: 'global',
                    name: 'Global',
                    year: 2024,
                    data: [
                      ['01-01', 10], // On start date
                      ['01-02', 15], // After start
                      ['01-03', 20]  // After start
                    ]
                  }
                ]
              }
            }
          }
        ],
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-12-31T00:00:00.000Z') },
        recordStartBasis: 'added',
        isLoading: false
      });

      render(<SingleStatRecordCount />);

      // Should include all data from start date onwards: 10 + 15 + 20 = 45
      expect(screen.getByText('45')).toBeInTheDocument();
    });

    it('should handle partial date ranges (only end date)', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: [
          {
            year: 2023,
            recordDeltaDataAdded: {
              global: {
                records: [
                  {
                    id: 'global',
                    name: 'Global',
                    year: 2023,
                    data: [
                      ['12-31', 5]  // Before end
                    ]
                  }
                ]
              }
            }
          },
          {
            year: 2024,
            recordDeltaDataAdded: {
              global: {
                records: [
                  {
                    id: 'global',
                    name: 'Global',
                    year: 2024,
                    data: [
                      ['01-01', 10], // Before end
                      ['01-02', 15], // On end date
                      ['01-03', 20]  // After end
                    ]
                  }
                ]
              }
            }
          }
        ],
        dateRange: { start: null, end: new Date('2024-01-02T00:00:00.000Z') },
        recordStartBasis: 'added',
        isLoading: false
      });

      render(<SingleStatRecordCount />);

      // Should include all data up to and including end date: 5 + 10 + 15 = 30
      expect(screen.getByText('30')).toBeInTheDocument();
    });
  });

  describe('Different Record Bases', () => {
    it('should handle different record start basis correctly', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: [
          {
            year: 2024,
            recordDeltaDataCreated: {
              global: {
                records: [
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
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') },
        recordStartBasis: 'created',
        isLoading: false
      });

      render(<SingleStatRecordCount />);

      expect(screen.getByText('30')).toBeInTheDocument();
    });

    it('should handle published record basis', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: [
          {
            year: 2024,
            recordDeltaDataPublished: {
              global: {
                records: [
                  {
                    id: 'global',
                    name: 'Global',
                    year: 2024,
                    data: [
                      ['01-01', 5],
                      ['01-02', 15]
                    ]
                  }
                ]
              }
            }
          }
        ],
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') },
        recordStartBasis: 'published',
        isLoading: false
      });

      render(<SingleStatRecordCount />);

      expect(screen.getByText('20')).toBeInTheDocument();
    });
  });

  describe('Edge Cases and Error Handling', () => {
    it('should handle empty stats gracefully', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: null,
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') },
        recordStartBasis: 'added',
        isLoading: false
      });

      render(<SingleStatRecordCount />);

      expect(screen.getByText('0')).toBeInTheDocument();
    });

    it('should handle empty data array', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: {
          recordDeltaDataAdded: {
            global: {
              records: [
                {
                  id: 'global',
                  name: 'Records',
                  data: []
                }
              ]
            }
          }
        },
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') },
        recordStartBasis: 'added',
        isLoading: false
      });

      render(<SingleStatRecordCount />);

      expect(screen.getByText('0')).toBeInTheDocument();
    });

    it('should handle missing data property', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: {
          recordDeltaDataAdded: {
            global: {
              records: [
                {
                  id: 'global',
                  name: 'Records'
                  // Missing data property
                }
              ]
            }
          }
        },
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') },
        recordStartBasis: 'added',
        isLoading: false
      });

      render(<SingleStatRecordCount />);

      expect(screen.getByText('0')).toBeInTheDocument();
    });

    it('should handle no date range', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: [
          {
            year: 2024,
            recordDeltaDataAdded: {
              global: {
                records: [
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
        recordStartBasis: 'added',
        isLoading: false
      });

      render(<SingleStatRecordCount />);

      // Should sum all data when no date range is provided: 10 + 20 = 30
      expect(screen.getByText('30')).toBeInTheDocument();
    });
  });
});