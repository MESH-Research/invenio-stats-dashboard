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
import { getCountryNames } from './mapHelpers';


/**
 * Transform multi-display data into chart-ready format
 *
 * @param {Array} rawData - Array of data items from the API (access rights, affiliations, etc.)
 * @param {number} pageSize - Number of top items to show individually
 * @param {string} searchField - Field name for search links (e.g., 'metadata.access_status.id', 'metadata.affiliations.affiliation')
 * @param {Array} colorPalette - Array of color arrays for chart styling
 * @param {boolean} hideOtherInCharts - If true and "other" is >30% of total, exclude it from charts
 * @param {Array} globalData - Optional global data series for accurate percentage calculations
 * @param {boolean} isDelta - Whether the data is delta (sum all points) or snapshot (take latest point)
 * @returns {Object} Object containing transformedData, otherData, originalOtherData, totalCount, and otherPercentage
 */
const transformMultiDisplayData = (rawData, pageSize = 10, searchField, colorPalette = CHART_COLORS.secondary, hideOtherInCharts = false, globalData = null, isDelta = false) => {
  if (!rawData || !Array.isArray(rawData)) {
    return {
      transformedData: [],
      otherData: null,
      originalOtherData: null,
      totalCount: 0,
      otherPercentage: 0
    };
  }

  // Calculate value for each item based on data type
  const getItemValue = (item) => {
    if (!item?.data || !Array.isArray(item.data)) return 0;
    
    if (isDelta) {
      // For delta data, sum all data points
      return item.data.reduce((sum, point) => sum + (point?.value?.[1] || 0), 0);
    } else {
      // For snapshot data, take the first (and only) data point
      return item.data[0]?.value?.[1] || 0;
    }
  };

  // Calculate total count from subcount items (for backward compatibility)
  const subcountTotalCount = rawData.reduce((sum, item) => sum + getItemValue(item), 0);
  
  // Calculate global total count if global data is provided
  let globalTotalCount = 0;
  if (globalData && Array.isArray(globalData) && globalData.length > 0) {
    const globalSeries = globalData[0]; // Global data is typically a single series
    if (globalSeries && globalSeries.data && globalSeries.data.length > 0) {
      if (isDelta) {
        // For delta data, sum all values
        globalTotalCount = globalSeries.data.reduce((sum, point) => sum + (point?.value?.[1] || 0), 0);
      } else {
        // For snapshot data, use latest value
        globalTotalCount = globalSeries.data[globalSeries.data.length - 1]?.value?.[1] || 0;
      }
    }
  }
  
  // Use global total if available, otherwise fall back to subcount total
  const totalCount = globalTotalCount > 0 ? globalTotalCount : subcountTotalCount;

  // Transform all items first, then sort and slice
  const allTransformedData = rawData.map((item, index) => {
    const value = getItemValue(item);
    const percentage = totalCount > 0 ? Math.round((value / totalCount) * 100) : 0;
    const currentLanguage = i18next.language || 'en';

    const itemName = item.name || item.id;
    const localizedName = extractLocalizedLabel(itemName, currentLanguage);

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

  // Sort by value (descending) and slice
  const sortedTransformedData = allTransformedData.sort((a, b) => b.value - a.value);
  const transformedData = sortedTransformedData.slice(0, pageSize);
  const otherItems = sortedTransformedData.slice(pageSize);

  const otherData = otherItems.length > 0 ? otherItems.reduce((acc, item) => {
    acc.value += item.value;
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

  const otherPercentage = otherData ? otherData.percentage : 0;
  const shouldHideOther = hideOtherInCharts && otherPercentage > 30;

  return {
    transformedData,
    otherData: shouldHideOther ? null : otherData,
    originalOtherData: otherData, // Keep original for floating label count
    totalCount,
    otherPercentage
  };
};

/**
 * Transform multi-display data for countries into chart-ready format
 * This function specifically handles country codes and converts them to readable names
 *
 * @param {Array} rawData - Array of country data items from the API
 * @param {number} pageSize - Number of top items to show individually
 * @param {string} searchField - Field name for search links (e.g., 'metadata.country.id')
 * @param {Array} colorPalette - Array of color arrays for chart styling
 * @param {boolean} hideOtherInCharts - If true and "other" is >30% of total, exclude it from charts
 * @param {Array} globalData - Optional global data series for accurate percentage calculations
 * @param {boolean} isDelta - Whether the data is delta (sum all points) or snapshot (take latest point)
 * @returns {Object} Object containing transformedData, otherData, originalOtherData, totalCount, and otherPercentage
 */
const transformCountryMultiDisplayData = (rawData, pageSize = 10, searchField, colorPalette = CHART_COLORS.secondary, hideOtherInCharts = false, globalData = null, isDelta = false) => {
  if (!rawData || !Array.isArray(rawData)) {
    return {
      transformedData: [],
      otherData: null,
      originalOtherData: null,
      totalCount: 0,
      otherPercentage: 0
    };
  }

  // Calculate value for each item based on data type
  const getItemValue = (item) => {
    if (!item?.data || !Array.isArray(item.data)) return 0;
    
    if (isDelta) {
      // For delta data, sum all data points
      return item.data.reduce((sum, point) => sum + (point?.value?.[1] || 0), 0);
    } else {
      // For snapshot data, take the first (and only) data point
      return item.data[0]?.value?.[1] || 0;
    }
  };

  // Calculate total count from subcount items (for backward compatibility)
  const subcountTotalCount = rawData.reduce((sum, item) => sum + getItemValue(item), 0);
  
  // Calculate global total count if global data is provided
  let globalTotalCount = 0;
  if (globalData && Array.isArray(globalData) && globalData.length > 0) {
    const globalSeries = globalData[0]; // Global data is typically a single series
    if (globalSeries && globalSeries.data && globalSeries.data.length > 0) {
      if (isDelta) {
        // For delta data, sum all values
        globalTotalCount = globalSeries.data.reduce((sum, point) => sum + (point?.value?.[1] || 0), 0);
      } else {
        // For snapshot data, use latest value
        globalTotalCount = globalSeries.data[globalSeries.data.length - 1]?.value?.[1] || 0;
      }
    }
  }
  
  // Use global total if available, otherwise fall back to subcount total
  const totalCount = globalTotalCount > 0 ? globalTotalCount : subcountTotalCount;

  // Transform all items first, then sort and slice
  const allTransformedData = rawData.map((item, index) => {
    const value = getItemValue(item);
    const percentage = totalCount > 0 ? Math.round((value / totalCount) * 100) : 0;
    const countryCode = item.name || item.id;
    const countryName = getCountryNames(countryCode).displayName;
    return {
      name: countryName,
      value: value,
      percentage: percentage,
      id: item.id,
      link: searchField ? `/search?q=${searchField}:${item.id}` : null,
      itemStyle: {
        color: colorPalette[index % colorPalette.length][1]
      }
    };
  });

  // Sort by value (descending) and slice
  const sortedTransformedData = allTransformedData.sort((a, b) => b.value - a.value);
  const transformedData = sortedTransformedData.slice(0, pageSize);
  const otherItems = sortedTransformedData.slice(pageSize);

  const otherData = otherItems.length > 0 ? otherItems.reduce((acc, item) => {
    acc.value += item.value;
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

  const otherPercentage = otherData ? otherData.percentage : 0;
  const shouldHideOther = hideOtherInCharts && otherPercentage > 30;

  return {
    transformedData,
    otherData: shouldHideOther ? null : otherData,
    originalOtherData: otherData, // Keep original for floating label count
    totalCount,
    otherPercentage
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
 * Extract data from yearly stats array (consolidated for both record and usage data)
 *
 * @param {Array} stats - Array of yearly stats objects
 * @param {string} recordStartBasis - Record basis ('added', 'created', 'published') - only used for record data
 * @param {string} category - Data category ('resourceTypes', 'subjects', 'countriesByView', etc.)
 * @param {string} metric - Metric name ('records', 'views', 'downloads', etc.)
 * @param {Object} dateRange - Date range object
 * @param {boolean} isDelta - Whether to use delta data (sum across period) or snapshot data (latest only)
 * @param {boolean} isUsageData - Whether to extract usage data or record data
 * @returns {Array} Filtered array of series data
 */
const extractData = (stats, recordStartBasis, category, metric, dateRange, isDelta = false, isUsageData = false) => {
  let allItems;

  if (isUsageData) {
    // Extract usage data
    allItems = stats?.flatMap(yearlyStats =>
      yearlyStats?.[isDelta ? 'usageDeltaData' : 'usageSnapshotData']?.[category]?.[metric] || []
    );
  } else {
    // Extract record data
    const seriesCategoryMap = isDelta ? {
      [RECORD_START_BASES.ADDED]: 'recordDeltaDataAdded',
      [RECORD_START_BASES.CREATED]: 'recordDeltaDataCreated',
      [RECORD_START_BASES.PUBLISHED]: 'recordDeltaDataPublished',
    } : {
      [RECORD_START_BASES.ADDED]: 'recordSnapshotDataAdded',
      [RECORD_START_BASES.CREATED]: 'recordSnapshotDataCreated',
      [RECORD_START_BASES.PUBLISHED]: 'recordSnapshotDataPublished',
    };

    allItems = stats?.flatMap(yearlyStats =>
      yearlyStats?.[seriesCategoryMap[recordStartBasis]]?.[category]?.[metric] || []
    );
  }

  if (!allItems || allItems.length === 0) {
    return [];
  }

  // Group items by ID and combine their time series data
  const combinedItems = {};

  allItems.forEach(item => {
    const itemId = item.id;

    if (!combinedItems[itemId]) {
      combinedItems[itemId] = {
        id: itemId,
        name: item.name,
        data: []
      };
    }

    if (item.data && Array.isArray(item.data)) {
      combinedItems[itemId].data.push(...item.data);
    }
  });

  const processedItems = Object.values(combinedItems);

  return filterSeriesArrayByDate(processedItems, dateRange, !isDelta);
};

/**
 * Generate floating "Other" label graphic element
 * @param {Object|null} originalOtherData - The original "other" data
 * @param {number} otherPercentage - Percentage of "other" data
 * @param {string} otherColor - Color for the "other" region
 * @returns {Object} ECharts graphic group element
 */
const createFloatingOtherLabel = (originalOtherData, otherPercentage, otherColor) => {
  return {
    type: 'group',
    left: 'center',
    bottom: '5px',
    children: [
      {
        type: 'rect',
        left: -5,
        top: 'middle',
        shape: {
          width: 16,
          height: 16
        },
        style: {
          fill: otherColor
        }
      },
      {
        type: 'text',
        left: 20,
        top: 'middle',
        style: {
          text: `${i18next.t("Other")}: ${formatNumber(originalOtherData?.value || 0, 'compact')} (${otherPercentage}%)`,
          fontSize: 14,
          fontWeight: 'normal',
          fill: '#666',
          textAlign: 'left',
          textVerticalAlign: 'middle'
        }
      }
    ]
  };
};

/**
 * Generate standard chart options for multi-display components
 *
 * @param {Array} transformedData - Transformed data array
 * @param {Object} otherData - Other data object
 * @param {Array} availableViews - Available view types
 * @param {number} otherPercentage - Percentage of "other" data (for floating label)
 * @param {Object} originalOtherData - Original other data object (for count in floating label)
 * @param {boolean} hideOtherInCharts - Whether to hide "other" in charts and show as floating label when >30%
 * @returns {Object} Chart options object
 */
const generateMultiDisplayChartOptions = (transformedData, otherData, availableViews, otherPercentage = 0, originalOtherData = null, hideOtherInCharts = false) => {
  const allData = [...transformedData, ...(otherData ? [otherData] : [])];

  // Get the color for the "other" data to use in the floating label
  const otherColor = originalOtherData?.itemStyle?.color || '#999';

  const options = {
    list: {},
    pie: {
      grid: {
        top: hideOtherInCharts && otherPercentage > 30 ? '2%' : '7%',
        right: '5%',
        bottom: hideOtherInCharts && otherPercentage > 30 ? '15%' : '5%',
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
      graphic: hideOtherInCharts && otherPercentage > 30 ? [createFloatingOtherLabel(originalOtherData, otherPercentage, otherColor)] : [],
      series: [
        {
          type: "pie",
          radius: ["30%", "70%"],
          center: hideOtherInCharts && otherPercentage > 30 ? ['50%', '45%'] : ['50%', '50%'],
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
        top: hideOtherInCharts && otherPercentage > 30 ? '2%' : '7%',
        right: '5%',
        bottom: hideOtherInCharts && otherPercentage > 30 ? '15%' : '5%',
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
      graphic: hideOtherInCharts && otherPercentage > 30 ? [createFloatingOtherLabel(originalOtherData, otherPercentage, otherColor)] : [],
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
  transformCountryMultiDisplayData,
  assembleMultiDisplayRows,
  extractData,
  generateMultiDisplayChartOptions
};