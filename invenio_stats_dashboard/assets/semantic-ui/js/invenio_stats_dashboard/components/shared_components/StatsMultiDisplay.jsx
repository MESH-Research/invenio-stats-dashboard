// Part of the Invenio-Stats-Dashboard extension for InvenioRDM
// Copyright (C) 2025 Mesh Research
//
// Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
// it under the terms of the MIT License; see LICENSE file for more details.

import React, { useState, useRef, useEffect } from "react";
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import {
	Header,
	Segment,
	Icon,
	Button,
	Loader,
	Message,
} from "semantic-ui-react";
import { PropTypes } from "prop-types";
import ReactECharts from "echarts-for-react";
import { StatsTable } from "./StatsTable";
import { disableInvalidLinks } from "../../utils/multiDisplayHelpers";

const VIEW_MODE_ICON_MAP = {
	list: "list",
	line: "chart line",
	bar: "chart bar",
	pie: "pie chart",
	map: "map",
};

/** A component that displays a data series in a variety of views.
 *
 * Allows for a data series to be displayed in a table or a variety of chart views
 * with the ability to switch between views.
 *
 * The display modes are defined by the `chartOptions` object. If a simple table
 * view is desired as one view mode, a "list" key should be included in the object
 * and the value can be an empty object.
 *
 * Other views (various chart types) are defined by the remaining keys in
 * the `chartOptions` object. Each key is a view mode and the corresponding value
 * is the chart `option` object for the view mode.
 *
 * The view modes are defined by the `VIEW_MODE_ICON_MAP` object. The keys are
 * the view modes and the values are the icon names for the view modes. These are
 * also the valid values for the `type` property of the chart `option` object.
 *
 * Data for each chart view is provided in the `option` value for the view mode.
 * Data for the table view is provided in the `rows` array. This is an array of
 * arrays, where each item is an array representing a row in the table. The first
 * column in each row is used for the icon if an icon is desired. Other values in
 * each row can contain either a string, a number, or a React component to be
 * rendered in the corresponding table cell.
 *
 * @param {string} title - The display title for the widget.
 * @param {string} subtitle - Optional subtitle to display below the title (e.g., time-frame information).
 * @param {string} icon - The icon to display next to the title in the widget
 *      header. (Optional)
 * @param {string} label - The label of the data series.
 * @param {string[][]} headers - The headers for the table view of the data series.
 *      If the rows include an icon that column is not included in the headers array.
 *      Otherwise, the headers should match the number of columns in the rows array.
 * @param {string[][]} rows - The rows of the data series formatted for the table view.
 *      If the rows should include an icon for each item in the table display,
 *      the first column should be the icon name. Otherwise, the rows should
 *      match the number of columns in the headers array.
 * @param {object} chartOptions - An object containing the chart options for
 *      configuring the chart view of the data series. The keys are the view modes
 *      and the values are the chart options for the view mode.
 * @param {string} defaultViewMode - The default view mode of the data series.
 *      Defaults to "list".
 * @param {object} onEvents - The events to be passed to ReactECharts.
 * @param {boolean} hideOtherInCharts - If true and "other" is >30% of total, exclude it from charts and show as floating label.
 */
const StatsMultiDisplay = ({
	title,
	subtitle,
	icon: labelIcon,
	label,
	headers,
	rows,
	chartOptions,
	defaultViewMode = "list",
	onEvents,
	isLoading = false,
	maxHeight = null,
	isDelta = false,
	dateRangeEnd = null,
	metricType = "records",
	startCollapsed = false,
}) => {
	const [viewMode, setViewMode] = useState(defaultViewMode);
	const [collapsed, setCollapsed] = useState(collapsed);
	const [neverOpened, setNeverOpened] = useState(true);
	const [showContent, setShowContent] = useState(!collapsed && !neverOpened);
	const chartRef = useRef(null);
	const availableViewModes = Object.keys(chartOptions);
	const tableLabel = label
		? label
		: title
			? title.toLowerCase().replace(/\s+/g, "-")
			: "stats";

	const handleViewChange = (e, mode) => {
		e.stopPropagation();
		if (!!collapsed) {
			setCollapsed(false);
		}
		setViewMode(mode);
	};

	const handleOpenClose = () => {
		setCollapsed(!collapsed);
		if (!!neverOpened) {
			setNeverOpened(false);
		}
	};

	const effectiveHasData = !isLoading && rows && rows.length > 0;

	// Resize chart after mount and when viewMode changes to fix initial zoom/overflow issue
	const resizeChart = () => {
		if (!chartRef.current) {
			return;
		}

		// Use requestAnimationFrame to ensure the DOM has settled and container has final size
		requestAnimationFrame(() => {
			try {
				const chartInstance = chartRef.current.getEchartsInstance();
				if (chartInstance) {
					chartInstance.resize();
				}
			} catch (error) {
				// Silently handle errors if chart instance is not ready
				console.debug("Chart resize error:", error);
			}
		});
	};

	useEffect(() => {
		if (viewMode === "list" || !effectiveHasData || isLoading) {
			return;
		}

		// Resize immediately and after a short delay to handle any async layout
		resizeChart();
		const timeoutId = setTimeout(resizeChart, 100);

		return () => {
			clearTimeout(timeoutId);
		};
	}, [viewMode, effectiveHasData, isLoading]);

	// Set collapsed state based on mobile width (Semantic UI mobile breakpoint is < 768px)
	useEffect(() => {
		const checkMobile = () => {
			const isMobileWidth = window.innerWidth < 768;
			// Collapse on mobile if never opened, or if already collapsed
			if (isMobileWidth && neverOpened) {
				setCollapsed(true);
			}
		};
		checkMobile();
		window.addEventListener("resize", checkMobile);

		return () => {
			window.removeEventListener("resize", checkMobile);
		};
	}, [neverOpened]);

	// Delay content rendering during open animation (500ms transition duration)
	useEffect(() => {
		if (collapsed) {
			// Hide content immediately when collapsing
			setShowContent(false);
		} else {
			// Delay showing content when opening to allow animation to complete
			const timeoutId = setTimeout(() => {
				setShowContent(true);
			}, 500); // Match the CSS transition duration

			return () => {
				clearTimeout(timeoutId);
			};
		}
	}, [collapsed]);

	// Cleanup: dispose chart instance on unmount
	useEffect(() => {
		return () => {
			if (chartRef.current) {
				try {
					const chartInstance = chartRef.current.getEchartsInstance();
					if (chartInstance && !chartInstance.isDisposed()) {
						chartInstance.dispose();
					}
				} catch (error) {
					// Silently handle errors if chart instance is not available
					console.debug("Chart dispose error:", error);
				}
			}
		};
	}, []);

	// Handle chart ready callback to resize when chart is first initialized
	const handleChartReady = (chart) => {
		// Resize after chart is ready to ensure correct dimensions
		setTimeout(() => {
			if (chart) {
				chart.resize();
			}
		}, 0);
	};

	// Add aria.enabled to all chart options
	const enhancedChartOptions = Object.fromEntries(
		Object.entries(chartOptions).map(([key, value]) => [
			key,
			{
				...value,
				aria: {
					enabled: true,
				},
			},
		]),
	);

	return (
		<div
			className={`stats-multi-display-container ${tableLabel}-stats-multi-display-container rel-mb-1 rel-mt-1`}
			role="region"
			aria-label={title}
			data-testid="stats-multi-display"
		>
			{title && (
				<Header
					as="h3"
					id={`${tableLabel}-stats-multi-display-header`}
					className="stats-multi-display-header"
					attached="top"
					onClick={handleOpenClose}
				>
					{labelIcon && (
						<Icon
							name={labelIcon}
							className="stats-multi-display-icon"
							aria-hidden="true"
							size="small"
						/>
					)}
					{availableViewModes.length > 1 &&
						!isLoading &&
						availableViewModes.map((mode) => (
							<Button
								key={mode}
								active={viewMode === mode}
								onClick={(e) => handleViewChange(e, mode)}
								aria-label={i18next.t(mode)}
								size="small"
								toggle
							>
								<Icon fitted name={VIEW_MODE_ICON_MAP[mode]} />
							</Button>
						))}
					{title}
					{subtitle && <Header.Subheader>{subtitle}</Header.Subheader>}
				</Header>
			)}
			<Segment
				attached
				className={`stats-multi-display-segment pr-0 pl-0 pb-0 pt-0 ${collapsed ? "collapsed" : ""} ${!!neverOpened ? "never-opened" : ""}`}
			>
				{isLoading ? (
					<div className="stats-loading-container">
						<Loader active size="large" />
					</div>
				) : !effectiveHasData ? (
					<div className="stats-no-data-container">
						<Message info>
							<Message.Header>{i18next.t("No Data Available")}</Message.Header>
							<p>
								{i18next.t(
									"No data is available for the selected time period.",
								)}
							</p>
						</Message>
					</div>
				) : showContent ? (
					viewMode === "list" ? (
						<StatsTable
							label={`${tableLabel}-table`}
							headers={headers}
							rows={rows}
							labelIcon={labelIcon}
							maxHeight={maxHeight}
							isDelta={isDelta}
							dateRangeEnd={dateRangeEnd}
							metricType={metricType}
						/>
					) : (
						<ReactECharts
							ref={chartRef}
							option={enhancedChartOptions[viewMode]}
							notMerge={true}
							style={{ height: "338px" }} // 340px - 2px for border
							className={`${tableLabel}-${viewMode}-chart`}
							onEvents={disableInvalidLinks(onEvents)}
							onChartReady={handleChartReady}
						/>
					)
				) : null}
			</Segment>
		</div>
	);
};

StatsMultiDisplay.propTypes = {
	title: PropTypes.string.isRequired,
	subtitle: PropTypes.string,
	icon: PropTypes.string,
	label: PropTypes.string,
	headers: PropTypes.array.isRequired,
	rows: PropTypes.array.isRequired,
	chartOptions: PropTypes.object.isRequired,
	defaultViewMode: PropTypes.string,
	onEvents: PropTypes.object,
	isLoading: PropTypes.bool,
	hasData: PropTypes.bool,
	maxHeight: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
	hideOtherInCharts: PropTypes.bool,
	isDelta: PropTypes.bool,
	dateRangeEnd: PropTypes.string,
	metricType: PropTypes.string,
};

export { StatsMultiDisplay };
