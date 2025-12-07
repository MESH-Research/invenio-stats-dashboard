/**
 * Part of Invenio-Stats-Dashboard
 * Copyright (C) 2025 Mesh Research
 *
 * Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
 * it under the terms of the MIT License; see LICENSE file for more details.
 */

import React from "react";
import { StatsDashboardLayout } from "./StatsDashboardLayout";
import { StatsDashboardDisabledMessage } from "./StatsDashboardDisabledMessage";
import { DASHBOARD_TYPES } from "./constants";
import PropTypes from "prop-types";

/**
 * Community stats dashboard layout
 */
const CommunityStatsDashboardLayout = ({
	community,
	dashboardConfig,
	stats,
}) => {
	const dashboardType = DASHBOARD_TYPES.COMMUNITY;
	const dashboardEnabled = community.custom_fields["stats:dashboard_enabled"];
	console.log("dashboardConfig:", dashboardConfig);

	// Community-specific configuration
	const containerClassNames = `${dashboardType}-stats-dashboard communities-stats ${community.slug}`;
	const sidebarClassNames = "communities-detail-left-sidebar";
	const bodyClassNames = "communities-detail-body communities-detail-stats";

	const disabledMessage =
		!!dashboardConfig.dashboard_enabled_communities &&
		!!dashboardConfig.dashboard_enabled_global
			? dashboardConfig.disabled_message
			: dashboardConfig.disabled_message_global;

	const getStatsParams = (community, dashboardType) => [
		community.id,
		dashboardType,
	];

	return !!dashboardEnabled ? (
		<StatsDashboardLayout
			dashboardConfig={dashboardConfig}
			dashboardType={dashboardType}
			community={community}
			showSubheader={false}
			containerClassNames={containerClassNames}
			sidebarClassNames={sidebarClassNames}
			bodyClassNames={bodyClassNames}
			getStatsParams={getStatsParams}
			stats={stats}
		/>
	) : (
		<StatsDashboardDisabledMessage
			msg={disabledMessage}
			dashboardType={dashboardType}
		/>
	);
};

CommunityStatsDashboardLayout.propTypes = {
	community: PropTypes.object.isRequired,
	dashboardConfig: PropTypes.object.isRequired,
	stats: PropTypes.object,
};

export { CommunityStatsDashboardLayout };
