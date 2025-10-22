// Part of the Invenio-Stats-Dashboard extension for InvenioRDM
// Copyright (C) 2025 Mesh Research
//
// Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
// it under the terms of the MIT License; see LICENSE file for more details.

import React from 'react';
import { render, screen } from '@testing-library/react';
import { SingleStatDataVolume } from './SingleStatDataVolume';
import { useStatsDashboard } from '../../context/StatsDashboardContext';

// Mock the dependencies
jest.mock('../../context/StatsDashboardContext');

const mockUseStatsDashboard = useStatsDashboard;

describe('SingleStatDataVolume', () => {
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
          recordDeltaDataAdded: {
            global: {
              dataVolume: [
                {
                  id: 'global',
                  name: 'Global',
                  data: [
                    { value: [new Date('2024-01-01T00:00:00.000Z'), 1024] },
                    { value: [new Date('2024-01-02T00:00:00.000Z'), 2048] }
                  ]
                }
              ]
            }
          }
        }],
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') },
        recordStartBasis: 'added',
        isLoading: false
      });
    });

    it('should render with default title and value', () => {
      render(<SingleStatDataVolume />);

      expect(screen.getByText('Data Volume')).toBeInTheDocument();
      expect(screen.getByText('3.1 kB')).toBeInTheDocument(); // 1024 + 2048 = 3072 bytes = 3.1 kB
    });

    it('should render with custom title', () => {
      render(<SingleStatDataVolume title="Custom Data Volume" />);

      expect(screen.getByText('Custom Data Volume')).toBeInTheDocument();
    });

    it('should display description with date range', () => {
      render(<SingleStatDataVolume />);

      // The description should contain the date range
      expect(screen.getByText(/from/)).toBeInTheDocument();
      expect(screen.getByText(/–/)).toBeInTheDocument();
    });
  });

  describe('Date Filtering and Cumulative Totaling', () => {
    it('should filter data by date range and sum values correctly', () => {
      // Test data with values inside and outside the date range
      mockUseStatsDashboard.mockReturnValue({
        stats: [{
          year: 2024,
          recordDeltaDataAdded: {
            global: {
              dataVolume: [
                {
                  id: 'global',
                  name: 'Global',
                  data: [
                    { value: [new Date('2023-12-31T00:00:00.000Z'), 512] },  // Outside range
                    { value: [new Date('2024-01-01T00:00:00.000Z'), 1024] }, // Inside range
                    { value: [new Date('2024-01-02T00:00:00.000Z'), 2048] }, // Inside range
                    { value: [new Date('2024-01-03T00:00:00.000Z'), 4096] }  // Outside range
                  ]
                }
              ]
            }
          }
        }],
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') },
        recordStartBasis: 'added',
        isLoading: false,
        isLoading: false
      });

      render(<SingleStatDataVolume />);

      // Should only sum values within the date range: 1024 + 2048 = 3072 bytes = 3.1 kB
      expect(screen.getByText('3.1 kB')).toBeInTheDocument();
    });

    it('should handle data completely outside date range', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: [{
          year: 2024,
          recordDeltaDataAdded: {
            global: {
              dataVolume: [
                {
                  id: 'global',
                  name: 'Global',
                  data: [
                    { value: [new Date('2023-12-30T00:00:00.000Z'), 512] },  // Outside range
                    { value: [new Date('2023-12-31T00:00:00.000Z'), 1024] }, // Outside range
                    { value: [new Date('2024-01-03T00:00:00.000Z'), 2048] }, // Outside range
                    { value: [new Date('2024-01-04T00:00:00.000Z'), 4096] }  // Outside range
                  ]
                }
              ]
            }
          }
        }],
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') },
        recordStartBasis: 'added',
        isLoading: false
      });

      render(<SingleStatDataVolume />);

      // Should show 0 since no data is within the date range
      expect(screen.getByText('0 Bytes')).toBeInTheDocument();
    });

    it('should handle partial date ranges (only start date)', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: [
          {
            year: 2023,
            recordDeltaDataAdded: {
              global: {
                dataVolume: [
                  {
                    id: 'global',
                    name: 'Global',
                    data: [
                      { value: [new Date('2023-12-31T00:00:00.000Z'), 512] }  // Before start
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
                dataVolume: [
                  {
                    id: 'global',
                    name: 'Global',
                    data: [
                      { value: [new Date('2024-01-01T00:00:00.000Z'), 1024] }, // On start date
                      { value: [new Date('2024-01-02T00:00:00.000Z'), 2048] }, // After start
                      { value: [new Date('2024-01-03T00:00:00.000Z'), 4096] }  // After start
                    ]
                  }
                ]
              }
            }
          }
        ],
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: null },
        recordStartBasis: 'added',
        isLoading: false
      });

      render(<SingleStatDataVolume />);

      // Should include all data from start date onwards: 1024 + 2048 + 4096 = 7168 bytes = 7.2 kB
      expect(screen.getByText('7.2 kB')).toBeInTheDocument();
    });
  });

  describe('Different Record Bases', () => {
    it('should handle different record start basis correctly', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: [{
          year: 2024,
          recordDeltaDataCreated: {
            global: {
              dataVolume: [
                {
                  id: 'global',
                  name: 'Global',
                  data: [
                    { value: [new Date('2024-01-01T00:00:00.000Z'), 1024] },
                    { value: [new Date('2024-01-02T00:00:00.000Z'), 2048] }
                  ]
                }
              ]
            }
          }
        }],
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') },
        recordStartBasis: 'created',
        isLoading: false
      });

      render(<SingleStatDataVolume />);

      expect(screen.getByText('3.1 kB')).toBeInTheDocument();
    });

    it('should handle published record basis', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: [{
          year: 2024,
          recordDeltaDataPublished: {
            global: {
              dataVolume: [
                {
                  id: 'global',
                  name: 'Global',
                  data: [
                    { value: [new Date('2024-01-01T00:00:00.000Z'), 512] },
                    { value: [new Date('2024-01-02T00:00:00.000Z'), 1024] }
                  ]
                }
              ]
            }
          }
        }],
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') },
        recordStartBasis: 'published',
        isLoading: false
      });

      render(<SingleStatDataVolume />);

      expect(screen.getByText('1.5 kB')).toBeInTheDocument(); // 512 + 1024 = 1536 bytes = 1.5 kB
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

      render(<SingleStatDataVolume />);

      expect(screen.getByText('0 Bytes')).toBeInTheDocument();
    });

    it('should handle empty data array', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: [{
          year: 2024,
          recordDeltaDataAdded: {
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
        }],
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') },
        recordStartBasis: 'added',
        isLoading: false
      });

      render(<SingleStatDataVolume />);

      expect(screen.getByText('0 Bytes')).toBeInTheDocument();
    });

    it('should handle missing data property', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: [{
          year: 2024,
          recordDeltaDataAdded: {
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
        }],
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') },
        recordStartBasis: 'added',
        isLoading: false
      });

      render(<SingleStatDataVolume />);

      expect(screen.getByText('0 Bytes')).toBeInTheDocument();
    });

    it('should handle invalid data points', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: [{
          year: 2024,
          recordDeltaDataAdded: {
            global: {
              dataVolume: [
                {
                  id: 'global',
                  name: 'Global',
                  data: [
                    { value: [new Date('2024-01-01T00:00:00.000Z'), 1024] },
                    { value: null }, // Invalid data point
                    { value: [new Date('2024-01-02T00:00:00.000Z'), 2048] },
                    { value: [new Date('2024-01-03T00:00:00.000Z')] }, // Missing value
                    { value: ['not a date', 4096] } // Invalid date
                  ]
                }
              ]
            }
          }
        }],
        dateRange: { start: new Date('2024-01-01T00:00:00.000Z'), end: new Date('2024-01-02T00:00:00.000Z') },
        recordStartBasis: 'added',
        isLoading: false
      });

      render(<SingleStatDataVolume />);

      // Should only sum valid data points within range: 1024 + 2048 = 3072 bytes = 3.1 kB
      expect(screen.getByText('3.1 kB')).toBeInTheDocument();
    });

    it('should handle no date range', () => {
      mockUseStatsDashboard.mockReturnValue({
        stats: [{
          year: 2024,
          recordDeltaDataAdded: {
            global: {
              dataVolume: [
                {
                  id: 'global',
                  name: 'Global',
                  data: [
                    { value: [new Date('2024-01-01T00:00:00.000Z'), 1024] },
                    { value: [new Date('2024-01-02T00:00:00.000Z'), 2048] }
                  ]
                }
              ]
            }
          }
        }],
        dateRange: null,
        recordStartBasis: 'added',
        isLoading: false
      });

      render(<SingleStatDataVolume />);

      // Should sum all data when no date range is provided: 1024 + 2048 = 3072 bytes = 3.1 kB
      expect(screen.getByText('3.1 kB')).toBeInTheDocument();
    });
  });
});