// Part of the Invenio-Stats-Dashboard extension for InvenioRDM
// Copyright (C) 2025 Mesh Research
//
// Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
// it under the terms of the MIT License; see LICENSE file for more details.

/**
 * Pattern detection utility functions for time series data transformation
 */

/**
 * Calculate Simple Moving Average for a data series
 * @param {Array} dataPoints - Array of {date, value} objects
 * @param {number} windowSize - Number of periods to average (e.g., 7 for 7-day SMA)
 * @returns {Array} Array of {date, value} objects with SMA values
 */
export function calculateSMA(dataPoints, windowSize = 7) {
  if (dataPoints.length < windowSize) {
    return []; // Not enough data
  }
  
  const smaData = [];
  
  for (let i = windowSize - 1; i < dataPoints.length; i++) {
    // Get the window of data points
    const window = dataPoints.slice(i - windowSize + 1, i + 1);
    
    // Calculate average
    const sum = window.reduce((acc, point) => acc + point.value, 0);
    const average = sum / windowSize;
    
    // Use the date of the last point in the window
    smaData.push({
      date: dataPoints[i].date,
      value: average
    });
  }
  
  return smaData;
}

/**
 * Calculate growth rate between consecutive periods
 * @param {Array} dataPoints - Array of {date, value} objects
 * @returns {Array} Array of {date, value} objects with growth rates
 */
export function calculateGrowthRate(dataPoints) {
  if (dataPoints.length < 2) {
    return [];
  }
  
  const growthData = [];
  
  for (let i = 1; i < dataPoints.length; i++) {
    const current = dataPoints[i].value;
    const previous = dataPoints[i - 1].value;
    
    if (previous === 0) {
      // Avoid division by zero
      growthData.push({
        date: dataPoints[i].date,
        value: null // or 0, depending on how you want to handle this
      });
    } else {
      const growthRate = ((current - previous) / previous) * 100;
      growthData.push({
        date: dataPoints[i].date,
        value: growthRate
      });
    }
  }
  
  return growthData;
}

/**
 * Transform data series to show SMA instead of raw data
 * @param {Array} dataSeriesArray - Array of data series objects (each with a `data` property)
 * @param {number} windowSize - Number of periods to average (e.g., 7 for 7-day SMA)
 * @returns {Array} Data series array with SMA data points
 */
export function transformToSMA(dataSeriesArray, windowSize = 7) {
  return dataSeriesArray.map(series => ({
    ...series,
    data: calculateSMA(series.data, windowSize)
  }));
}

/**
 * Transform data series to show growth rates instead of raw data
 * @param {Array} dataSeriesArray - Array of data series objects (each with a `data` property)
 * @returns {Array} Data series array with growth rate data points
 */
export function transformToGrowthRate(dataSeriesArray) {
  return dataSeriesArray.map(series => ({
    ...series,
    data: calculateGrowthRate(series.data)
  }));
}
