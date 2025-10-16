// Part of the Invenio-Stats-Dashboard extension for InvenioRDM
// Copyright (C) 2025 Mesh Research
//
// Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
// it under the terms of the MIT License; see LICENSE file for more details.

/**
 * Yearly Block Manager for invenio-stats-dashboard
 *
 * This module handles translating user-selected date ranges into 1-year blocks
 * and managing which blocks need to be fetched from the back-end, and which
 * are already in memory.
 */

/**
 * Determine which yearly blocks are missing from the current stats.
 *
 * @param {Date} startDate - Start date of the requested range
 * @param {Date} endDate - End date of the requested range
 * @param {Array} currentStats - Array of yearly stats objects (each with a 'year' property)
 * @returns {Array} Array of missing yearly block objects
 */
const findMissingBlocks = (startDate, endDate, currentStats) => {
  const requestedBlocks = [];
  const startYear = startDate.getUTCFullYear();
  const endYear = endDate.getUTCFullYear();

  for (let year = startYear; year <= endYear; year++) {
    requestedBlocks.push({
      year,
      startDate: new Date(Date.UTC(year, 0, 1)),
      endDate: new Date(Date.UTC(year, 11, 31)),
    });
  }
  const cachedYears = new Set(currentStats.map((stats) => stats.year));
  const missingBlocks = requestedBlocks.filter(
    (block) => !cachedYears.has(block.year),
  );
  return missingBlocks;
};

/**
 * Merge new yearly stats with existing stats array
 *
 * @param {Array} currentStats - Array of existing yearly stats objects
 * @param {Array} newYearlyStats - Array of new yearly stats objects
 * @returns {Array} Merged and sorted array of yearly stats objects
 */
const mergeYearlyStats = (currentStats, newYearlyStats) => {
  const existingYears = new Set(currentStats.map((stats) => stats.year));
  const mergedStats = [...currentStats];

  newYearlyStats.forEach((yearStats) => {
    if (!existingYears.has(yearStats.year)) {
      mergedStats.push(yearStats);
    }
  });

  return mergedStats.sort((a, b) => a.year - b.year);
};

export { findMissingBlocks, mergeYearlyStats };
