// Part of the Invenio-Stats-Dashboard extension for InvenioRDM
// Copyright (C) 2025 Mesh Research
//
// Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
// it under the terms of the MIT License; see LICENSE file for more details.

import {
  calculateSMA,
  calculateGrowthRate,
  transformToSMA,
  transformToGrowthRate,
} from './patternDetection';

describe('Pattern Detection Utilities', () => {
  describe('calculateSMA', () => {
    it('should return empty array when not enough data points', () => {
      const dataPoints = [
        { date: '2024-01-01', value: 10 },
        { date: '2024-01-02', value: 15 },
      ];
      const result = calculateSMA(dataPoints, 7);
      expect(result).toEqual([]);
    });

    it('should calculate 7-day SMA correctly', () => {
      const dataPoints = [
        { date: '2024-01-01', value: 10 },
        { date: '2024-01-02', value: 15 },
        { date: '2024-01-03', value: 8 },
        { date: '2024-01-04', value: 12 },
        { date: '2024-01-05', value: 20 },
        { date: '2024-01-06', value: 18 },
        { date: '2024-01-07', value: 14 },
      ];
      const result = calculateSMA(dataPoints, 7);
      
      expect(result).toHaveLength(1);
      expect(result[0].date).toBe('2024-01-07');
      expect(result[0].value).toBeCloseTo(13.86, 2); // (10+15+8+12+20+18+14)/7
    });

    it('should calculate 3-day SMA correctly', () => {
      const dataPoints = [
        { date: '2024-01-01', value: 10 },
        { date: '2024-01-02', value: 15 },
        { date: '2024-01-03', value: 8 },
        { date: '2024-01-04', value: 12 },
        { date: '2024-01-05', value: 20 },
      ];
      const result = calculateSMA(dataPoints, 3);
      
      expect(result).toHaveLength(3);
      expect(result[0].value).toBeCloseTo(11, 2); // (10+15+8)/3
      expect(result[1].value).toBeCloseTo(11.67, 2); // (15+8+12)/3
      expect(result[2].value).toBeCloseTo(13.33, 2); // (8+12+20)/3
    });

    it('should handle empty array', () => {
      const result = calculateSMA([], 7);
      expect(result).toEqual([]);
    });
  });

  describe('calculateGrowthRate', () => {
    it('should return empty array when not enough data points', () => {
      const dataPoints = [{ date: '2024-01-01', value: 10 }];
      const result = calculateGrowthRate(dataPoints);
      expect(result).toEqual([]);
    });

    it('should calculate growth rate correctly', () => {
      const dataPoints = [
        { date: '2024-01-01', value: 100 },
        { date: '2024-01-02', value: 120 },
        { date: '2024-01-03', value: 110 },
        { date: '2024-01-04', value: 130 },
      ];
      const result = calculateGrowthRate(dataPoints);
      
      expect(result).toHaveLength(3);
      expect(result[0].value).toBe(20); // (120-100)/100 * 100
      expect(result[1].value).toBeCloseTo(-8.33, 2); // (110-120)/120 * 100
      expect(result[2].value).toBeCloseTo(18.18, 2); // (130-110)/110 * 100
    });

    it('should handle division by zero', () => {
      const dataPoints = [
        { date: '2024-01-01', value: 0 },
        { date: '2024-01-02', value: 10 },
      ];
      const result = calculateGrowthRate(dataPoints);
      
      expect(result).toHaveLength(1);
      expect(result[0].value).toBeNull();
    });

    it('should handle negative growth', () => {
      const dataPoints = [
        { date: '2024-01-01', value: 100 },
        { date: '2024-01-02', value: 80 },
      ];
      const result = calculateGrowthRate(dataPoints);
      
      expect(result).toHaveLength(1);
      expect(result[0].value).toBe(-20); // (80-100)/100 * 100
    });

    it('should handle empty array', () => {
      const result = calculateGrowthRate([]);
      expect(result).toEqual([]);
    });
  });

  describe('transformToSMA', () => {
    it('should transform data series to SMA', () => {
      const dataSeriesArray = [
        {
          name: 'Community A',
          data: [
            { date: '2024-01-01', value: 10 },
            { date: '2024-01-02', value: 15 },
            { date: '2024-01-03', value: 8 },
            { date: '2024-01-04', value: 12 },
            { date: '2024-01-05', value: 20 },
            { date: '2024-01-06', value: 18 },
            { date: '2024-01-07', value: 14 },
          ],
        },
      ];
      
      const result = transformToSMA(dataSeriesArray, 7);
      
      expect(result).toHaveLength(1);
      expect(result[0].name).toBe('Community A');
      expect(result[0].data).toHaveLength(1);
      expect(result[0].data[0].value).toBeCloseTo(13.86, 2);
    });

    it('should preserve series metadata', () => {
      const dataSeriesArray = [
        {
          name: 'Community A',
          color: '#ff0000',
          data: [
            { date: '2024-01-01', value: 10 },
            { date: '2024-01-02', value: 15 },
            { date: '2024-01-03', value: 8 },
          ],
        },
      ];
      
      const result = transformToSMA(dataSeriesArray, 3);
      
      expect(result[0].name).toBe('Community A');
      expect(result[0].color).toBe('#ff0000');
    });

    it('should handle empty data series', () => {
      const dataSeriesArray = [
        {
          name: 'Community A',
          data: [],
        },
      ];
      
      const result = transformToSMA(dataSeriesArray, 7);
      
      expect(result).toHaveLength(1);
      expect(result[0].data).toEqual([]);
    });
  });

  describe('transformToGrowthRate', () => {
    it('should transform data series to growth rates', () => {
      const dataSeriesArray = [
        {
          name: 'Community A',
          data: [
            { date: '2024-01-01', value: 100 },
            { date: '2024-01-02', value: 120 },
            { date: '2024-01-03', value: 110 },
          ],
        },
      ];
      
      const result = transformToGrowthRate(dataSeriesArray);
      
      expect(result).toHaveLength(1);
      expect(result[0].name).toBe('Community A');
      expect(result[0].data).toHaveLength(2);
      expect(result[0].data[0].value).toBe(20);
      expect(result[0].data[1].value).toBeCloseTo(-8.33, 2);
    });

    it('should preserve series metadata', () => {
      const dataSeriesArray = [
        {
          name: 'Community A',
          color: '#00ff00',
          data: [
            { date: '2024-01-01', value: 100 },
            { date: '2024-01-02', value: 120 },
          ],
        },
      ];
      
      const result = transformToGrowthRate(dataSeriesArray);
      
      expect(result[0].name).toBe('Community A');
      expect(result[0].color).toBe('#00ff00');
    });

    it('should handle empty data series', () => {
      const dataSeriesArray = [
        {
          name: 'Community A',
          data: [],
        },
      ];
      
      const result = transformToGrowthRate(dataSeriesArray);
      
      expect(result).toHaveLength(1);
      expect(result[0].data).toEqual([]);
    });
  });
});
