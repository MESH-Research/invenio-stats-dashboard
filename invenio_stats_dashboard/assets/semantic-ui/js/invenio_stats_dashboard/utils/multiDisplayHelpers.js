// Part of the Invenio-Stats-Dashboard extension for InvenioRDM
// Copyright (C) 2025 Mesh Research
//
// Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
// it under the terms of the MIT License; see LICENSE file for more details.

import React from "react";
import { formatNumber } from "./numbers";
import { CHART_COLORS, RECORD_START_BASES } from "../constants";
import { extractLocalizedLabel } from "./i18n";
import { filterSeriesArrayByDate } from "./filters";
import { reconstructDateFromMMDD } from "./dates";
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { getCountryNames } from "./mapHelpers";
import { transformItemForChart } from "./nameTransformHelpers";
import { getOtherIdsForCategory } from "./chartHelpers";

const FILTER_PATHS = {
	"metadata.languages.id": "language",
	"metadata.resource_type.id": "resource_type",
	"access.status": "access_status",
	"files.entries.ext": "file_type",
};

const COMPOUND_FILTERS = ["resource_type"];

function makeLinkURL(searchPath, community, item) {
	if (!searchPath) {
		return null;
	}

	const searchUrl = !!community
		? `/collections/${community.id}/records`
		: "/search";

	const isFilterField = Object.keys(FILTER_PATHS).includes(searchPath);

	const isFilterName = Object.values(FILTER_PATHS).includes(searchPath);

	let searchField =
		isFilterName || !isFilterField ? searchPath : FILTER_PATHS[searchPath];

	let itemValue = item;

	if (COMPOUND_FILTERS.includes(searchField)) {
		const itemValueStem = itemValue?.split("-")[0];
		itemValue = `${itemValueStem}%2Binner:${item}`;
	}

	const q_param = !!isFilterField || !!isFilterName ? "q=&f" : "q";
	const q_term =
		!!isFilterField || !!isFilterName ? itemValue : `"${itemValue}"`;

	return `${searchUrl}?${q_param}=${searchField}:${q_term}`;
}

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
 * @param {string} categoryName - Optional category name (e.g., 'publishers', 'languages') to determine which IDs should be treated as "other"
 * @returns {Object} Object containing transformedData, otherData, originalOtherData, totalCount, and otherPercentage
 */

const transformMultiDisplayData = (
	rawData,
	community = null,
	pageSize = 10,
	searchField,
	colorPalette = CHART_COLORS.secondary,
	hideOtherInCharts = false,
	globalData = null,
	isDelta = false,
	categoryName = null,
) => {
	if (!rawData || !Array.isArray(rawData)) {
		return {
			transformedData: [],
			otherData: null,
			originalOtherData: null,
			totalCount: 0,
			otherPercentage: 0,
		};
	}

	// Get IDs that should be treated as "other" for this category
	// If categoryName is not provided, try to infer it from searchField for backward compatibility
	const inferredCategoryName =
		categoryName ||
		(searchField && searchField.includes("publisher") ? "publishers" : null);
	const otherIds = getOtherIdsForCategory(inferredCategoryName);

	// Filter out items with IDs that should be treated as "other"
	const filteredRawData =
		otherIds.length > 0
			? rawData.filter((item) => !otherIds.includes(item.id))
			: rawData;

	// Calculate value for each item based on data type
	const getItemValue = (item) => {
		if (!item?.data || !Array.isArray(item.data)) return 0;

		if (isDelta) {
			// For delta data, sum all data points
			return item.data.reduce((sum, point) => sum + (point?.[1] || 0), 0);
		} else {
			// For snapshot data, take the first (and only) data point
			return item.data[0]?.[1] || 0;
		}
	};

	// Calculate total count from subcount items (for backward compatibility)
	// Note: IDs configured as "other" are excluded from this count
	const subcountTotalCount = filteredRawData.reduce(
		(sum, item) => sum + getItemValue(item),
		0,
	);

	// Calculate global total count if global data is provided
	let globalTotalCount = 0;
	if (globalData && Array.isArray(globalData) && globalData.length > 0) {
		const globalSeries = globalData[0]; // Global data is typically a single series
		if (globalSeries && globalSeries.data && globalSeries.data.length > 0) {
			if (isDelta) {
				// For delta data, sum all values
				globalTotalCount = globalSeries.data.reduce(
					(sum, point) => sum + (point?.[1] || 0),
					0,
				);
			} else {
				// For snapshot data, use first (and only) data point
				// (data should already be filtered to single point by extractData)
				globalTotalCount = globalSeries.data[0]?.[1] || 0;
			}
		}
	}

	// Use global total if available, otherwise fall back to subcount total
	const totalCount =
		globalTotalCount > 0 ? globalTotalCount : subcountTotalCount;

	// Transform all items first, then sort and slice
	// Use filteredRawData (which excludes "unknown" for publisher data)
	const allTransformedData = filteredRawData.map((item) => {
		const value = getItemValue(item);
		const percentage =
			totalCount > 0 ? Math.round((value / totalCount) * 100) : 0;
		const currentLanguage = i18next.language || "en";

		// Transform item for chart display with appropriate name forms
		const transformedItem = transformItemForChart(
			item,
			searchField,
			currentLanguage,
			extractLocalizedLabel,
		);

		return {
			name: transformedItem.name,
			fullName: transformedItem.fullName,
			isAbbreviated: transformedItem.isAbbreviated,
			value: value,
			percentage: percentage,
			id: item.id,
			link: makeLinkURL(searchField, community, item.id),
			// Color will be assigned after sorting
		};
	});

	// Sort by value (descending) and slice
	const sortedTransformedData = allTransformedData.sort(
		(a, b) => b.value - a.value,
	);

	// Assign colors based on sorted position to ensure adjacent items have different colors
	sortedTransformedData.forEach((item, index) => {
		item.itemStyle = {
			color: colorPalette[index % colorPalette.length][1],
		};
	});
	const transformedData = sortedTransformedData.slice(0, pageSize);
	const otherItems = sortedTransformedData.slice(pageSize);

	const otherData =
		otherItems.length > 0
			? otherItems.reduce(
					(acc, item) => {
						acc.value += item.value;
						return acc;
					},
					{
						id: "other",
						name: i18next.t("Other"),
						value: 0,
						itemStyle: {
							color: colorPalette[colorPalette.length - 1][1],
						},
					},
				)
			: null;

	if (otherData) {
		otherData.percentage =
			totalCount > 0 ? Math.round((otherData.value / totalCount) * 100) : 0;
	}

	const otherPercentage = otherData ? otherData.percentage : 0;
	const shouldHideOther = hideOtherInCharts && otherPercentage > 30;

	// Filter out zero values from the final data
	const filteredTransformedData = transformedData.filter(
		(item) => item.value !== 0,
	);
	const filteredOtherData =
		otherData && otherData.value !== 0 ? otherData : null;

	return {
		transformedData: filteredTransformedData,
		otherData: shouldHideOther ? null : filteredOtherData,
		originalOtherData: otherData, // Keep original for floating label count
		totalCount,
		otherPercentage,
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
const transformCountryMultiDisplayData = (
	rawData,
	pageSize = 10,
	searchField,
	colorPalette = CHART_COLORS.secondary,
	hideOtherInCharts = false,
	globalData = null,
	isDelta = false,
) => {
	if (!rawData || !Array.isArray(rawData)) {
		return {
			transformedData: [],
			otherData: null,
			originalOtherData: null,
			totalCount: 0,
			otherPercentage: 0,
		};
	}

	// Calculate value for each item based on data type
	const getItemValue = (item) => {
		if (!item?.data || !Array.isArray(item.data)) return 0;

		if (isDelta) {
			// For delta data, sum all data points
			return item.data.reduce((sum, point) => sum + (point?.[1] || 0), 0);
		} else {
			// For snapshot data, take the first (and only) data point
			return item.data[0]?.[1] || 0;
		}
	};

	// Filter out "imported" from rawData before any calculations (it should be completely discarded)
	const countriesData = rawData.filter((item) => item.id !== "imported");

	// Calculate total count from subcount items, excluding "imported" (for backward compatibility)
	const subcountTotalCount = countriesData.reduce(
		(sum, item) => sum + getItemValue(item),
		0,
	);

	// Calculate global total count if global data is provided
	// Note: We assume global data already excludes "imported" or we need to subtract it
	let globalTotalCount = 0;
	if (globalData && Array.isArray(globalData) && globalData.length > 0) {
		const globalSeries = globalData[0]; // Global data is typically a single series
		if (globalSeries && globalSeries.data && globalSeries.data.length > 0) {
			if (isDelta) {
				// For delta data, sum all values
				globalTotalCount = globalSeries.data.reduce(
					(sum, point) => sum + (point?.[1] || 0),
					0,
				);
			} else {
				// For snapshot data, use first (and only) data point
				// (data should already be filtered to single point by extractData)
				globalTotalCount = globalSeries.data[0]?.[1] || 0;
			}
		}
	}

	// Use global total if available, otherwise fall back to subcount total (both exclude "imported")
	const totalCount =
		globalTotalCount > 0 ? globalTotalCount : subcountTotalCount;

	// Transform all items (excluding "imported" which was already filtered)
	const allTransformedData = countriesData.map((item) => {
		const value = getItemValue(item);
		const percentage =
			totalCount > 0 ? Math.round((value / totalCount) * 100) : 0;
		const countryCode = item.name || item.id;
		const countryName = getCountryNames(countryCode).displayName;
		return {
			name: countryName,
			value: value,
			percentage: percentage,
			id: item.id,
			link: searchField ? `/search?q=${searchField}:"${item.id}"` : null,
			// Color will be assigned after sorting
		};
	});

	// Filter out items with zero values
	const nonZeroTransformedData = allTransformedData.filter(
		(item) => item.value !== 0,
	);

	// Sort countries
	const sortedTransformedData = nonZeroTransformedData.sort(
		(a, b) => b.value - a.value,
	);

	// Assign colors based on sorted position to ensure adjacent items have different colors
	sortedTransformedData.forEach((item, index) => {
		item.itemStyle = {
			color: colorPalette[index % colorPalette.length][1],
		};
	});
	const transformedData = sortedTransformedData.slice(0, pageSize);
	const otherItems = sortedTransformedData.slice(pageSize);

	// Calculate "other" from non-visible countries only (excluding "imported")
	const otherData =
		otherItems.length > 0
			? otherItems.reduce(
					(acc, item) => {
						acc.value += item.value;
						return acc;
					},
					{
						id: "other",
						name: i18next.t("Other"),
						value: 0,
						itemStyle: {
							color: colorPalette[colorPalette.length - 1][1],
						},
					},
				)
			: null;

	if (otherData) {
		otherData.percentage =
			totalCount > 0 ? Math.round((otherData.value / totalCount) * 100) : 0;
	}

	const otherPercentage = otherData ? otherData.percentage : 0;
	const shouldHideOther = hideOtherInCharts && otherPercentage > 30;

	// Filter out zero values from the final data
	const filteredTransformedData = transformedData.filter(
		(item) => item.value !== 0,
	);
	const filteredOtherData =
		otherData && otherData.value !== 0 ? otherData : null;

	return {
		transformedData: filteredTransformedData,
		otherData: shouldHideOther ? null : filteredOtherData,
		originalOtherData: otherData, // Keep original for floating label count
		totalCount,
		otherPercentage,
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
	const allData = [...transformedData, ...(otherData ? [otherData] : [])];

	return allData.map(({ name, value, percentage, link }) => [
		null,
		link ? (
			<a href={link} target="_blank" rel="noopener noreferrer">
				{name}
			</a>
		) : (
			name
		),
		`${formatNumber(value, "compact")} (${percentage}%)`,
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
const extractData = (
	stats,
	recordStartBasis,
	category,
	metric,
	dateRange,
	isDelta = false,
	isUsageData = false,
) => {
	let allItems;

	if (isUsageData) {
		// Extract usage data
		allItems = stats?.flatMap((yearlyStats) => {
			const seriesArray =
				yearlyStats?.[isDelta ? "usageDeltaData" : "usageSnapshotData"]?.[
					category
				]?.[metric] || [];
			// Convert MM-DD dates to full YYYY-MM-DD format before merging years
			return seriesArray.map((series) => ({
				...series,
				data: series.data?.map((dataPoint) => {
					const [date, value] = dataPoint;
					return [reconstructDateFromMMDD(date, yearlyStats.year), value];
				}),
			}));
		});
	} else {
		// Extract record data
		const seriesCategoryMap = isDelta
			? {
					[RECORD_START_BASES.ADDED]: "recordDeltaDataAdded",
					[RECORD_START_BASES.CREATED]: "recordDeltaDataCreated",
					[RECORD_START_BASES.PUBLISHED]: "recordDeltaDataPublished",
				}
			: {
					[RECORD_START_BASES.ADDED]: "recordSnapshotDataAdded",
					[RECORD_START_BASES.CREATED]: "recordSnapshotDataCreated",
					[RECORD_START_BASES.PUBLISHED]: "recordSnapshotDataPublished",
				};

		allItems = stats?.flatMap((yearlyStats) => {
			const seriesArray =
				yearlyStats?.[seriesCategoryMap[recordStartBasis]]?.[category]?.[
					metric
				] || [];
			// Convert MM-DD dates to full YYYY-MM-DD format before merging years
			return seriesArray.map((series) => ({
				...series,
				data: series.data?.map((dataPoint) => {
					const [date, value] = dataPoint;
					return [reconstructDateFromMMDD(date, yearlyStats.year), value];
				}),
			}));
		});
	}

	if (!allItems || allItems.length === 0) {
		return [];
	}

	// Group items by ID and combine their time series data
	const combinedItems = {};

	allItems.forEach((item) => {
		const itemId = item.id;

		if (!combinedItems[itemId]) {
			combinedItems[itemId] = {
				id: itemId,
				name: item.name,
				data: [],
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
const createFloatingOtherLabel = (
	originalOtherData,
	otherPercentage,
	otherColor,
) => {
	return {
		type: "group",
		left: "center",
		bottom: "5px",
		children: [
			{
				type: "rect",
				left: -5,
				top: "middle",
				shape: {
					width: 16,
					height: 16,
				},
				style: {
					fill: otherColor,
				},
			},
			{
				type: "text",
				left: 20,
				top: "middle",
				style: {
					text: `${i18next.t("Other")}: ${formatNumber(originalOtherData?.value || 0, "compact")} (${otherPercentage}%)`,
					fontSize: 14,
					fontWeight: "normal",
					fill: "#666",
					textAlign: "left",
					textVerticalAlign: "middle",
				},
			},
		],
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
const generateMultiDisplayChartOptions = (
	transformedData,
	otherData,
	availableViews,
	otherPercentage = 0,
	originalOtherData = null,
	hideOtherInCharts = false,
) => {
	const allData = [...transformedData, ...(otherData ? [otherData] : [])];

	// Get the color for the "other" data to use in the floating label
	const otherColor = originalOtherData?.itemStyle?.color || "#999";

	const options = {
		list: {},
		pie: {
			grid: {
				top: hideOtherInCharts && otherPercentage > 30 ? "6%" : "11%",
				right: "9%",
				bottom: hideOtherInCharts && otherPercentage > 30 ? "19%" : "9%",
				left: "6%",
				containLabel: true,
			},
			tooltip: {
				trigger: "item",
				confine: true,
				appendToBody: false,
				formatter: (params) => {
					const displayName = params.data.fullName || params.name;
					return `<div>
            ${displayName}: ${formatNumber(params.value, "compact")} (${params.data.percentage}%)
          </div>`;
				},
			},
			graphic:
				hideOtherInCharts && otherPercentage > 30
					? [
							createFloatingOtherLabel(
								originalOtherData,
								otherPercentage,
								otherColor,
							),
						]
					: [],
			series: [
				{
					type: "pie",
					radius: ["30%", "70%"],
					center:
						hideOtherInCharts && otherPercentage > 30
							? ["50%", "45%"]
							: ["50%", "50%"],
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
				top: hideOtherInCharts && otherPercentage > 30 ? "6%" : "6%",
				right: "9%",
				bottom: hideOtherInCharts && otherPercentage > 30 ? "19%" : "6%",
				left: "6%",
				containLabel: true,
			},
			tooltip: {
				trigger: "item",
				confine: true,
				appendToBody: false,
				formatter: (params) => {
					const displayName = params.data.fullName || params.name;
					return `<div>
            ${displayName}: ${formatNumber(params.value, "compact")} (${params.data.percentage}%)
          </div>`;
				},
			},
			graphic:
				hideOtherInCharts && otherPercentage > 30
					? [
							createFloatingOtherLabel(
								originalOtherData,
								otherPercentage,
								otherColor,
							),
						]
					: [],
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
					barMaxWidth: 50,
					data: allData.map((item, index) => {
						const maxValue = Math.max(...allData.map((d) => d.value));
						return {
							value: item.value,
							percentage: item.percentage,
							id: item.id,
							link: item.link,
							itemStyle: item.itemStyle,
							label: {
								show: true,
								formatter: "{b}",
								fontSize: 14,
								position: item.value < maxValue * 0.3 ? "right" : "inside",
								color:
									item.value < maxValue * 0.3 ? item.itemStyle.color : "#fff",
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
		Object.entries(options).filter(([key]) => availableViews.includes(key)),
	);
};

/**
 * Wraps a click event handler to prevent navigation for "other" values
 * This prevents clicking on "other" chart regions from navigating to about:blank
 *
 * @param {Function} clickHandler - The original click handler function
 * @returns {Function} Wrapped click handler that filters out "other" clicks
 */
const wrapClickHandler = (clickHandler) => {
	return (params) => {
		if (
			!params.data ||
			params.data.id === "other" ||
			(params.data.link === undefined && !params.data.id)
		) {
			return;
		}
		clickHandler(params);
	};
};

/**
 * Disables navigation for invalid links (e.g., "other" values) in chart click handlers
 * This prevents clicking on "other" chart regions from navigating to about:blank
 *
 * @param {Object} onEvents - The original onEvents object from ECharts
 * @returns {Object} onEvents object with click handler that filters invalid links
 */
const disableInvalidLinks = (onEvents) => {
	if (!onEvents || !onEvents.click) {
		return onEvents;
	}
	return {
		...onEvents,
		click: wrapClickHandler(onEvents.click),
	};
};

export {
	transformMultiDisplayData,
	transformCountryMultiDisplayData,
	assembleMultiDisplayRows,
	extractData,
	generateMultiDisplayChartOptions,
	wrapClickHandler,
	disableInvalidLinks,
};
