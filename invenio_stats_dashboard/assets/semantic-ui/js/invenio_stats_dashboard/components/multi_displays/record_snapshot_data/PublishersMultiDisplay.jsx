// Part of the Invenio-Stats-Dashboard extension for InvenioRDM
// Copyright (C) 2025 Mesh Research
//
// Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
// it under the terms of the MIT License; see LICENSE file for more details.

import React, { useState, useEffect } from "react";
import PropTypes from "prop-types";
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { StatsMultiDisplay } from "../../shared_components/StatsMultiDisplay";
import { useStatsDashboard } from "../../../context/StatsDashboardContext";
import { CHART_COLORS } from "../../../constants";
import { formatDate } from "../../../utils";
import {
	transformMultiDisplayData,
	assembleMultiDisplayRows,
	extractData,
	generateMultiDisplayChartOptions,
} from "../../../utils/multiDisplayHelpers";

const PublishersMultiDisplay = ({
	title = i18next.t("Publishers"),
	icon: labelIcon = "building",
	headers = [i18next.t("Publisher"), i18next.t("Works")],
	default_view = "pie",
	pageSize = 10,
	available_views = ["pie", "bar", "list"],
	hideOtherInCharts = false,
	...otherProps
}) => {
	const { stats, recordStartBasis, dateRange, isLoading } = useStatsDashboard();
	const [subtitle, setSubtitle] = useState(null);

	useEffect(() => {
		if (dateRange) {
			setSubtitle(
				i18next.t("as of") + " " + formatDate(dateRange.end, "day", true),
			);
		}
	}, [dateRange]);

	// Extract and process publishers data
	const rawPublishers = extractData(
		stats,
		recordStartBasis,
		"publishers",
		"records",
		dateRange,
		false,
		false,
	);
	const globalData = extractData(
		stats,
		recordStartBasis,
		"global",
		"records",
		dateRange,
		false,
		false,
	);

	const {
		transformedData,
		otherData,
		originalOtherData,
		totalCount,
		otherPercentage,
	} = transformMultiDisplayData(
		rawPublishers,
		pageSize,
		"metadata.publisher",
		CHART_COLORS.secondary,
		hideOtherInCharts,
		globalData,
		false, // isDelta = false for snapshot data
	);
	const rowsWithLinks = assembleMultiDisplayRows(transformedData, otherData);

	const chartOptions = generateMultiDisplayChartOptions(
		transformedData,
		otherData,
		available_views,
		otherPercentage,
		originalOtherData,
		hideOtherInCharts,
	);

	return (
		<StatsMultiDisplay
			title={title}
			subtitle={subtitle}
			icon={labelIcon}
			label={"publishers"}
			headers={headers}
			rows={rowsWithLinks}
			chartOptions={chartOptions}
			defaultViewMode={default_view}
			isLoading={isLoading}
			isDelta={false}
			dateRangeEnd={dateRange?.end}
			onEvents={{
				click: (params) => {
					if (params.data && params.data.id) {
						window.open(params.data.link, "_blank");
					}
				},
			}}
			{...otherProps}
		/>
	);
};

PublishersMultiDisplay.propTypes = {
	title: PropTypes.string,
	icon: PropTypes.string,
	headers: PropTypes.array,
	rows: PropTypes.array,
	default_view: PropTypes.string,
	pageSize: PropTypes.number,
	available_views: PropTypes.arrayOf(PropTypes.string),
	hideOtherInCharts: PropTypes.bool,
};

export { PublishersMultiDisplay };
