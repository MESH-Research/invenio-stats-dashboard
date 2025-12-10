// Part of the Invenio-Stats-Dashboard extension for InvenioRDM
// Copyright (C) 2025 Mesh Research
//
// Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
// it under the terms of the MIT License; see LICENSE file for more details.

import React from "react";
import { render, screen } from "@testing-library/react";
import { StatsDashboardPage, checkForEmptyStats } from "./StatsDashboardPage";

const EMPTY_STATS_OBJECT = [
	{
		usageSnapshotData: {
			global: {
				dataVolume: [],
				downloadUniqueFiles: [],
				downloadUniqueParents: [],
				downloadUniqueRecords: [],
				downloadVisitors: [],
				downloads: [],
				viewUniqueParents: [],
				viewUniqueRecords: [],
				viewVisitors: [],
				views: [],
			},
			resourceTypes: {
				dataVolume: [],
				downloadUniqueFiles: [],
				downloadUniqueParents: [],
				downloadUniqueRecords: [],
				downloadVisitors: [],
				downloads: [],
				viewUniqueParents: [],
				viewUniqueRecords: [],
				viewVisitors: [],
				views: [],
			},
			accessStatuses: {
				dataVolume: [],
				downloadUniqueFiles: [],
				downloadUniqueParents: [],
				downloadUniqueRecords: [],
				downloadVisitors: [],
				downloads: [],
				viewUniqueParents: [],
				viewUniqueRecords: [],
				viewVisitors: [],
				views: [],
			},
			languagesByView: {
				dataVolume: [],
				downloadUniqueFiles: [],
				downloadUniqueParents: [],
				downloadUniqueRecords: [],
				downloadVisitors: [],
				downloads: [],
				viewUniqueParents: [],
				viewUniqueRecords: [],
				viewVisitors: [],
				views: [],
			},
			languagesByDownload: {
				dataVolume: [],
				downloadUniqueFiles: [],
				downloadUniqueParents: [],
				downloadUniqueRecords: [],
				downloadVisitors: [],
				downloads: [],
				viewUniqueParents: [],
				viewUniqueRecords: [],
				viewVisitors: [],
				views: [],
			},
			subjects: {
				dataVolume: [],
				downloadUniqueFiles: [],
				downloadUniqueParents: [],
				downloadUniqueRecords: [],
				downloadVisitors: [],
				downloads: [],
				viewUniqueParents: [],
				viewUniqueRecords: [],
				viewVisitors: [],
				views: [],
				byViewViews: [],
				byViewDownloads: [],
				byViewViewVisitors: [],
				byViewDownloadVisitors: [],
				byViewViewUniqueRecords: [],
				byViewViewUniqueParents: [],
				byViewDownloadUniqueFiles: [],
				byViewDownloadUniqueParents: [],
				byViewDownloadUniqueRecords: [],
				byViewDataVolume: [],
				byDownloadViews: [],
				byDownloadDownloads: [],
				byDownloadViewVisitors: [],
				byDownloadDownloadVisitors: [],
				byDownloadViewUniqueRecords: [],
				byDownloadViewUniqueParents: [],
				byDownloadDownloadUniqueFiles: [],
				byDownloadDownloadUniqueParents: [],
				byDownloadDownloadUniqueRecords: [],
				byDownloadDataVolume: [],
			},
			rightsByView: {
				views: [],
				downloads: [],
				viewVisitors: [],
				downloadVisitors: [],
				viewUniqueRecords: [],
				viewUniqueParents: [],
				downloadUniqueFiles: [],
				downloadUniqueParents: [],
				downloadUniqueRecords: [],
				dataVolume: [],
			},
			rightsByDownload: {
				views: [],
				downloads: [],
				viewVisitors: [],
				downloadVisitors: [],
				viewUniqueRecords: [],
				viewUniqueParents: [],
				downloadUniqueFiles: [],
				downloadUniqueParents: [],
				downloadUniqueRecords: [],
				dataVolume: [],
			},
			fundersByView: {
				dataVolume: [],
				downloadUniqueFiles: [],
				downloadUniqueParents: [],
				downloadUniqueRecords: [],
				downloadVisitors: [],
				downloads: [],
				viewUniqueParents: [],
				viewUniqueRecords: [],
				viewVisitors: [],
				views: [],
			},
			fundersByDownload: {
				dataVolume: [],
				downloadUniqueFiles: [],
				downloadUniqueParents: [],
				downloadUniqueRecords: [],
				downloadVisitors: [],
				downloads: [],
				viewUniqueParents: [],
				viewUniqueRecords: [],
				viewVisitors: [],
				views: [],
			},
			periodicalsByView: {
				dataVolume: [],
				downloadUniqueFiles: [],
				downloadUniqueParents: [],
				downloadUniqueRecords: [],
				downloadVisitors: [],
				downloads: [],
				viewUniqueParents: [],
				viewUniqueRecords: [],
				viewVisitors: [],
				views: [],
			},
			periodicalsByDownload: {
				dataVolume: [],
				downloadUniqueFiles: [],
				downloadUniqueParents: [],
				downloadUniqueRecords: [],
				downloadVisitors: [],
				downloads: [],
				viewUniqueParents: [],
				viewUniqueRecords: [],
				viewVisitors: [],
				views: [],
			},
			publishersByView: {
				views: [],
				downloads: [],
				viewVisitors: [],
				downloadVisitors: [],
				viewUniqueRecords: [],
				viewUniqueParents: [],
				downloadUniqueFiles: [],
				downloadUniqueParents: [],
				downloadUniqueRecords: [],
				dataVolume: [],
			},
			publishersByDownload: {
				views: [],
				downloads: [],
				viewVisitors: [],
				downloadVisitors: [],
				viewUniqueRecords: [],
				viewUniqueParents: [],
				downloadUniqueFiles: [],
				downloadUniqueParents: [],
				downloadUniqueRecords: [],
				dataVolume: [],
			},
			affiliationsByView: {
				views: [],
				downloads: [],
				viewVisitors: [],
				downloadVisitors: [],
				viewUniqueRecords: [],
				viewUniqueParents: [],
				downloadUniqueFiles: [],
				downloadUniqueParents: [],
				downloadUniqueRecords: [],
				dataVolume: [],
			},
			affiliationsByDownload: {
				views: [],
				downloads: [],
				viewVisitors: [],
				downloadVisitors: [],
				viewUniqueRecords: [],
				viewUniqueParents: [],
				downloadUniqueFiles: [],
				downloadUniqueParents: [],
				downloadUniqueRecords: [],
				dataVolume: [],
			},
			countriesByView: {
				views: [],
				downloads: [],
				viewVisitors: [],
				downloadVisitors: [],
				viewUniqueRecords: [],
				viewUniqueParents: [],
				downloadUniqueFiles: [],
				downloadUniqueParents: [],
				downloadUniqueRecords: [],
				dataVolume: [],
			},
			countriesByDownload: {
				views: [],
				downloads: [],
				viewVisitors: [],
				downloadVisitors: [],
				viewUniqueRecords: [],
				viewUniqueParents: [],
				downloadUniqueFiles: [],
				downloadUniqueParents: [],
				downloadUniqueRecords: [],
				dataVolume: [],
			},
			referrers: {
				dataVolume: [],
				downloadUniqueFiles: [],
				downloadUniqueParents: [],
				downloadUniqueRecords: [],
				downloadVisitors: [],
				downloads: [],
				viewUniqueParents: [],
				viewUniqueRecords: [],
				viewVisitors: [],
				views: [],
				byViewViews: [],
				byViewDownloads: [],
				byViewViewVisitors: [],
				byViewDownloadVisitors: [],
				byViewViewUniqueRecords: [],
				byViewViewUniqueParents: [],
				byViewDownloadUniqueFiles: [],
				byViewDownloadUniqueParents: [],
				byViewDownloadUniqueRecords: [],
				byViewDataVolume: [],
				byDownloadViews: [],
				byDownloadDownloads: [],
				byDownloadViewVisitors: [],
				byDownloadDownloadVisitors: [],
				byDownloadViewUniqueRecords: [],
				byDownloadViewUniqueParents: [],
				byDownloadDownloadUniqueFiles: [],
				byDownloadDownloadUniqueParents: [],
				byDownloadDownloadUniqueRecords: [],
				byDownloadDataVolume: [],
			},
			fileTypes: {
				dataVolume: [],
				downloadUniqueFiles: [],
				downloadUniqueParents: [],
				downloadUniqueRecords: [],
				downloadVisitors: [],
				downloads: [],
				viewUniqueParents: [],
				viewUniqueRecords: [],
				viewVisitors: [],
				views: [],
			},
			subjectsByView: {
				views: [],
				downloads: [],
				viewVisitors: [],
				downloadVisitors: [],
				viewUniqueRecords: [],
				viewUniqueParents: [],
				downloadUniqueFiles: [],
				downloadUniqueParents: [],
				downloadUniqueRecords: [],
				dataVolume: [],
			},
			subjectsByDownload: {
				views: [],
				downloads: [],
				viewVisitors: [],
				downloadVisitors: [],
				viewUniqueRecords: [],
				viewUniqueParents: [],
				downloadUniqueFiles: [],
				downloadUniqueParents: [],
				downloadUniqueRecords: [],
				dataVolume: [],
			},
			referrersByView: {
				views: [],
				downloads: [],
				viewVisitors: [],
				downloadVisitors: [],
				viewUniqueRecords: [],
				viewUniqueParents: [],
				downloadUniqueFiles: [],
				downloadUniqueParents: [],
				downloadUniqueRecords: [],
				dataVolume: [],
			},
			referrersByDownload: {
				views: [],
				downloads: [],
				viewVisitors: [],
				downloadVisitors: [],
				viewUniqueRecords: [],
				viewUniqueParents: [],
				downloadUniqueFiles: [],
				downloadUniqueParents: [],
				downloadUniqueRecords: [],
				dataVolume: [],
			},
		},
		usageDeltaData: {
			global: {
				dataVolume: [],
				downloadUniqueFiles: [],
				downloadUniqueParents: [],
				downloadUniqueRecords: [],
				downloadVisitors: [],
				downloads: [],
				viewUniqueParents: [],
				viewUniqueRecords: [],
				viewVisitors: [],
				views: [],
			},
			resourceTypes: {
				dataVolume: [],
				downloadUniqueFiles: [],
				downloadUniqueParents: [],
				downloadUniqueRecords: [],
				downloadVisitors: [],
				downloads: [],
				viewUniqueParents: [],
				viewUniqueRecords: [],
				viewVisitors: [],
				views: [],
			},
			accessStatuses: {
				dataVolume: [],
				downloadUniqueFiles: [],
				downloadUniqueParents: [],
				downloadUniqueRecords: [],
				downloadVisitors: [],
				downloads: [],
				viewUniqueParents: [],
				viewUniqueRecords: [],
				viewVisitors: [],
				views: [],
			},
			languages: {
				dataVolume: [],
				downloadUniqueFiles: [],
				downloadUniqueParents: [],
				downloadUniqueRecords: [],
				downloadVisitors: [],
				downloads: [],
				viewUniqueParents: [],
				viewUniqueRecords: [],
				viewVisitors: [],
				views: [],
			},
			rights: {
				dataVolume: [],
				downloadUniqueFiles: [],
				downloadUniqueParents: [],
				downloadUniqueRecords: [],
				downloadVisitors: [],
				downloads: [],
				viewUniqueParents: [],
				viewUniqueRecords: [],
				viewVisitors: [],
				views: [],
			},
			funders: {
				dataVolume: [],
				downloadUniqueFiles: [],
				downloadUniqueParents: [],
				downloadUniqueRecords: [],
				downloadVisitors: [],
				downloads: [],
				viewUniqueParents: [],
				viewUniqueRecords: [],
				viewVisitors: [],
				views: [],
			},
			periodicals: {
				dataVolume: [],
				downloadUniqueFiles: [],
				downloadUniqueParents: [],
				downloadUniqueRecords: [],
				downloadVisitors: [],
				downloads: [],
				viewUniqueParents: [],
				viewUniqueRecords: [],
				viewVisitors: [],
				views: [],
			},
			publishers: {
				dataVolume: [],
				downloadUniqueFiles: [],
				downloadUniqueParents: [],
				downloadUniqueRecords: [],
				downloadVisitors: [],
				downloads: [],
				viewUniqueParents: [],
				viewUniqueRecords: [],
				viewVisitors: [],
				views: [],
			},
			affiliations: {
				dataVolume: [],
				downloadUniqueFiles: [],
				downloadUniqueParents: [],
				downloadUniqueRecords: [],
				downloadVisitors: [],
				downloads: [],
				viewUniqueParents: [],
				viewUniqueRecords: [],
				viewVisitors: [],
				views: [],
			},
			countries: {
				dataVolume: [],
				downloadUniqueFiles: [],
				downloadUniqueParents: [],
				downloadUniqueRecords: [],
				downloadVisitors: [],
				downloads: [],
				viewUniqueParents: [],
				viewUniqueRecords: [],
				viewVisitors: [],
				views: [],
			},
			fileTypes: {
				dataVolume: [],
				downloadUniqueFiles: [],
				downloadUniqueParents: [],
				downloadUniqueRecords: [],
				downloadVisitors: [],
				downloads: [],
				viewUniqueParents: [],
				viewUniqueRecords: [],
				viewVisitors: [],
				views: [],
			},
		},
		recordSnapshotDataAdded: {
			global: {
				records: [],
				parents: [],
				uploaders: [],
				dataVolume: [],
				fileCount: [],
			},
			resourceTypes: {
				records: [],
				parents: [],
				dataVolume: [],
				fileCount: [],
			},
			accessStatuses: {
				records: [],
				parents: [],
				dataVolume: [],
				fileCount: [],
			},
			languages: {
				records: [],
				parents: [],
				dataVolume: [],
				fileCount: [],
			},
			subjects: {
				records: [],
				parents: [],
				dataVolume: [],
				fileCount: [],
			},
			rights: {
				records: [],
				parents: [],
				dataVolume: [],
				fileCount: [],
			},
			funders: {
				records: [],
				parents: [],
				dataVolume: [],
				fileCount: [],
			},
			periodicals: {
				records: [],
				parents: [],
				dataVolume: [],
				fileCount: [],
			},
			publishers: {
				records: [],
				parents: [],
				dataVolume: [],
				fileCount: [],
			},
			affiliations: {
				records: [],
				parents: [],
				dataVolume: [],
				fileCount: [],
			},
			fileTypes: {
				records: [],
				parents: [],
				dataVolume: [],
				fileCount: [],
			},
			filePresence: {
				records: [
					{
						id: "metadata_only",
						name: "Metadata Only",
						data: [],
						type: "line",
						valueType: "number",
					},
					{
						id: "with_files",
						name: "With Files",
						data: [],
						type: "line",
						valueType: "number",
					},
				],
				parents: [
					{
						id: "metadata_only",
						name: "Metadata Only",
						data: [],
						type: "line",
						valueType: "number",
					},
					{
						id: "with_files",
						name: "With Files",
						data: [],
						type: "line",
						valueType: "number",
					},
				],
				dataVolume: [
					{
						id: "metadata_only",
						name: "Metadata Only",
						data: [],
						type: "line",
						valueType: "filesize",
					},
					{
						id: "with_files",
						name: "With Files",
						data: [],
						type: "line",
						valueType: "filesize",
					},
				],
				fileCount: [
					{
						id: "metadata_only",
						name: "Metadata Only",
						data: [],
						type: "line",
						valueType: "number",
					},
					{
						id: "with_files",
						name: "With Files",
						data: [],
						type: "line",
						valueType: "number",
					},
				],
			},
		},
		recordDeltaDataAdded: {
			global: {
				records: [],
				fileCount: [],
				dataVolume: [],
				parents: [],
				uploaders: [],
			},
			resourceTypes: {
				records: [],
				fileCount: [],
				dataVolume: [],
				parents: [],
			},
			accessStatuses: {
				records: [],
				fileCount: [],
				dataVolume: [],
				parents: [],
			},
			languages: {
				records: [],
				fileCount: [],
				dataVolume: [],
				parents: [],
			},
			subjects: {
				records: [],
				fileCount: [],
				dataVolume: [],
				parents: [],
			},
			rights: {
				records: [],
				fileCount: [],
				dataVolume: [],
				parents: [],
			},
			funders: {
				records: [],
				fileCount: [],
				dataVolume: [],
				parents: [],
			},
			periodicals: {
				records: [],
				fileCount: [],
				dataVolume: [],
				parents: [],
			},
			publishers: {
				records: [],
				fileCount: [],
				dataVolume: [],
				parents: [],
			},
			affiliations: {
				records: [],
				fileCount: [],
				dataVolume: [],
				parents: [],
			},
			fileTypes: {
				records: [],
				fileCount: [],
				dataVolume: [],
				parents: [],
			},
			filePresence: {
				records: [
					{
						id: "metadata_only",
						name: "Metadata Only",
						data: [],
						type: "line",
						valueType: "number",
					},
					{
						id: "with_files",
						name: "With Files",
						data: [],
						type: "line",
						valueType: "number",
					},
				],
				fileCount: [
					{
						id: "metadata_only",
						name: "Metadata Only",
						data: [],
						type: "line",
						valueType: "number",
					},
					{
						id: "with_files",
						name: "With Files",
						data: [],
						type: "line",
						valueType: "number",
					},
				],
				dataVolume: [
					{
						id: "metadata_only",
						name: "Metadata Only",
						data: [],
						type: "line",
						valueType: "filesize",
					},
					{
						id: "with_files",
						name: "With Files",
						data: [],
						type: "line",
						valueType: "filesize",
					},
				],
				parents: [
					{
						id: "metadata_only",
						name: "Metadata Only",
						data: [],
						type: "line",
						valueType: "number",
					},
					{
						id: "with_files",
						name: "With Files",
						data: [],
						type: "line",
						valueType: "number",
					},
				],
			},
		},
		year: 2025,
	},
];

// Mock i18next
jest.mock("@translations/invenio_stats_dashboard/i18next", () => ({
	i18next: {
		t: (key) => key,
	},
}));

// Mock the StatsDashboard context
const mockUseStatsDashboard = jest.fn();
jest.mock("./context/StatsDashboardContext", () => ({
	useStatsDashboard: () => mockUseStatsDashboard(),
}));

// Mock componentsMap
jest.mock("./components/components_map", () => ({
	componentsMap: {
		SingleStatRecordCount: () => (
			<div data-testid="single-stat-record-count">Record Count</div>
		),
		SingleStatViews: () => <div data-testid="single-stat-views">Views</div>,
	},
}));

describe("StatsDashboardPage", () => {
	const mockCommunity = {
		id: "test-community",
		metadata: {
			title: "Test Community",
		},
	};

	const baseDashboardConfig = {
		layout: {
			tabs: [
				{
					name: "content",
					label: "Content",
					icon: "file text",
					rows: [
						{
							name: "test-row",
							components: [
								{
									component: "SingleStatRecordCount",
									width: 8,
								},
							],
						},
					],
				},
			],
		},
		dashboard_type: "community",
	};

	beforeEach(() => {
		jest.clearAllMocks();
		// Default mock return value
		mockUseStatsDashboard.mockReturnValue({
			dateRange: { start: new Date("2024-01-01"), end: new Date("2024-01-31") },
			isLoading: false,
			isUpdating: false,
			error: null,
			stats: [],
		});
	});

	describe("Loading State", () => {
		it("should show loading message when isLoading is true and no stats", () => {
			mockUseStatsDashboard.mockReturnValue({
				dateRange: {
					start: new Date("2024-01-01"),
					end: new Date("2024-01-31"),
				},
				isLoading: true,
				isUpdating: false,
				error: null,
				stats: null,
			});

			render(
				<StatsDashboardPage
					dashboardConfig={baseDashboardConfig}
					community={mockCommunity}
					variant="content"
				/>,
			);

			expect(screen.getByText("Loading statistics...")).toBeInTheDocument();
		});

		it("should not show loading message when stats are available", () => {
			mockUseStatsDashboard.mockReturnValue({
				dateRange: {
					start: new Date("2024-01-01"),
					end: new Date("2024-01-31"),
				},
				isLoading: true,
				isUpdating: false,
				error: null,
				stats: [
					{
						year: 2024,
						usageSnapshotData: {
							global: {
								views: [1, 2, 3],
							},
						},
					},
				],
			});

			render(
				<StatsDashboardPage
					dashboardConfig={baseDashboardConfig}
					community={mockCommunity}
					variant="content"
				/>,
			);

			expect(
				screen.queryByText("Loading statistics..."),
			).not.toBeInTheDocument();
		});
	});

	describe("Error State", () => {
		it("should show error message when error is present", () => {
			const error = new Error("Test error message");
			mockUseStatsDashboard.mockReturnValue({
				dateRange: {
					start: new Date("2024-01-01"),
					end: new Date("2024-01-31"),
				},
				isLoading: false,
				isUpdating: false,
				error: error,
				stats: null,
			});

			render(
				<StatsDashboardPage
					dashboardConfig={baseDashboardConfig}
					community={mockCommunity}
					variant="content"
				/>,
			);

			expect(screen.getByText("Error Loading Statistics")).toBeInTheDocument();
			expect(
				screen.getByText(
					"There was an error loading the statistics. Please try again later.",
				),
			).toBeInTheDocument();
		});

		it("should show debug error message in development mode", () => {
			const originalEnv = process.env.NODE_ENV;
			process.env.NODE_ENV = "development";

			const error = new Error("Test error message");
			mockUseStatsDashboard.mockReturnValue({
				dateRange: {
					start: new Date("2024-01-01"),
					end: new Date("2024-01-31"),
				},
				isLoading: false,
				isUpdating: false,
				error: error,
				stats: null,
			});

			render(
				<StatsDashboardPage
					dashboardConfig={baseDashboardConfig}
					community={mockCommunity}
					variant="content"
				/>,
			);

			expect(screen.getByText("Debug:")).toBeInTheDocument();
			expect(screen.getByText("Test error message")).toBeInTheDocument();

			process.env.NODE_ENV = originalEnv;
		});
	});

	describe("No Data Messages", () => {
		it("should show first_run_incomplete message when first_run_incomplete is true and stats is null", () => {
			const dashboardConfig = {
				...baseDashboardConfig,
				first_run_incomplete: true,
				agg_in_progress: false,
				caching_in_progress: false,
			};

			mockUseStatsDashboard.mockReturnValue({
				dateRange: {
					start: new Date("2024-01-01"),
					end: new Date("2024-01-31"),
				},
				isLoading: false,
				isUpdating: false,
				error: null,
				stats: null,
			});

			render(
				<StatsDashboardPage
					dashboardConfig={dashboardConfig}
					community={mockCommunity}
					variant="content"
				/>,
			);

			expect(screen.getByText("No Data Available")).toBeInTheDocument();
			expect(
				screen.getByText(
					"Initial calculation of statistics is still in progress. Check back again in a few hours.",
				),
			).toBeInTheDocument();
		});

		it("should show first_run_incomplete message when first_run_incomplete is true and stats is empty array", () => {
			const dashboardConfig = {
				...baseDashboardConfig,
				first_run_incomplete: true,
				agg_in_progress: false,
				caching_in_progress: false,
			};

			mockUseStatsDashboard.mockReturnValue({
				dateRange: {
					start: new Date("2024-01-01"),
					end: new Date("2024-01-31"),
				},
				isLoading: false,
				isUpdating: false,
				error: null,
				stats: [],
			});

			render(
				<StatsDashboardPage
					dashboardConfig={dashboardConfig}
					community={mockCommunity}
					variant="content"
				/>,
			);

			expect(screen.getByText("No Data Available")).toBeInTheDocument();
			expect(
				screen.getByText(
					"Initial calculation of statistics is still in progress. Check back again in a few hours.",
				),
			).toBeInTheDocument();
		});

		it("should show agg_in_progress message when agg_in_progress is true", () => {
			const dashboardConfig = {
				...baseDashboardConfig,
				first_run_incomplete: false,
				agg_in_progress: true,
				caching_in_progress: false,
			};

			mockUseStatsDashboard.mockReturnValue({
				dateRange: {
					start: new Date("2024-01-01"),
					end: new Date("2024-01-31"),
				},
				isLoading: false,
				isUpdating: false,
				error: null,
				stats: null,
			});

			render(
				<StatsDashboardPage
					dashboardConfig={dashboardConfig}
					community={mockCommunity}
					variant="content"
				/>,
			);

			expect(screen.getByText("No Data Available")).toBeInTheDocument();
			expect(
				screen.getByText(
					"A calculation operation is currently in progress. Check back again later.",
				),
			).toBeInTheDocument();
		});

		it("should show caching_in_progress message when caching_in_progress is true", () => {
			const dashboardConfig = {
				...baseDashboardConfig,
				first_run_incomplete: false,
				agg_in_progress: false,
				caching_in_progress: true,
			};

			mockUseStatsDashboard.mockReturnValue({
				dateRange: {
					start: new Date("2024-01-01"),
					end: new Date("2024-01-31"),
				},
				isLoading: false,
				isUpdating: false,
				error: null,
				stats: null,
			});

			render(
				<StatsDashboardPage
					dashboardConfig={dashboardConfig}
					community={mockCommunity}
					variant="content"
				/>,
			);

			expect(screen.getByText("No Data Available")).toBeInTheDocument();
			expect(
				screen.getByText(
					"A calculation operation is currently in progress. Check back again later.",
				),
			).toBeInTheDocument();
		});

		it("should show default no data message when no flags are set", () => {
			const dashboardConfig = {
				...baseDashboardConfig,
				first_run_incomplete: false,
				agg_in_progress: false,
				caching_in_progress: false,
			};

			mockUseStatsDashboard.mockReturnValue({
				dateRange: {
					start: new Date("2024-01-01"),
					end: new Date("2024-01-31"),
				},
				isLoading: false,
				isUpdating: false,
				error: null,
				stats: null,
			});

			render(
				<StatsDashboardPage
					dashboardConfig={dashboardConfig}
					community={mockCommunity}
					variant="content"
				/>,
			);

			expect(screen.getByText("No Data Available")).toBeInTheDocument();
			expect(
				screen.getByText(
					"No statistics data is available for the selected time period.",
				),
			).toBeInTheDocument();
		});

		it("should prioritize first_run_incomplete over agg_in_progress", () => {
			const dashboardConfig = {
				...baseDashboardConfig,
				first_run_incomplete: true,
				agg_in_progress: true,
				caching_in_progress: false,
			};

			mockUseStatsDashboard.mockReturnValue({
				dateRange: {
					start: new Date("2024-01-01"),
					end: new Date("2024-01-31"),
				},
				isLoading: false,
				isUpdating: false,
				error: null,
				stats: null,
			});

			render(
				<StatsDashboardPage
					dashboardConfig={dashboardConfig}
					community={mockCommunity}
					variant="content"
				/>,
			);

			expect(
				screen.getByText(
					"Initial calculation of statistics is still in progress. Check back again in a few hours.",
				),
			).toBeInTheDocument();
			expect(
				screen.queryByText(
					"A calculation operation is currently in progress. Check back again later.",
				),
			).not.toBeInTheDocument();
		});

		it("should prioritize first_run_incomplete over caching_in_progress", () => {
			const dashboardConfig = {
				...baseDashboardConfig,
				first_run_incomplete: true,
				agg_in_progress: false,
				caching_in_progress: true,
			};

			mockUseStatsDashboard.mockReturnValue({
				dateRange: {
					start: new Date("2024-01-01"),
					end: new Date("2024-01-31"),
				},
				isLoading: false,
				isUpdating: false,
				error: null,
				stats: [],
			});

			render(
				<StatsDashboardPage
					dashboardConfig={dashboardConfig}
					community={mockCommunity}
					variant="content"
				/>,
			);

			expect(
				screen.getByText(
					"Initial calculation of statistics is still in progress. Check back again in a few hours.",
				),
			).toBeInTheDocument();
			expect(
				screen.queryByText(
					"A calculation operation is currently in progress. Check back again later.",
				),
			).not.toBeInTheDocument();
		});

		it("should show agg_in_progress message when agg_in_progress is true and stats is empty array", () => {
			const dashboardConfig = {
				...baseDashboardConfig,
				first_run_incomplete: false,
				agg_in_progress: true,
				caching_in_progress: false,
			};

			mockUseStatsDashboard.mockReturnValue({
				dateRange: {
					start: new Date("2024-01-01"),
					end: new Date("2024-01-31"),
				},
				isLoading: false,
				isUpdating: false,
				error: null,
				stats: [],
			});

			render(
				<StatsDashboardPage
					dashboardConfig={dashboardConfig}
					community={mockCommunity}
					variant="content"
				/>,
			);

			expect(screen.getByText("No Data Available")).toBeInTheDocument();
			expect(
				screen.getByText(
					"A calculation operation is currently in progress. Check back again later.",
				),
			).toBeInTheDocument();
		});

		it("should show caching_in_progress message when caching_in_progress is true and stats is empty array", () => {
			const dashboardConfig = {
				...baseDashboardConfig,
				first_run_incomplete: false,
				agg_in_progress: false,
				caching_in_progress: true,
			};

			mockUseStatsDashboard.mockReturnValue({
				dateRange: {
					start: new Date("2024-01-01"),
					end: new Date("2024-01-31"),
				},
				isLoading: false,
				isUpdating: false,
				error: null,
				stats: [],
			});

			render(
				<StatsDashboardPage
					dashboardConfig={dashboardConfig}
					community={mockCommunity}
					variant="content"
				/>,
			);

			expect(screen.getByText("No Data Available")).toBeInTheDocument();
			expect(
				screen.getByText(
					"A calculation operation is currently in progress. Check back again later.",
				),
			).toBeInTheDocument();
		});

		it("should show agg_in_progress message when both agg_in_progress and caching_in_progress are true", () => {
			const dashboardConfig = {
				...baseDashboardConfig,
				first_run_incomplete: false,
				agg_in_progress: true,
				caching_in_progress: true,
			};

			mockUseStatsDashboard.mockReturnValue({
				dateRange: {
					start: new Date("2024-01-01"),
					end: new Date("2024-01-31"),
				},
				isLoading: false,
				isUpdating: false,
				error: null,
				stats: [],
			});

			render(
				<StatsDashboardPage
					dashboardConfig={dashboardConfig}
					community={mockCommunity}
					variant="content"
				/>,
			);

			expect(screen.getByText("No Data Available")).toBeInTheDocument();
			expect(
				screen.getByText(
					"A calculation operation is currently in progress. Check back again later.",
				),
			).toBeInTheDocument();
		});

		it("should show default no data message when no flags are set and stats is empty array", () => {
			const dashboardConfig = {
				...baseDashboardConfig,
				first_run_incomplete: false,
				agg_in_progress: false,
				caching_in_progress: false,
			};

			mockUseStatsDashboard.mockReturnValue({
				dateRange: {
					start: new Date("2024-01-01"),
					end: new Date("2024-01-31"),
				},
				isLoading: false,
				isUpdating: false,
				error: null,
				stats: [],
			});

			render(
				<StatsDashboardPage
					dashboardConfig={dashboardConfig}
					community={mockCommunity}
					variant="content"
				/>,
			);

			expect(screen.getByText("No Data Available")).toBeInTheDocument();
			expect(
				screen.getByText(
					"No statistics data is available for the selected time period.",
				),
			).toBeInTheDocument();
		});

		it("should show first_run_incomplete message when first_run_incomplete is true and stats object is empty", () => {
			// Get the emptyStatsObject from the checkForEmptyStats tests
			const emptyStatsObject = [
				{
					usageSnapshotData: {
						global: {
							views: [],
						},
					},
				},
			];

			const dashboardConfig = {
				...baseDashboardConfig,
				first_run_incomplete: true,
				agg_in_progress: false,
				caching_in_progress: false,
			};

			mockUseStatsDashboard.mockReturnValue({
				dateRange: {
					start: new Date("2024-01-01"),
					end: new Date("2024-01-31"),
				},
				isLoading: false,
				isUpdating: false,
				error: null,
				stats: emptyStatsObject,
			});

			render(
				<StatsDashboardPage
					dashboardConfig={dashboardConfig}
					community={mockCommunity}
					variant="content"
				/>,
			);

			expect(screen.getByText("No Data Available")).toBeInTheDocument();
			expect(
				screen.getByText(
					"Initial calculation of statistics is still in progress. Check back again in a few hours.",
				),
			).toBeInTheDocument();
		});

		it("should show agg_in_progress message when agg_in_progress is true and stats object is empty", () => {
			const emptyStatsObject = [
				{
					usageSnapshotData: {
						global: {
							views: [],
						},
					},
				},
			];

			const dashboardConfig = {
				...baseDashboardConfig,
				first_run_incomplete: false,
				agg_in_progress: true,
				caching_in_progress: false,
			};

			mockUseStatsDashboard.mockReturnValue({
				dateRange: {
					start: new Date("2024-01-01"),
					end: new Date("2024-01-31"),
				},
				isLoading: false,
				isUpdating: false,
				error: null,
				stats: emptyStatsObject,
			});

			render(
				<StatsDashboardPage
					dashboardConfig={dashboardConfig}
					community={mockCommunity}
					variant="content"
				/>,
			);

			expect(screen.getByText("No Data Available")).toBeInTheDocument();
			expect(
				screen.getByText(
					"A calculation operation is currently in progress. Check back again later.",
				),
			).toBeInTheDocument();
		});

		it("should show caching_in_progress message when caching_in_progress is true and stats object is empty", () => {
			const emptyStatsObject = [
				{
					usageSnapshotData: {
						global: {
							views: [],
						},
					},
				},
			];

			const dashboardConfig = {
				...baseDashboardConfig,
				first_run_incomplete: false,
				agg_in_progress: false,
				caching_in_progress: true,
			};

			mockUseStatsDashboard.mockReturnValue({
				dateRange: {
					start: new Date("2024-01-01"),
					end: new Date("2024-01-31"),
				},
				isLoading: false,
				isUpdating: false,
				error: null,
				stats: emptyStatsObject,
			});

			render(
				<StatsDashboardPage
					dashboardConfig={dashboardConfig}
					community={mockCommunity}
					variant="content"
				/>,
			);

			expect(screen.getByText("No Data Available")).toBeInTheDocument();
			expect(
				screen.getByText(
					"A calculation operation is currently in progress. Check back again later.",
				),
			).toBeInTheDocument();
		});

		it("should show default no data message when no flags are set and stats object is empty", () => {
			const dashboardConfig = {
				...baseDashboardConfig,
				first_run_incomplete: false,
				agg_in_progress: false,
				caching_in_progress: false,
			};

			mockUseStatsDashboard.mockReturnValue({
				dateRange: {
					start: new Date("2024-01-01"),
					end: new Date("2024-01-31"),
				},
				isLoading: false,
				isUpdating: false,
				error: null,
				stats: EMPTY_STATS_OBJECT,
			});

			render(
				<StatsDashboardPage
					dashboardConfig={dashboardConfig}
					community={mockCommunity}
					variant="content"
				/>,
			);

			expect(screen.getByText("No Data Available")).toBeInTheDocument();
			expect(
				screen.getByText(
					"No statistics data is available for the selected time period.",
				),
			).toBeInTheDocument();
		});

		it("should not show no data message when isLoading is true, even with flags set", () => {
			const dashboardConfig = {
				...baseDashboardConfig,
				first_run_incomplete: true,
				agg_in_progress: true,
				caching_in_progress: true,
			};

			mockUseStatsDashboard.mockReturnValue({
				dateRange: {
					start: new Date("2024-01-01"),
					end: new Date("2024-01-31"),
				},
				isLoading: true,
				isUpdating: false,
				error: null,
				stats: null,
			});

			render(
				<StatsDashboardPage
					dashboardConfig={dashboardConfig}
					community={mockCommunity}
					variant="content"
				/>,
			);

			expect(screen.queryByText("No Data Available")).not.toBeInTheDocument();
		});

		it("should not show no data message when isUpdating is true, even with flags set", () => {
			const dashboardConfig = {
				...baseDashboardConfig,
				first_run_incomplete: true,
				agg_in_progress: true,
				caching_in_progress: true,
			};

			mockUseStatsDashboard.mockReturnValue({
				dateRange: {
					start: new Date("2024-01-01"),
					end: new Date("2024-01-31"),
				},
				isLoading: false,
				isUpdating: true,
				error: null,
				stats: null,
			});

			render(
				<StatsDashboardPage
					dashboardConfig={dashboardConfig}
					community={mockCommunity}
					variant="content"
				/>,
			);

			expect(screen.queryByText("No Data Available")).not.toBeInTheDocument();
		});

		it("should not show no data message when error is present, even with flags set", () => {
			const dashboardConfig = {
				...baseDashboardConfig,
				first_run_incomplete: true,
				agg_in_progress: true,
				caching_in_progress: true,
			};

			mockUseStatsDashboard.mockReturnValue({
				dateRange: {
					start: new Date("2024-01-01"),
					end: new Date("2024-01-31"),
				},
				isLoading: false,
				isUpdating: false,
				error: new Error("Test error"),
				stats: null,
			});

			render(
				<StatsDashboardPage
					dashboardConfig={dashboardConfig}
					community={mockCommunity}
					variant="content"
				/>,
			);

			expect(screen.queryByText("No Data Available")).not.toBeInTheDocument();
		});

		it("should not show no data message when stats are available, even with flags set", () => {
			const dashboardConfig = {
				...baseDashboardConfig,
				first_run_incomplete: true,
				agg_in_progress: true,
				caching_in_progress: true,
			};

			mockUseStatsDashboard.mockReturnValue({
				dateRange: {
					start: new Date("2024-01-01"),
					end: new Date("2024-01-31"),
				},
				isLoading: false,
				isUpdating: false,
				error: null,
				stats: [
					{
						year: 2024,
						usageSnapshotData: {
							global: {
								views: [1, 2, 3],
							},
						},
					},
				],
			});

			render(
				<StatsDashboardPage
					dashboardConfig={dashboardConfig}
					community={mockCommunity}
					variant="content"
				/>,
			);

			expect(screen.queryByText("No Data Available")).not.toBeInTheDocument();
		});
	});

	describe("Aggregation In Progress Message", () => {
		it("should show agg in progress message when stats exist, first_run is complete, and agg_in_progress is true", () => {
			const dashboardConfig = {
				...baseDashboardConfig,
				first_run_incomplete: false,
				agg_in_progress: true,
				caching_in_progress: false,
			};

			mockUseStatsDashboard.mockReturnValue({
				dateRange: {
					start: new Date("2024-01-01"),
					end: new Date("2024-01-31"),
				},
				isLoading: false,
				isUpdating: false,
				error: null,
				stats: [
					{
						year: 2024,
						usageSnapshotData: {
							global: {
								views: [1, 2, 3],
							},
						},
					},
				],
			});

			render(
				<StatsDashboardPage
					dashboardConfig={dashboardConfig}
					community={mockCommunity}
					variant="content"
				/>,
			);

			expect(
				screen.getByText(
					"Update calculation in progress. Check back soon for updated data.",
				),
			).toBeInTheDocument();
			expect(screen.queryByText("No Data Available")).not.toBeInTheDocument();
		});

		it("should show agg in progress message when stats exist, first_run is complete, and caching_in_progress is true", () => {
			const dashboardConfig = {
				...baseDashboardConfig,
				first_run_incomplete: false,
				agg_in_progress: false,
				caching_in_progress: true,
			};

			mockUseStatsDashboard.mockReturnValue({
				dateRange: {
					start: new Date("2024-01-01"),
					end: new Date("2024-01-31"),
				},
				isLoading: false,
				isUpdating: false,
				error: null,
				stats: [
					{
						year: 2024,
						usageSnapshotData: {
							global: {
								views: [1, 2, 3],
							},
						},
					},
				],
			});

			render(
				<StatsDashboardPage
					dashboardConfig={dashboardConfig}
					community={mockCommunity}
					variant="content"
				/>,
			);

			expect(
				screen.getByText(
					"Update calculation in progress. Check back soon for updated data.",
				),
			).toBeInTheDocument();
			expect(screen.queryByText("No Data Available")).not.toBeInTheDocument();
		});

		it("should show agg in progress message when stats exist, first_run is complete, and both agg_in_progress and caching_in_progress are true", () => {
			const dashboardConfig = {
				...baseDashboardConfig,
				first_run_incomplete: false,
				agg_in_progress: true,
				caching_in_progress: true,
			};

			mockUseStatsDashboard.mockReturnValue({
				dateRange: {
					start: new Date("2024-01-01"),
					end: new Date("2024-01-31"),
				},
				isLoading: false,
				isUpdating: false,
				error: null,
				stats: [
					{
						year: 2024,
						usageSnapshotData: {
							global: {
								views: [1, 2, 3],
							},
						},
					},
				],
			});

			render(
				<StatsDashboardPage
					dashboardConfig={dashboardConfig}
					community={mockCommunity}
					variant="content"
				/>,
			);

			expect(
				screen.getByText(
					"Update calculation in progress. Check back soon for updated data.",
				),
			).toBeInTheDocument();
			expect(screen.queryByText("No Data Available")).not.toBeInTheDocument();
		});

		it("should NOT show agg in progress message when first_run_incomplete is true, even with stats and agg_in_progress", () => {
			const dashboardConfig = {
				...baseDashboardConfig,
				first_run_incomplete: true,
				agg_in_progress: true,
				caching_in_progress: false,
			};

			mockUseStatsDashboard.mockReturnValue({
				dateRange: {
					start: new Date("2024-01-01"),
					end: new Date("2024-01-31"),
				},
				isLoading: false,
				isUpdating: false,
				error: null,
				stats: [
					{
						year: 2024,
						usageSnapshotData: {
							global: {
								views: [1, 2, 3],
							},
						},
					},
				],
			});

			render(
				<StatsDashboardPage
					dashboardConfig={dashboardConfig}
					community={mockCommunity}
					variant="content"
				/>,
			);

			expect(
				screen.queryByText(
					"Update calculation in progress. Check back soon for updated data.",
				),
			).not.toBeInTheDocument();
		});

		it("should NOT show agg in progress message when stats are empty, even with first_run complete and agg_in_progress", () => {
			const dashboardConfig = {
				...baseDashboardConfig,
				first_run_incomplete: false,
				agg_in_progress: true,
				caching_in_progress: false,
			};

			mockUseStatsDashboard.mockReturnValue({
				dateRange: {
					start: new Date("2024-01-01"),
					end: new Date("2024-01-31"),
				},
				isLoading: false,
				isUpdating: false,
				error: null,
				stats: [],
			});

			render(
				<StatsDashboardPage
					dashboardConfig={dashboardConfig}
					community={mockCommunity}
					variant="content"
				/>,
			);

			expect(
				screen.queryByText(
					"Update calculation in progress. Check back soon for updated data.",
				),
			).not.toBeInTheDocument();
		});

		it("should NOT show agg in progress message when stats are null, even with first_run complete and agg_in_progress", () => {
			const dashboardConfig = {
				...baseDashboardConfig,
				first_run_incomplete: false,
				agg_in_progress: true,
				caching_in_progress: false,
			};

			mockUseStatsDashboard.mockReturnValue({
				dateRange: {
					start: new Date("2024-01-01"),
					end: new Date("2024-01-31"),
				},
				isLoading: false,
				isUpdating: false,
				error: null,
				stats: null,
			});

			render(
				<StatsDashboardPage
					dashboardConfig={dashboardConfig}
					community={mockCommunity}
					variant="content"
				/>,
			);

			expect(
				screen.queryByText(
					"Update calculation in progress. Check back soon for updated data.",
				),
			).not.toBeInTheDocument();
		});

		it("should NOT show agg in progress message when neither agg_in_progress nor caching_in_progress is true", () => {
			const dashboardConfig = {
				...baseDashboardConfig,
				first_run_incomplete: false,
				agg_in_progress: false,
				caching_in_progress: false,
			};

			mockUseStatsDashboard.mockReturnValue({
				dateRange: {
					start: new Date("2024-01-01"),
					end: new Date("2024-01-31"),
				},
				isLoading: false,
				isUpdating: false,
				error: null,
				stats: [
					{
						year: 2024,
						usageSnapshotData: {
							global: {
								views: [1, 2, 3],
							},
						},
					},
				],
			});

			render(
				<StatsDashboardPage
					dashboardConfig={dashboardConfig}
					community={mockCommunity}
					variant="content"
				/>,
			);

			expect(
				screen.queryByText(
					"Update calculation in progress. Check back soon for updated data.",
				),
			).not.toBeInTheDocument();
		});

		it("should NOT show agg in progress message when isLoading is true", () => {
			const dashboardConfig = {
				...baseDashboardConfig,
				first_run_incomplete: false,
				agg_in_progress: true,
				caching_in_progress: false,
			};

			mockUseStatsDashboard.mockReturnValue({
				dateRange: {
					start: new Date("2024-01-01"),
					end: new Date("2024-01-31"),
				},
				isLoading: true,
				isUpdating: false,
				error: null,
				stats: [
					{
						year: 2024,
						usageSnapshotData: {
							global: {
								views: [1, 2, 3],
							},
						},
					},
				],
			});

			render(
				<StatsDashboardPage
					dashboardConfig={dashboardConfig}
					community={mockCommunity}
					variant="content"
				/>,
			);

			expect(
				screen.queryByText(
					"Update calculation in progress. Check back soon for updated data.",
				),
			).not.toBeInTheDocument();
		});

		it("should NOT show agg in progress message when isUpdating is true", () => {
			const dashboardConfig = {
				...baseDashboardConfig,
				first_run_incomplete: false,
				agg_in_progress: true,
				caching_in_progress: false,
			};

			mockUseStatsDashboard.mockReturnValue({
				dateRange: {
					start: new Date("2024-01-01"),
					end: new Date("2024-01-31"),
				},
				isLoading: false,
				isUpdating: true,
				error: null,
				stats: [
					{
						year: 2024,
						usageSnapshotData: {
							global: {
								views: [1, 2, 3],
							},
						},
					},
				],
			});

			render(
				<StatsDashboardPage
					dashboardConfig={dashboardConfig}
					community={mockCommunity}
					variant="content"
				/>,
			);

			expect(
				screen.queryByText(
					"Update calculation in progress. Check back soon for updated data.",
				),
			).not.toBeInTheDocument();
		});

		it("should NOT show agg in progress message when error is present", () => {
			const dashboardConfig = {
				...baseDashboardConfig,
				first_run_incomplete: false,
				agg_in_progress: true,
				caching_in_progress: false,
			};

			mockUseStatsDashboard.mockReturnValue({
				dateRange: {
					start: new Date("2024-01-01"),
					end: new Date("2024-01-31"),
				},
				isLoading: false,
				isUpdating: false,
				error: new Error("Test error"),
				stats: [
					{
						year: 2024,
						usageSnapshotData: {
							global: {
								views: [1, 2, 3],
							},
						},
					},
				],
			});

			render(
				<StatsDashboardPage
					dashboardConfig={dashboardConfig}
					community={mockCommunity}
					variant="content"
				/>,
			);

			expect(
				screen.queryByText(
					"Update calculation in progress. Check back soon for updated data.",
				),
			).not.toBeInTheDocument();
		});
	});

	describe("Component Rendering", () => {
		it("should render components from layout configuration", () => {
			mockUseStatsDashboard.mockReturnValue({
				dateRange: {
					start: new Date("2024-01-01"),
					end: new Date("2024-01-31"),
				},
				isLoading: false,
				isUpdating: false,
				error: null,
				stats: [
					{
						year: 2024,
						usageSnapshotData: {
							global: {
								views: [1, 2, 3],
							},
						},
					},
				],
			});

			render(
				<StatsDashboardPage
					dashboardConfig={baseDashboardConfig}
					community={mockCommunity}
					variant="content"
				/>,
			);

			expect(
				screen.getByTestId("single-stat-record-count"),
			).toBeInTheDocument();
		});

		it("should return null when variant does not match any tab", () => {
			const consoleSpy = jest
				.spyOn(console, "warn")
				.mockImplementation(() => {});

			mockUseStatsDashboard.mockReturnValue({
				dateRange: {
					start: new Date("2024-01-01"),
					end: new Date("2024-01-31"),
				},
				isLoading: false,
				isUpdating: false,
				error: null,
				stats: [],
			});

			const { container } = render(
				<StatsDashboardPage
					dashboardConfig={baseDashboardConfig}
					community={mockCommunity}
					variant="nonexistent"
				/>,
			);

			expect(container.firstChild).toBeNull();
			expect(consoleSpy).toHaveBeenCalledWith(
				"No tab found for variant: nonexistent",
			);

			consoleSpy.mockRestore();
		});
	});

	describe("Aria Labels and Accessibility", () => {
		it("should have proper aria-label for community dashboard", () => {
			mockUseStatsDashboard.mockReturnValue({
				dateRange: {
					start: new Date("2024-01-01"),
					end: new Date("2024-01-31"),
				},
				isLoading: false,
				isUpdating: false,
				error: null,
				stats: [],
			});

			render(
				<StatsDashboardPage
					dashboardConfig={baseDashboardConfig}
					community={mockCommunity}
					variant="content"
				/>,
			);

			const grid = screen.getByRole("main");
			expect(grid).toHaveAttribute(
				"aria-label",
				"Test Community Statistics Dashboard",
			);
		});

		it("should have proper aria-label for global dashboard", () => {
			const globalConfig = {
				...baseDashboardConfig,
				dashboard_type: "global",
			};

			mockUseStatsDashboard.mockReturnValue({
				dateRange: {
					start: new Date("2024-01-01"),
					end: new Date("2024-01-31"),
				},
				isLoading: false,
				isUpdating: false,
				error: null,
				stats: [],
			});

			render(
				<StatsDashboardPage
					dashboardConfig={globalConfig}
					community={null}
					variant="content"
				/>,
			);

			const grid = screen.getByRole("main");
			expect(grid).toHaveAttribute("aria-label", "Global Statistics Dashboard");
		});

		it("should use custom title from dashboardConfig when provided", () => {
			const configWithTitle = {
				...baseDashboardConfig,
				title: "Custom Dashboard Title",
			};

			mockUseStatsDashboard.mockReturnValue({
				dateRange: {
					start: new Date("2024-01-01"),
					end: new Date("2024-01-31"),
				},
				isLoading: false,
				isUpdating: false,
				error: null,
				stats: [],
			});

			render(
				<StatsDashboardPage
					dashboardConfig={configWithTitle}
					community={mockCommunity}
					variant="content"
				/>,
			);

			const grid = screen.getByRole("main");
			expect(grid).toHaveAttribute("aria-label", "Custom Dashboard Title");
		});
	});

	describe("Date Range Display", () => {
		it("should display date range phrase and display date range", () => {
			mockUseStatsDashboard.mockReturnValue({
				dateRange: {
					start: new Date("2024-01-01"),
					end: new Date("2024-01-31"),
				},
				isLoading: false,
				isUpdating: false,
				error: null,
				stats: [],
			});

			render(
				<StatsDashboardPage
					dashboardConfig={baseDashboardConfig}
					community={mockCommunity}
					variant="content"
					pageDateRangePhrase="Last 30 days"
					displayDateRange="Jan 1 - Jan 31, 2024"
				/>,
			);

			// The Label component should contain both the phrase and the date range
			const label = screen.getByText(/Last 30 days/);
			expect(label).toBeInTheDocument();
			expect(screen.getByText(/Jan 1 - Jan 31, 2024/)).toBeInTheDocument();
		});
	});

	describe("checkForEmptyStats", () => {
		it("should return true for empty stats array", () => {
			expect(checkForEmptyStats([])).toBe(true);
		});

		it("should return true for null stats", () => {
			expect(checkForEmptyStats(null)).toBe(true);
		});

		it("should return true for undefined stats", () => {
			expect(checkForEmptyStats(undefined)).toBe(true);
		});

		it("should return true for non-array stats", () => {
			expect(checkForEmptyStats({})).toBe(true);
			expect(checkForEmptyStats("not an array")).toBe(true);
		});

		it("should return true for the provided empty stats object", () => {
			expect(checkForEmptyStats(EMPTY_STATS_OBJECT)).toBe(true);
		});

		it("should return false when stats contain non-empty arrays at top level", () => {
			const statsWithData = [
				{
					usageSnapshotData: {
						global: {
							views: [1, 2, 3],
						},
					},
				},
			];
			expect(checkForEmptyStats(statsWithData)).toBe(false);
		});

		it("should return false when stats contain non-empty arrays in nested structure", () => {
			const statsWithData = [
				{
					usageSnapshotData: {
						global: {
							views: [],
							downloads: [10, 20, 30],
						},
					},
				},
			];
			expect(checkForEmptyStats(statsWithData)).toBe(false);
		});

		it("should return false when filePresence contains objects with non-empty data arrays", () => {
			const statsWithData = [
				{
					recordSnapshotDataAdded: {
						filePresence: {
							records: [
								{
									id: "metadata_only",
									name: "Metadata Only",
									data: [1, 2, 3],
									type: "line",
									valueType: "number",
								},
							],
						},
					},
				},
			];
			expect(checkForEmptyStats(statsWithData)).toBe(false);
		});

		it("should return true when filePresence contains objects but all data arrays are empty", () => {
			const statsWithEmptyFilePresence = [
				{
					recordSnapshotDataAdded: {
						filePresence: {
							records: [
								{
									id: "metadata_only",
									name: "Metadata Only",
									data: [],
									type: "line",
									valueType: "number",
								},
								{
									id: "with_files",
									name: "With Files",
									data: [],
									type: "line",
									valueType: "number",
								},
							],
						},
					},
				},
			];
			expect(checkForEmptyStats(statsWithEmptyFilePresence)).toBe(true);
		});

		it("should return false when any year has data even if others are empty", () => {
			const mixedStats = [
				{
					usageSnapshotData: {
						global: {
							views: [],
						},
					},
				},
				{
					usageSnapshotData: {
						global: {
							views: [1, 2, 3],
						},
					},
				},
			];
			expect(checkForEmptyStats(mixedStats)).toBe(false);
		});

		it("should return true when all years are empty", () => {
			const allEmptyStats = [
				{
					usageSnapshotData: {
						global: {
							views: [],
						},
					},
				},
				{
					usageSnapshotData: {
						global: {
							views: [],
						},
					},
				},
			];
			expect(checkForEmptyStats(allEmptyStats)).toBe(true);
		});
	});
});
