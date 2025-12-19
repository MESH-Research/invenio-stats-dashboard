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

const FundersMultiDisplayViewsDelta = ({
	title = i18next.t("Funders"),
	icon: labelIcon = "money bill alternate",
	pageSize = 10,
	headers = [i18next.t("Funder"), i18next.t("Views")],
	default_view = "pie",
	available_views = ["pie", "bar", "list"],
	hideOtherInCharts = false,
	...otherProps
}) => {
	const { community, stats, dateRange, isLoading } = useStatsDashboard();
	const [subtitle, setSubtitle] = useState(null);

	useEffect(() => {
		if (dateRange) {
			setSubtitle(
				i18next.t("during") +
					" " +
					formatDate(dateRange.start, "day", true, dateRange.end),
			);
		}
	}, [dateRange]);

	// Extract usage delta data for views
	const rawData = extractData(
		stats,
		null,
		"funders",
		"viewUniqueRecords",
		dateRange,
		true,
		true, // isUsageData = true
	);
	const globalData = extractData(
		stats,
		null,
		"global",
		"viewUniqueRecords",
		dateRange,
		true,
		true, // isUsageData = true
	);

	const {
		transformedData,
		otherData,
		originalOtherData,
		totalCount,
		otherPercentage,
	} = transformMultiDisplayData(
		rawData,
		community,
		pageSize,
		"metadata.funding.funder",
		CHART_COLORS.secondary,
		hideOtherInCharts,
		globalData,
		true,
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
			label={"funders"}
			headers={headers}
			rows={rowsWithLinks}
			chartOptions={chartOptions}
			defaultViewMode={default_view}
			isLoading={isLoading}
			isDelta={true}
			dateRangeEnd={dateRange?.end}
			metricType="views"
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

FundersMultiDisplayViewsDelta.propTypes = {
	title: PropTypes.string,
	icon: PropTypes.string,
	headers: PropTypes.array,
	rows: PropTypes.array,
	default_view: PropTypes.string,
	pageSize: PropTypes.number,
	available_views: PropTypes.arrayOf(PropTypes.string),
	hideOtherInCharts: PropTypes.bool,
	width: PropTypes.number,
};

export { FundersMultiDisplayViewsDelta };
