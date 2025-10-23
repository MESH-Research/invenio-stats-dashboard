// Part of the Invenio-Stats-Dashboard extension for InvenioRDM
// Copyright (C) 2025 Mesh Research
//
// Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
// it under the terms of the MIT License; see LICENSE file for more details.

import React, { useState, useEffect } from "react";
import PropTypes from "prop-types";
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { StatsMultiDisplay } from "../shared_components/StatsMultiDisplay";
import { formatNumber } from "../../utils";
import { CHART_COLORS } from "../../constants";
import { fetchRecords } from "../../api/api";
import { useStatsDashboard } from "../../context/StatsDashboardContext";
import {
  transformMultiDisplayData,
  assembleMultiDisplayRows,
  generateMultiDisplayChartOptions,
} from "../../utils/multiDisplayHelpers";
import { createTruncatedTitle } from "../../utils/textTruncation";

const MostViewedRecordsMultiDisplay = ({
  title = i18next.t("Most Viewed Works"),
  pageSize = 10,
  available_views = ["list"],
  default_view = "list",
  maxHeight = null, // Optional max height for scrollable list
}) => {
  const { dateRange } = useStatsDashboard();
  const [records, setRecords] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const loadMostViewedRecords = async () => {
      try {
        setIsLoading(true);
        setError(null);
        const response = await fetchRecords(
          "mostviewed",
          1,
          pageSize,
          dateRange,
        );
        setRecords(response.hits?.hits || []);
      } catch (err) {
        console.error("Error loading most viewed records:", err);
        setError(err);
      } finally {
        setIsLoading(false);
      }
    };

    loadMostViewedRecords();
  }, [pageSize, dateRange]);

  // Transform the API response into the format expected by StatsMultiDisplay
  const transformedData = records.map((record, index) => ({
    name: record.metadata?.title || "Untitled",
    value: record.stats?.all_versions?.views || 0, // Use stats.all_versions.views
    percentage: 0, // We'll calculate this if needed
    link: record.links?.self_html,
    itemStyle: {
      color: CHART_COLORS.secondary[index % CHART_COLORS.secondary.length],
    },
  }));

  const rowsWithLinks = transformedData.map(({ name, value, link }) => [
    null,
    createTruncatedTitle(
      name,
      link ? (
        <a href={link} target="_blank" rel="noopener noreferrer">
          {name}
        </a>
      ) : null,
      60,
    ),
    `${formatNumber(value, "compact")}`,
  ]);

  const chartOptions = generateMultiDisplayChartOptions(
    transformedData,
    null,
    available_views,
  );

  return (
    <StatsMultiDisplay
      title={title || i18next.t("Most Viewed Records")}
      subtitle={i18next.t("all time")}
      icon="eye"
      label="viewed_records"
      headers={[i18next.t("Record"), i18next.t("Views")]}
      rows={rowsWithLinks}
      chartOptions={chartOptions}
      defaultViewMode={default_view || available_views[0]}
      pageSize={pageSize}
      isLoading={isLoading}
      maxHeight={maxHeight}
      onEvents={{
        click: (params) => {
          if (params.data && params.data.link) {
            window.open(params.data.link, "_blank");
          }
        },
      }}
    />
  );
};

MostViewedRecordsMultiDisplay.propTypes = {
  title: PropTypes.string,
  pageSize: PropTypes.number,
  available_views: PropTypes.arrayOf(PropTypes.string),
  default_view: PropTypes.string,
  maxHeight: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  width: PropTypes.number,
};

export { MostViewedRecordsMultiDisplay };
