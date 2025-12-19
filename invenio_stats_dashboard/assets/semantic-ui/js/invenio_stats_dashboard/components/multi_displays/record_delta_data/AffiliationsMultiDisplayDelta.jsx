// Part of the Invenio-Stats-Dashboard extension for InvenioRDM
// Copyright (C) 2025 Mesh Research
//
// Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
// it under the terms of the MIT License; see LICENSE file for more details.

import React, { useState, useEffect } from "react";
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { StatsMultiDisplay } from "../../shared_components/StatsMultiDisplay";
import { PropTypes } from "prop-types";
import { useStatsDashboard } from "../../../context/StatsDashboardContext";
import { CHART_COLORS, RECORD_START_BASES } from "../../../constants";
import { formatDate } from "../../../utils";
import {
	transformMultiDisplayData,
	assembleMultiDisplayRows,
	extractData,
	generateMultiDisplayChartOptions,
} from "../../../utils/multiDisplayHelpers";

const AffiliationsMultiDisplayDelta = ({
	title = i18next.t("Affiliations"),
	icon: labelIcon = "university",
	headers = [i18next.t("Affiliation"), i18next.t("Works")],
	default_view,
	pageSize = 10,
	available_views = ["list", "pie", "bar"],
	hideOtherInCharts = false,
	...otherProps
}) => {
	const { community, stats, recordStartBasis, dateRange, isLoading } =
		useStatsDashboard();
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

	// Extract and process affiliations data using DELTA data (period-restricted)
	const rawAffiliations = extractData(
		stats,
		recordStartBasis,
		"affiliations",
		"records",
		dateRange,
		true,
		false,
	);

	const {
		transformedData,
		otherData,
		originalOtherData,
		totalCount,
		otherPercentage,
	} = transformMultiDisplayData(
		rawAffiliations,
		community,
		pageSize,
		"metadata.creators.affiliations.id",
		CHART_COLORS.secondary,
		hideOtherInCharts,
		null,
		true, // isDelta = true for delta data
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
			headers={headers}
			defaultViewMode={default_view}
			available_views={available_views}
			pageSize={pageSize}
			totalCount={totalCount}
			chartOptions={chartOptions}
			rows={rowsWithLinks}
			label={"affiliations"}
			isLoading={isLoading}
			{...otherProps}
		/>
	);
};

AffiliationsMultiDisplayDelta.propTypes = {
	title: PropTypes.string,
	icon: PropTypes.string,
	headers: PropTypes.array,
	default_view: PropTypes.string,
	pageSize: PropTypes.number,
	available_views: PropTypes.arrayOf(PropTypes.string),
	hideOtherInCharts: PropTypes.bool,
};

export { AffiliationsMultiDisplayDelta };
