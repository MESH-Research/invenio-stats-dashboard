// Part of the Invenio-Stats-Dashboard extension for InvenioRDM
// Copyright (C) 2025 Mesh Research
//
// Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
// it under the terms of the MIT License; see LICENSE file for more details.

import React, { useState, useEffect } from "react";
import PropTypes from "prop-types";
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { StatsMultiDisplay } from "../../shared_components/StatsMultiDisplay";
import { formatNumber } from "../../../utils/numbers";
import { CHART_COLORS } from "../../../constants";
import { fetchRecords } from "../../../api/api";
import { useStatsDashboard } from "../../../context/StatsDashboardContext";
import {
	generateMultiDisplayChartOptions,
} from "../../../utils/multiDisplayHelpers";
import { createTruncatedTitle } from "../../../utils/textTruncation";

const MostDownloadedRecordsMultiDisplay = ({
	title = undefined,
	icon = "download",
	pageSize = 10,
	headers = [i18next.t("Record"), i18next.t("Downloads")],
	default_view,
	available_views = ["list", "pie", "bar"],
	maxHeight = null, // Optional max height for scrollable list
	community = null,
	...otherProps
}) => {
	const { dateRange } = useStatsDashboard();
	const [records, setRecords] = useState([]);
	const [isLoading, setIsLoading] = useState(true);
	const [error, setError] = useState(null);

	const fetchUrl = !!community ? community?.links?.records : "/api/records";

	useEffect(() => {
		const loadMostDownloadedRecords = async () => {
			try {
				setIsLoading(true);
				setError(null);
				const response = await fetchRecords(
					"mostdownloaded",
					1,
					pageSize,
					dateRange,
					fetchUrl,
				);
				setRecords(response.hits?.hits || []);
			} catch (err) {
				console.error("Error loading most downloaded records:", err);
				setError(err);
			} finally {
				setIsLoading(false);
			}
		};

		loadMostDownloadedRecords();
	}, [pageSize, dateRange]);

	// Transform the API response into the format expected by StatsMultiDisplay
	const transformedData = records.map((record, index) => ({
		name: record.metadata?.title || "Untitled",
		value: record.stats?.all_versions?.downloads || 0, // Use stats.all_versions.downloads
		percentage: 0, // We'll calculate this if needed
		link: record.links?.self_html,
		itemStyle: {
			color: CHART_COLORS.secondary[index % CHART_COLORS.secondary.length],
		},
	}));

	const rowsWithLinks = transformedData.map(({ name, value, link }) => [
		null,
		createTruncatedTitle(
			name,
			link ? (
				<a href={link} target="_blank" rel="noopener noreferrer">
					{name}
				</a>
			) : null,
			60,
		),
		`${formatNumber(value, "compact")}`,
	]);

	const chartOptions = generateMultiDisplayChartOptions(
		transformedData,
		null,
		available_views,
	);

	return (
		<StatsMultiDisplay
			title={title || i18next.t("Most Downloaded Records")}
			subtitle={i18next.t("all time")}
			icon={icon}
			label="downloaded_records"
			headers={headers}
			rows={rowsWithLinks}
			chartOptions={chartOptions}
			defaultViewMode={default_view || available_views[0]}
			pageSize={pageSize}
			isLoading={isLoading}
			maxHeight={maxHeight}
			onEvents={{
				click: (params) => {
					if (params.data && params.data.link) {
						window.open(params.data.link, "_blank");
					}
				},
			}}
			{...otherProps}
		/>
	);
};

MostDownloadedRecordsMultiDisplay.propTypes = {
	title: PropTypes.string,
	icon: PropTypes.string,
	pageSize: PropTypes.number,
	headers: PropTypes.array,
	default_view: PropTypes.string,
	available_views: PropTypes.arrayOf(PropTypes.string),
	maxHeight: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
	width: PropTypes.number,
};

export { MostDownloadedRecordsMultiDisplay };
