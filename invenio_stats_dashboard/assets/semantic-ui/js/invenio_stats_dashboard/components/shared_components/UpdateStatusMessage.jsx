/**
 * Part of Invenio-Stats-Dashboard
 * Copyright (C) 2025 Mesh Research
 *
 * Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
 * it under the terms of the MIT License; see LICENSE file for more details.
 */

import React from "react";
import { Icon, Loader } from "semantic-ui-react";
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { formatCacheTimestamp } from "../../utils/dates";
import PropTypes from "prop-types";

/**
 * Component to display update status messages for the stats dashboard
 * Shows "last updated" with timestamp, and "updating" message while updating
 */
const UpdateStatusMessage = ({
	isUpdating,
	lastUpdated,
	isLoading,
	className = "",
	size = "small",
}) => {
	if (!isUpdating && !lastUpdated) {
		return null;
	}

	const showUpdating = !isLoading && isUpdating;

	return (
		<section
			className={`stats-update-status ${className}`}
			data-testid="update-status-message"
		>
			{lastUpdated && (
				<div className="stats-last-updated-container">
					<Icon name="clock outline" />
					<span className="stats-last-updated-text">
						{i18next.t("Last updated: {{timestamp}}", {
							timestamp: formatCacheTimestamp(lastUpdated),
						})}
					</span>
				</div>
			)}
			{showUpdating && (
				<div className="stats-updating-container">
					<Loader active inline size="mini" />
					<span className="stats-updating-text">
						{i18next.t("Updating data...")}
					</span>
				</div>
			)}
		</section>
	);
};

UpdateStatusMessage.propTypes = {
	isUpdating: PropTypes.bool,
	isLoading: PropTypes.bool,
	lastUpdated: PropTypes.number,
	className: PropTypes.string,
	size: PropTypes.oneOf([
		"mini",
		"tiny",
		"small",
		"large",
		"big",
		"huge",
		"massive",
	]),
};

export { UpdateStatusMessage };
