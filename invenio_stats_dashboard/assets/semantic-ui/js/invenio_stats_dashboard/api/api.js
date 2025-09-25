// Part of the Invenio-Stats-Dashboard extension for InvenioRDM
// Copyright (C) 2025 Mesh Research
//
// Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
// it under the terms of the MIT License; see LICENSE file for more details.

import { http } from "react-invenio-forms";
import { DASHBOARD_TYPES } from "../constants";
import { transformApiData } from "./dataTransformer";
import { generateTestStatsData } from "../components/test_data";

/**
 * API client for requesting stats to populate a stats dashboard.
 *
 * Returns a promise that resolves to an object with the following keys:
 * - record_deltas
 * - record_snapshots
 * - usage_deltas
 * - usage_snapshots
 *
 * Each property is an array of objects, each representing one day of stats.
 *
 * @param {string} communityId - The ID of the community to get stats for.
 * @param {string} dashboardType - The type of dashboard to get stats for.
 * @param {string} startDate - The start date of the stats. If not provided, the stats will begin at the earliest date in the data.
 * @param {string} endDate - The end date of the stats. If not provided, the stats will end at the current date or latest date in the data.
 * @param {string} dateBasis - The date basis for the query ("added", "created", "published"). Defaults to "added".
 *
 * @returns {Promise<Object>} - The stats data.
 */
const statsApiClient = {
	getStats: async (
		communityId,
		dashboardType,
		startDate = null,
		endDate = null,
		dateBasis = "added",
	) => {
		if (dashboardType === DASHBOARD_TYPES.GLOBAL) {
			communityId = "global";
		}

		const statCategories = [
			"usage-snapshot-category",
			"usage-delta-category",
			"record-snapshot-category",
			"record-delta-category",
		];

		let responses = [];

		for (let i = 0; i < statCategories.length; i++) {
			const category = statCategories[i];

			let requestBody = {
				[`${category}`]: {
					stat: `${category}`,
					params: {
						community_id: communityId,
						date_basis: dateBasis,
					},
				},
			};
			if (startDate) {
				requestBody[`${category}`].params.start_date = startDate;
			}
			if (endDate) {
				requestBody[`${category}`].params.end_date = endDate;
			}

			// Request with compression headers for optimal performance
			const response = await http.post(`/api/stats`, requestBody, {
				headers: {
					'Accept-Encoding': 'br, gzip',  // Prefer Brotli, fallback to Gzip
					'Accept': 'application/json'
				}
			});
			responses.push(response.data);
			console.log("response.data", response.data);
		}

		return responses;
	},
};

/**
 * Fetch stats data without caching
 *
 * @param {Object} params - Parameters for fetching stats
 * @param {string} params.communityId - The community ID (or 'global')
 * @param {string} params.dashboardType - The dashboard type
 * @param {Date} [params.startDate] - Start date (optional)
 * @param {Date} [params.endDate] - End date (optional)
 * @param {string} [params.dateBasis] - Date basis for the query ("added", "created", "published"). Defaults to "added".
 * @param {Function} [params.onStateChange] - Callback for state changes
 * @param {Function} [params.isMounted] - Function to check if component is still mounted
 * @param {boolean} [params.useTestData] - Whether to use test data instead of API
 *
 * @returns {Promise<Object>} Object containing:
 *   - stats: Fresh data from API (transformed)
 *   - lastUpdated: Timestamp of data fetch
 *   - error: Error object if fetch failed
 */
const fetchStats = async ({
	communityId,
	dashboardType,
	startDate = null,
	endDate = null,
	dateBasis = "added",
	onStateChange = null,
	isMounted = null,
	useTestData = false,
}) => {
	try {
		// Start loading state
		if (onStateChange && (!isMounted || isMounted())) {
			onStateChange({
				type: "loading_started",
				stats: null,
				isLoading: true,
				isUpdating: false,
				error: null,
			});
		}

		let transformedStats;

		if (useTestData) {
			transformedStats = await generateTestStatsData(startDate, endDate);
		} else {
			const rawStats = await statsApiClient.getStats(
				communityId,
				dashboardType,
				startDate,
				endDate,
				dateBasis,
			);
			transformedStats = transformApiData(rawStats);
		}

		console.log("Stats data fetched and transformed:", {
			communityId,
			dashboardType,
			startDate: startDate?.toISOString?.() || startDate,
			endDate: endDate?.toISOString?.() || endDate,
			dataSize: JSON.stringify(transformedStats).length,
			dataKeys: Object.keys(transformedStats || {}),
		});

		// Data loaded successfully
		if (onStateChange && (!isMounted || isMounted())) {
			onStateChange({
				type: "data_loaded",
				stats: transformedStats,
				isLoading: false,
				isUpdating: false,
				lastUpdated: Date.now(),
				error: null,
			});
		}

		return {
			stats: transformedStats,
			lastUpdated: Date.now(),
			error: null,
		};
	} catch (error) {
		console.error("Error fetching stats:", error);

		if (onStateChange && (!isMounted || isMounted())) {
			onStateChange({
				type: "error",
				stats: null,
				isLoading: false,
				isUpdating: false,
				error,
			});
		}

		return {
			stats: null,
			lastUpdated: null,
			error,
		};
	}
};

export {
	statsApiClient,
	fetchStats,
};
