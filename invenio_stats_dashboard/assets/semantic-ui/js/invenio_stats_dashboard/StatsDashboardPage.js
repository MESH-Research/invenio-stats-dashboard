// Part of the Invenio-Stats-Dashboard extension for InvenioRDM
// Copyright (C) 2025 Mesh Research
//
// Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
// it under the terms of the MIT License; see LICENSE file for more details.

import React, { useMemo } from "react";
import PropTypes from "prop-types";
import { Label, Grid, Loader, Message } from "semantic-ui-react";
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { componentsMap } from "./components/components_map";
import { useStatsDashboard } from "./context/StatsDashboardContext";

/**
 *  Helper function to check that there is some data in stats.
 *
 *   @param {array} stats - the current stats from context
 *   @returns {boolean} - whether or not the stats are empty.
 *     (true if empty, false if not)
 */
const checkForEmptyStats = (stats) => {
	if (!stats || !Array.isArray(stats) || stats.length === 0) {
		return true;
	}

	for (const yearStats of stats) {
		// yearStats is an object, iterate over its values (which are arrays)
		if (yearStats && typeof yearStats === "object") {
			for (const arrayValue of Object.values(yearStats)) {
				// Check if the value is an array with elements
				if (Array.isArray(arrayValue) && arrayValue.length > 0) {
					return false; // Found data, stats are not empty
				}
			}
		}
	}

	// No data found, stats are empty
	return true;
};

/**
 * StatsDashboard page layout component
 *
 * This component converts the layout configuration object into a grid layout
 * and renders the components in the grid.
 *
 * @param {Object} dashboardConfig - The dashboard configuration
 * @param {Object} stats - The stats object
 * @param {Object} community - The community object if the dashboard is for a community
 * @param {string} variant - The variant (one of "content", "traffic")
 */
const StatsDashboardPage = ({
	dashboardConfig,
	stats: initialStats,
	community = undefined,
	variant,
	pageDateRangePhrase,
	displayDateRange,
	...otherProps
}) => {
	const layout = dashboardConfig.layout;
	const { dateRange, isLoading, isUpdating, error, stats } =
		useStatsDashboard();
	const agg_in_progress = dashboardConfig.agg_in_progress;
	const caching_in_progress = dashboardConfig.caching_in_progress;
	const first_run_incomplete = dashboardConfig.first_run_incomplete;

	const statsAreEmpty = useMemo(() => {
		return checkForEmptyStats(stats);
	}, [stats]);
	console.log("statsAreEmpty", statsAreEmpty);

	console.log("first_run_incomplete", first_run_incomplete);
	console.log("agg_in_progress", agg_in_progress);
	console.log("caching_in_progress", caching_in_progress);

	const noDataText = !!first_run_incomplete
		? "Initial calculation of statistics is still in progress. Check back again in a few hours."
		: !!agg_in_progress || !!caching_in_progress
			? "A calculation operation is currently in progress. Check back again later."
			: "No statistics data is available for the selected time period.";

	const renderComponent = (componentConfig) => {
		const Component = componentsMap[componentConfig.component];
		if (!Component) {
			return null;
		}

		// Pass props to components
		const componentProps = {
			...componentConfig.props,
			community,
		};

		// Get mobile and tablet widths from config, with fallback to 16
		const mobileWidth =
			componentConfig.props?.mobile ?? componentConfig.mobile ?? 16;
		const tabletWidth =
			componentConfig.props?.tablet ??
			componentConfig.tablet ??
			componentConfig.width;

		return (
			<Grid.Column
				computer={componentConfig.width}
				tablet={tabletWidth}
				mobile={mobileWidth}
				key={componentConfig.component}
				className={`${componentConfig.component.startsWith("SingleStat") ? "centered" : ""}`}
			>
				<Component {...componentProps} />
			</Grid.Column>
		);
	};

	// Find the tab that matches the variant
	const currentTab = layout.tabs.find((tab) => tab.name === variant);
	if (!currentTab) {
		console.warn(`No tab found for variant: ${variant}`);
		return null;
	}

	// Handle error state - show error message but still render components
	const errorMessage = error ? (
		<Grid.Row>
			<Grid.Column width={16}>
				<Message negative>
					<Message.Header>
						{i18next.t("Error Loading Statistics")}
					</Message.Header>
					<p>
						{i18next.t(
							"There was an error loading the statistics. Please try again later.",
						)}
					</p>
					{process.env.NODE_ENV === "development" && (
						<p>
							<strong>Debug:</strong> {error.message}
						</p>
					)}
				</Message>
			</Grid.Column>
		</Grid.Row>
	) : null;

	// 5 expected possible states:
	// (a) loading + no cached (!stats) + fetch in process
	// (b) loading + cached (stats) + fetch in process
	// (c) done loading + cached (stats) + fetch in process
	// (d) done loading + live data (stats) + fetch finished
	// (e) done loading + fetch finished + stats are still null (!stats)

	console.log(
		"StatsDashboardPage render - isLoading:",
		isLoading,
		"isUpdating:",
		isUpdating,
		"stats:",
		!!stats,
	);

	// State (a): loading + no cached + fetch in process
	const loadingMessage =
		isLoading && !stats ? (
			<Grid.Row className="rel-mt-3 rel-mb-2">
				<Grid.Column
					width={16}
					className="text-center stats-dashboard-loading-message"
				>
					<Loader active size="large">
						{i18next.t("Loading statistics...")}
					</Loader>
				</Grid.Column>
			</Grid.Row>
		) : null;

	// State (e): done loading + fetch finished + stats are still null
	const noDataMessage =
		!isLoading && !isUpdating && !error && (!stats || !!statsAreEmpty) ? (
			<Grid.Row className="rel-mt-2">
				<Grid.Column width={16}>
					<Message info>
						<Message.Header>{i18next.t("No Data Available")}</Message.Header>
						<p>{i18next.t(noDataText)}</p>
					</Message>
				</Grid.Column>
			</Grid.Row>
		) : null;

	const defaultTitle =
		dashboardConfig?.dashboard_type === "global"
			? i18next.t("Global Statistics Dashboard")
			: `${community.metadata.title} ${i18next.t("Statistics Dashboard")}`;

	return (
		<Grid
			className={`container stats-dashboard-content ${variant}`}
			role="main"
			aria-label={dashboardConfig.title || defaultTitle}
			{...otherProps}
		>
			<Grid.Row className="pb-0 large-monitor computer only">
				<Grid.Column width={16} className="centered">
					<Label className="stats-dashboard-date-range-label" pointing="below">
						{pageDateRangePhrase} {displayDateRange}
					</Label>
				</Grid.Column>
			</Grid.Row>
			{errorMessage}
			{loadingMessage}
			{noDataMessage}
			{currentTab.rows.map((row, index) => (
				<Grid.Row
					key={row.name}
					className={`stats-dashboard-row pb-0 pt-0 ${row.name}`}
				>
					{row.components.map((componentConfig) =>
						renderComponent(componentConfig),
					)}
				</Grid.Row>
			))}
		</Grid>
	);
};

StatsDashboardPage.propTypes = {
	dashboardConfig: PropTypes.object.isRequired,
	stats: PropTypes.array,
	community: PropTypes.object,
	variant: PropTypes.string.isRequired,
};

export { StatsDashboardPage };
