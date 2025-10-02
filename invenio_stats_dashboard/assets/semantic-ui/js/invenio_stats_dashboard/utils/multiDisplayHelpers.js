// Part of the Invenio-Stats-Dashboard extension for InvenioRDM
// Copyright (C) 2025 Mesh Research
//
// Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
// it under the terms of the MIT License; see LICENSE file for more details.

import React from "react";
import { formatNumber } from "./numbers";
import { CHART_COLORS, RECORD_START_BASES } from '../constants';
import { extractLocalizedLabel } from '../api/dataTransformer';
import { filterSeriesArrayByDate } from './filters';
import { i18next } from "@translations/invenio_stats_dashboard/i18next";

/**
 * Transform multi-display data into chart-ready format
 *
 * @param {Array} rawData - Array of data items from the API (access rights, affiliations, etc.)
 * @param {number} pageSize - Number of top items to show individually
 * @param {string} searchField - Field name for search links (e.g., 'metadata.access_status.id', 'metadata.affiliations.affiliation')
 * @param {Array} colorPalette - Array of color arrays for chart styling
 * @returns {Object} Object containing transformedData, otherData, and totalCount
 */
const transformMultiDisplayData = (rawData, pageSize = 10, searchField, colorPalette = CHART_COLORS.secondary) => {
  if (!rawData || !Array.isArray(rawData)) {
    return {
      transformedData: [],
      otherData: null,
      totalCount: 0
    };
  }

  const totalCount = rawData.reduce((sum, item) => sum + item?.data?.[0]?.value?.[1] || 0, 0);

  const topXItems = rawData.slice(0, pageSize);
  const otherItems = rawData.slice(pageSize);

  const transformedData = topXItems.map((item, index) => {
    const value = item?.data?.[0]?.value?.[1] || 0;
    const percentage = totalCount > 0 ? Math.round((value / totalCount) * 100) : 0;
    const currentLanguage = i18next.language || 'en';
    const localizedName = extractLocalizedLabel(item.name, currentLanguage);
    return {
      name: localizedName,
      value: value,
      percentage: percentage,
      id: item.id,
      link: searchField ? `/search?q=${searchField}:${item.id}` : null,
      itemStyle: {
        color: colorPalette[index % colorPalette.length][1]
      }
    };
  });

  const otherData = otherItems.length > 0 ? otherItems.reduce((acc, item) => {
    acc.value += item?.data?.[0]?.value?.[1] || 0;
    return acc;
  }, {
    id: "other",
    name: i18next.t("Other"),
    value: 0,
    itemStyle: {
      color: colorPalette[colorPalette.length - 1][1]
    }
  }) : null;

  if (otherData) {
    otherData.percentage = totalCount > 0 ? Math.round((otherData.value / totalCount) * 100) : 0;
  }

  return {
    transformedData,
    otherData,
    totalCount
  };
};

/**
 * Assemble rows for the table display from transformed data
 *
 * @param {Array} transformedData - Array of transformed data
 * @param {Object} otherData - Other data object (can be null)
 * @returns {Array} Array of row arrays for the table
 */
const assembleMultiDisplayRows = (transformedData, otherData) => {
  const allData = [
    ...transformedData,
    ...(otherData ? [otherData] : [])
  ];

  return allData.map(({ name, value, percentage, link }) => [
    null,
    link ? <a href={link} target="_blank" rel="noopener noreferrer">{name}</a> : name,
    `${formatNumber(value, 'compact')} (${percentage}%)`,
  ]);
};

/**
 * Extract record-based data from yearly stats array
 *
 * @param {Array} stats - Array of yearly stats objects
 * @param {string} recordStartBasis - Record basis ('added', 'created', 'published')
 * @param {string} category - Data category ('resourceTypes', 'subjects', etc.)
 * @param {Object} dateRange - Date range object
 * @returns {Array} Filtered array of series data
 */
const extractRecordBasedData = (stats, recordStartBasis, category, dateRange) => {
  const seriesCategoryMap = {
    [RECORD_START_BASES.ADDED]: 'recordSnapshotDataAdded',
    [RECORD_START_BASES.CREATED]: 'recordSnapshotDataCreated',
    [RECORD_START_BASES.PUBLISHED]: 'recordSnapshotDataPublished',
  };

  const data = stats?.flatMap(yearlyStats =>
    yearlyStats?.[seriesCategoryMap[recordStartBasis]]?.[category]?.records || []
  );

  return filterSeriesArrayByDate(data, dateRange, true);
};

/**
 * Extract usage-based data from yearly stats array
 *
 * @param {Array} stats - Array of yearly stats objects
 * @param {string} category - Data category ('countriesByView', 'referrersByView', etc.)
 * @param {string} metric - Metric name ('views', 'downloads', etc.)
 * @param {Object} dateRange - Date range object
 * @returns {Array} Filtered array of series data
 */
const extractUsageBasedData = (stats, category, metric, dateRange) => {
  const data = stats?.flatMap(yearlyStats =>
    yearlyStats?.usageSnapshotData?.[category]?.[metric] || []
  );

  return filterSeriesArrayByDate(data, dateRange, true);
};

/**
 * Generate standard chart options for multi-display components
 *
 * @param {Array} transformedData - Transformed data array
 * @param {Object} otherData - Other data object
 * @param {Array} availableViews - Available view types
 * @returns {Object} Chart options object
 */
const generateMultiDisplayChartOptions = (transformedData, otherData, availableViews) => {
  const allData = [...transformedData, ...(otherData ? [otherData] : [])];

  const options = {
    list: {},
    pie: {
      grid: {
        top: '7%',
        right: '5%',
        bottom: '5%',
        left: '2%',
        containLabel: true
      },
      tooltip: {
        trigger: "item",
        formatter: (params) => {
          return `<div>
            ${params.name}: ${formatNumber(params.value, 'compact')} (${params.data.percentage}%)
          </div>`;
        },
      },
      series: [
        {
          type: "pie",
          radius: ["30%", "70%"],
          data: allData,
          spacing: 2,
          itemStyle: {
            borderWidth: 2,
            borderColor: "#fff",
          },
          label: {
            show: true,
            fontSize: 14,
          },
          emphasis: {
            itemStyle: {
              shadowBlur: 10,
              shadowOffsetX: 0,
              shadowColor: "rgba(0, 0, 0, 0.5)",
            },
          },
        },
      ],
    },
    bar: {
      grid: {
        top: '7%',
        right: '5%',
        bottom: '5%',
        left: '2%',
        containLabel: true
      },
      tooltip: {
        trigger: "item",
        formatter: (params) => {
          return `<div>
            ${params.name}: ${formatNumber(params.value, 'compact')} (${params.data.percentage}%)
          </div>`;
        },
      },
      yAxis: {
        type: "category",
        data: allData.map(({ name }) => name),
        axisTick: { show: false },
        axisLabel: {
          show: false,
        },
      },
      xAxis: {
        type: "value",
        axisLabel: {
          fontSize: 14,
          formatter: (value) => formatNumber(value, "compact"),
        },
      },
      series: [
        {
          type: "bar",
          barWidth: "90%",
          data: allData.map((item, index) => {
            const maxValue = Math.max(...allData.map((d) => d.value));
            return {
              value: item.value,
              percentage: item.percentage,
              id: item.id,
              itemStyle: item.itemStyle,
              label: {
                show: true,
                formatter: "{b}",
                fontSize: 14,
                position: item.value < maxValue * 0.3 ? "right" : "inside",
                color: item.value < maxValue * 0.3 ? item.itemStyle.color : "#fff",
                align: item.value < maxValue * 0.3 ? "left" : "center",
                verticalAlign: "middle",
              },
            };
          }),
        },
      ],
    },
  };

  return Object.fromEntries(
    Object.entries(options).filter(([key]) => availableViews.includes(key))
  );
};

export {
  transformMultiDisplayData,
  assembleMultiDisplayRows,
  extractRecordBasedData,
  extractUsageBasedData,
  generateMultiDisplayChartOptions
};