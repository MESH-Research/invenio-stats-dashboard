/**
 * Part of Invenio-Stats-Dashboard
 * Copyright (C) 2025 Mesh Research
 *
 * Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
 * it under the terms of the MIT License; see LICENSE file for more details.
 */

import React, { useState, useEffect, useRef } from "react";
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import {
	Button,
	Container,
	Dropdown,
	Grid,
	Icon,
	Label,
	Menu,
	Popup,
	Transition,
} from "semantic-ui-react";
import { StatsDashboardPage } from "./StatsDashboardPage";
import { DateRangeSelector } from "./components/controls/DateRangeSelector";
import { GranularitySelector } from "./components/controls/GranularitySelector";
import { ReportSelector } from "./components/controls/ReportSelector";
import { StatsDashboardProvider } from "./context/StatsDashboardContext";
import { fetchStats, updateStatsFromCache, updateState } from "./api/api";
import { formatDate, formatDateRange } from "./utils/dates";
import { UpdateStatusMessage } from "./components/shared_components/UpdateStatusMessage";
import PropTypes from "prop-types";

/**
 * Unified stats dashboard layout component
 *
 * This component extracts all common functionality from GlobalStatsDashboardLayout
 * and CommunityStatsDashboardLayout, allowing both to use this shared implementation
 * while preserving their distinctive configurations.
 */
const StatsDashboardLayout = ({
	dashboardConfig,
	dashboardType,
	community = null,
	showSubheader = false,
	containerClassNames,
	sidebarClassNames,
	bodyClassNames,
	getStatsParams = null,
}) => {
	const availableTabs = dashboardConfig?.layout?.tabs?.map((tab) => ({
		name: tab.name,
		label: i18next.t(tab.label),
		icon: tab.icon,
	}));
	const [selectedTab, setSelectedTab] = useState(availableTabs[0].name);
	const showTitle = ["true", "True", "TRUE", "1", true].includes(
		dashboardConfig?.show_title,
	);
	const showDescription = ["true", "True", "TRUE", "1", true].includes(
		dashboardConfig?.show_description,
	);
	const maxHistoryYears = dashboardConfig?.max_history_years || 15;
	const binary_sizes = dashboardConfig?.display_binary_sizes || false;
	const [dateRange, setDateRange] = useState();
	const [dataFetchRange, setDataFetchRange] = useState();
	const [granularity, setGranularity] = useState(
		dashboardConfig?.default_granularity || "day",
	);
	const [recordStartBasis, setRecordStartBasis] = useState(
		dashboardConfig?.default_record_start_basis || "added",
	);
	const [displaySeparately, setDisplaySeparately] = useState(null);
	const [stats, setStats] = useState([]); // Array of yearly stats objects
	const [isLoading, setIsLoading] = useState(true); // Start with loading true
	const [isUpdating, setIsUpdating] = useState(false);
	const [error, setError] = useState(null);
	const [lastUpdated, setLastUpdated] = useState(null);
	const [currentYearLastUpdated, setCurrentYearLastUpdated] = useState(null);
	const isMountedRef = useRef(true);
	const [actionMenuOpen, setActionMenuOpen] = useState(true);

	const handleTabChange = (_, data) => {
		const target = !!data.value ? data.value : data.name;
		setSelectedTab(target);
	};

	const [displayDateRange, setDisplayDateRange] = useState(null);
	useEffect(() => {
		if (dateRange) {
			const newDisplayDateRange = ["content", "traffic"].includes(selectedTab)
				? formatDate(dateRange.end, "day", true)
				: formatDateRange(dateRange, "day", true);
			setDisplayDateRange(newDisplayDateRange);
		}
	}, [dateRange, selectedTab]);

	const [pageDateRangePhrase, setPageDateRangePhrase] = useState(null);
	useEffect(() => {
		setPageDateRangePhrase(
			dashboardConfig.layout?.tabs?.find((tab) => tab.name === selectedTab)
				?.date_range_phrase,
		);
	}, [dashboardConfig, selectedTab]);

	const onStateChange = (state) => {
		if (isMountedRef.current) {
			setStats(state.stats);
			setIsLoading(state.isLoading);
			setIsUpdating(state.isUpdating);
			setError(state.error);

			if (state.lastUpdated !== undefined) {
				setLastUpdated(state.lastUpdated);
			}

			if (state.currentYearLastUpdated !== undefined) {
				setCurrentYearLastUpdated(state.currentYearLastUpdated);
			}
		}
	};

	useEffect(() => {
		// Don't fetch data if we don't have valid dates
		if (!dataFetchRange?.start || !dataFetchRange?.end) {
			console.log("Skipping data fetch - no valid dates");
			return;
		}

		isMountedRef.current = true;

		const useTestData = dashboardConfig?.use_test_data !== false;

		const loadStats = async () => {
			try {
				await fetchStats({
					communityId: community?.id,
					dashboardType,
					startDate: dataFetchRange?.start,
					endDate: dataFetchRange?.end,
					dateBasis: recordStartBasis,
					currentStats: stats, // Pass current stats for yearly block system
					getStatsParams,
					community,
					isMounted: () => isMountedRef.current,
					useTestData,
					dashboardConfig,
					onStateChange,
				});
			} catch (error) {
				if (isMountedRef.current) {
					console.error("Error in loadStats:", error);
					setError(error);
					setIsLoading(false);
					setIsUpdating(false);
				}
			}
		};

		loadStats();

		// Cleanup function to prevent state updates on unmounted component
		return () => {
			isMountedRef.current = false;
		};
	}, [dataFetchRange, community, dashboardType, getStatsParams]);

	// Listen for background cache updates
	useEffect(() => {
		const handleCacheUpdate = (event) => {
			const { data, year, success } = event.detail;

			if (!success || !data || !year) {
				return;
			}

			const updatedStats = updateStatsFromCache(stats, data, year);

			const fetchTimestamp = Date.now();
			const currentYear = new Date().getUTCFullYear();

			const newCurrentYearLastUpdated =
				year === currentYear ? fetchTimestamp : currentYearLastUpdated;

			updateState(onStateChange, () => true, "data_loaded", updatedStats, {
				lastUpdated: fetchTimestamp,
				currentYearLastUpdated: newCurrentYearLastUpdated,
			});
		};

		window.addEventListener("statsCacheUpdated", handleCacheUpdate);

		return () => {
			window.removeEventListener("statsCacheUpdated", handleCacheUpdate);
		};
	}, [stats, currentYearLastUpdated]);

	const contextValue = {
		binary_sizes,
		community,
		dateRange,
		dataFetchRange,
		displaySeparately,
		granularity,
		maxHistoryYears,
		recordStartBasis,
		setRecordStartBasis,
		setDateRange,
		setDataFetchRange,
		setDisplaySeparately,
		setGranularity,
		stats,
		isLoading,
		isUpdating,
		error,
		lastUpdated,
		ui_subcounts: dashboardConfig?.ui_subcounts,
	};

	return (
		<StatsDashboardProvider value={contextValue}>
			{showSubheader && (
				<div className="ui container fluid page-subheader-outer compact stats-dashboard-header ml-0-mobile mr-0-mobile">
					<div className="ui container stats-dashboard page-subheader flex align-items-center justify-space-between">
						<h1 className="ui huge header">
							{dashboardConfig?.title || i18next.t("Statistics")}
						</h1>
						{showDescription && (
							<p className="ui description">
								{dashboardConfig?.description || ""}
							</p>
						)}
					</div>
				</div>
			)}
			<Container
				className={`grid ${containerClassNames} ${dashboardType !== "global" ? "rel-m-2" : "rel-mb-2"} stats-dashboard-container`}
				id={`${dashboardType}-stats-dashboard`}
			>
				{showTitle && (
					<Grid.Row className="centered mobile tablet only">
						<h2 className="stats-dashboard-header ">
							{dashboardConfig.title || i18next.t("Statistics")}
						</h2>
					</Grid.Row>
				)}
				<Grid.Row>
					<Grid.Column
						width={3}
						className={`${sidebarClassNames} stats-dashboard-sidebar rel-mt-0 computer widescreen large-monitor only`}
					>
						{showTitle && (
							<h2 className="stats-dashboard-header computer widescreen large-monitor only">
								{dashboardConfig.title || i18next.t("Statistics")}
							</h2>
						)}
						<Menu
							fluid
							vertical
							className="stats-dashboard-sidebar-menu rel-mt-2 rel-mb-2 theme-primary-menu computer widescreen large-monitor only"
						>
							{availableTabs.map((tab) => (
								<Menu.Item
									key={tab.name}
									name={tab.name}
									onClick={handleTabChange}
									active={selectedTab === tab.name}
									as="button"
									fluid
									tabIndex={0}
									aria-pressed={selectedTab === tab.name}
									role="tab"
								>
									<span>{tab.label}</span>
									<Icon name={tab.icon} />
								</Menu.Item>
							))}
						</Menu>
						{showDescription && (
							<p className="ui description">
								{dashboardConfig?.description || ""}
							</p>
						)}
						<DateRangeSelector
							dateRange={dateRange}
							dataFetchRange={dataFetchRange}
							defaultRangeOptions={dashboardConfig?.default_range_options}
							granularity={granularity}
							maxHistoryYears={maxHistoryYears}
							setDateRange={setDateRange}
							setDataFetchRange={setDataFetchRange}
						/>
						<GranularitySelector
							defaultGranularity={dashboardConfig?.default_granularity}
							granularity={granularity}
							setGranularity={setGranularity}
						/>
						<ReportSelector />
						<UpdateStatusMessage
							isUpdating={isUpdating}
							isLoading={isLoading}
							lastUpdated={currentYearLastUpdated || lastUpdated}
							className="rel-mt-2"
						/>
						<section className="stats-sidebar-links-container rel-pt-1 rel-mt-1">
							<a href="/help/statistics" target="_blank">
								How do we track views and downloads?
							</a>
						</section>
					</Grid.Column>
					<Grid.Column
						computer={13}
						tablet={16}
						mobile={16}
						className={`${bodyClassNames} stats-dashboard-body`}
					>
						<Transition.Group
							animation="fade"
							duration={{ show: 1000, hide: 20 }}
						>
							{selectedTab && (
								<StatsDashboardPage
									community={community}
									dashboardConfig={dashboardConfig}
									stats={stats}
									variant={selectedTab}
									key={selectedTab}
									pageDateRangePhrase={pageDateRangePhrase}
									displayDateRange={displayDateRange}
								/>
							)}
						</Transition.Group>
					</Grid.Column>
				</Grid.Row>

				<Grid.Row className="mb-0 mt-0 pb-0 pt-0">
					<div
						className={`mobile-action-menu mobile tablet only sixteen wide sticky bottom ${!actionMenuOpen ? "hidden" : ""}`}
					>
						<div id="mobile-action-menu-toggle">
							<Button icon onClick={() => setActionMenuOpen(!actionMenuOpen)}>
								<Icon
									name={!!actionMenuOpen ? "chevron down" : "chevron up"}
									className="fitted"
								/>
							</Button>
						</div>
						<Grid>
							<Grid.Row className="pt-0">
								<b className="current-date-range-label pt-10">
									{pageDateRangePhrase} {displayDateRange}
								</b>
							</Grid.Row>

							<Grid.Row className="mb-0 mt-0 pb-0">
								<Grid.Column className="flex">
									<Dropdown
										id="mobile-category-selector"
										className="centered"
										selection
										upward
										options={availableTabs.map((tab) => ({
											icon: tab.icon,
											name: tab.name,
											value: tab.name,
											text: tab.label,
										}))}
										value={selectedTab}
										onChange={handleTabChange}
										closeOnChange={true}
										closeOnBlur={true}
										openOnFocus={false}
										text={
											<>
												<Icon
													name={
														availableTabs.find(
															(tab) => tab.name === selectedTab,
														)?.icon
													}
												/>
												<b>
													{
														availableTabs.find(
															(tab) => tab.name === selectedTab,
														)?.label
													}
												</b>
											</>
										}
									/>
								</Grid.Column>
							</Grid.Row>

							<Grid.Row id="mobile-date-selector flex">
								<Popup
									className="stats-dashboard-mobile-popup"
									trigger={
										<Button name="mobile-date-selector">
											<Icon name="calendar" />
											Dates
										</Button>
									}
									content={
										<DateRangeSelector
											dateRange={dateRange}
											dataFetchRange={dataFetchRange}
											defaultRangeOptions={
												dashboardConfig?.default_range_options
											}
											granularity={granularity}
											maxHistoryYears={maxHistoryYears}
											setDateRange={setDateRange}
											setDataFetchRange={setDataFetchRange}
										/>
									}
									on="click"
								/>

								<Popup
									className="stats-dashboard-mobile-popup"
									trigger={
										<Button name="mobile-granularity-selector">
											<Icon name="filter" />
											Granularity
										</Button>
									}
									content={
										<GranularitySelector
											defaultGranularity={dashboardConfig?.default_granularity}
											granularity={granularity}
											setGranularity={setGranularity}
											as="menu"
										/>
									}
									on="click"
								/>

								<Popup
									className="stats-dashboard-mobile-popup"
									trigger={
										<Button name="mobile-report-selector">
											<Icon fitted name="download" />
										</Button>
									}
									content={<ReportSelector />}
									on="click"
								/>
							</Grid.Row>
						</Grid>
					</div>
				</Grid.Row>
			</Container>
		</StatsDashboardProvider>
	);
};

StatsDashboardLayout.propTypes = {
	dashboardConfig: PropTypes.object.isRequired,
	dashboardType: PropTypes.string.isRequired,
	community: PropTypes.object,
	showSubheader: PropTypes.bool,
	containerClassNames: PropTypes.string.isRequired,
	sidebarClassNames: PropTypes.string.isRequired,
	bodyClassNames: PropTypes.string.isRequired,
	getStatsParams: PropTypes.func,
};

export { StatsDashboardLayout };
