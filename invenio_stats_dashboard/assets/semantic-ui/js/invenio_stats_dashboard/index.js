// Part of the Invenio-Stats-Dashboard extension for InvenioRDM
// Copyright (C) 2025 Mesh Research
//
// Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
// it under the terms of the MIT License; see LICENSE file for more details.

import React from "react";
import ReactDOM from "react-dom";
import { StatsDashboardPage } from "./StatsDashboardPage";
import { StatsDashboardLayout } from "./StatsDashboardLayout";
import { CommunityStatsDashboardLayout } from "./CommunityStatsDashboardLayout";
import { GlobalStatsDashboardLayout } from "./GlobalStatsDashboardLayout";

// Initialize the dashboard if the container exists
const domContainer = document.getElementById("stats-dashboard");
console.log("domContainer", domContainer);
console.log(JSON.parse(domContainer.dataset.dashboardConfig || "{}"));
if (domContainer) {
	const config = JSON.parse(domContainer.dataset.dashboardConfig || "{}");
	console.log("config", config);
	console.log("community", domContainer.dataset.community);
	const community = ["None", null, undefined].includes(
		domContainer.dataset.community,
	)
		? null
		: JSON.parse(domContainer.dataset.community);

	let DashboardComponent;
	switch (config.dashboard_type) {
		case "community":
			DashboardComponent = CommunityStatsDashboardLayout;
			break;
		case "global":
			DashboardComponent = GlobalStatsDashboardLayout;
			break;
		default:
			DashboardComponent = StatsDashboardLayout;
	}

	ReactDOM.render(
		<DashboardComponent
			{...(community && { community })}
			dashboardConfig={config}
		/>,
		domContainer,
	);
}

// Export all components
export * from "./components";
export * from "./api";
export * from "./utils";
export * from "./context";
export {
	CommunityStatsDashboardLayout,
	GlobalStatsDashboardLayout,
	StatsDashboardPage,
	StatsDashboardLayout,
};
