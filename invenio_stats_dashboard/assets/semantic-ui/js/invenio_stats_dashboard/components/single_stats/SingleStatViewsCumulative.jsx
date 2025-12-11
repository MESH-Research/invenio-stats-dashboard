// Part of the Invenio-Stats-Dashboard extension for InvenioRDM
// Copyright (C) 2025 Mesh Research
//
// Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
// it under the terms of the MIT License; see LICENSE file for more details.

import React, { useState, useEffect } from "react";
import PropTypes from "prop-types";
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { SingleStatBox } from "../shared_components/SingleStatBox";
import { formatNumber, formatDate } from "../../utils";
import { useStatsDashboard } from "../../context/StatsDashboardContext";
import { extractUsageSnapshotValue } from "../../utils/singleStatHelpers";

const SingleStatViewsCumulative = ({
	title = i18next.t("Cumulative Views"),
	icon = "eye",
	compactThreshold = 1_000_000,
}) => {
	const { stats, dateRange, isLoading } = useStatsDashboard();
	const [description, setDescription] = useState(null);

	useEffect(() => {
		if (dateRange) {
			setDescription(
				i18next.t("as of") + " " + formatDate(dateRange.end, "day", true),
			);
		}
	}, [dateRange]);

	// Extract cumulative views value using the helper function
	const value = extractUsageSnapshotValue(
		stats,
		"viewUniqueRecords",
		"global",
		dateRange,
	);

	return (
		<SingleStatBox
			title={title}
			value={formatNumber(value, "compact", { compactThreshold })}
			rawValue={value}
			icon={icon}
			isLoading={isLoading}
			{...(description && { description })}
		/>
	);
};

SingleStatViewsCumulative.propTypes = {
	title: PropTypes.string,
	icon: PropTypes.string,
	compactThreshold: PropTypes.number,
};

export { SingleStatViewsCumulative };
