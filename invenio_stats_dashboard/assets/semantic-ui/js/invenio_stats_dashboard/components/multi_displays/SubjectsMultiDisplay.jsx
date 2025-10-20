// Part of the Invenio-Stats-Dashboard extension for InvenioRDM
// Copyright (C) 2025 Mesh Research
//
// Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
// it under the terms of the MIT License; see LICENSE file for more details.

import React, { useState, useEffect } from "react";
import PropTypes from "prop-types";
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { StatsMultiDisplay } from "../shared_components/StatsMultiDisplay";
import { useStatsDashboard } from "../../context/StatsDashboardContext";
import { CHART_COLORS } from "../../constants";
import { formatDate } from "../../utils";
import {
  transformMultiDisplayData,
  assembleMultiDisplayRows,
  extractData,
  generateMultiDisplayChartOptions,
} from "../../utils/multiDisplayHelpers";

const SubjectsMultiDisplay = ({
  title = i18next.t("Subjects"),
  icon: labelIcon = "tag",
  pageSize = 10,
  headers = [i18next.t("Subject"), i18next.t("Works")],
  default_view = "pie",
  available_views = ["pie", "bar", "list"],
  hideOtherInCharts = false,
  ...otherProps
}) => {
  const { stats, dateRange, isLoading } = useStatsDashboard();
  const [subtitle, setSubtitle] = useState(null);

  useEffect(() => {
    if (dateRange) {
      setSubtitle(
        i18next.t("as of") + " " + formatDate(dateRange.end, "day", true),
      );
    }
  }, [dateRange]);

  const rawSubjects = extractData(
    stats,
    "added",
    "subjects",
    "records",
    dateRange,
    false,
    false,
  );
  const globalData = extractData(
    stats,
    "added",
    "global",
    "records",
    dateRange,
    false,
    false,
  );

  const {
    transformedData,
    otherData,
    originalOtherData,
    totalCount,
    otherPercentage,
  } = transformMultiDisplayData(
    rawSubjects,
    pageSize,
    "metadata.subjects.id",
    CHART_COLORS.secondary,
    hideOtherInCharts,
    globalData,
    false, // isDelta = false for snapshot data
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
      label={"subjects"}
      headers={headers}
      rows={rowsWithLinks}
      chartOptions={chartOptions}
      defaultViewMode={default_view}
      isLoading={isLoading}
      isDelta={false}
      dateRangeEnd={dateRange?.end}
      onEvents={{
        click: (params) => {
          if (params.data && params.data.id) {
            window.open(params.data.link, "_blank");
          }
        },
      }}
      {...otherProps}
    />
  );
};

SubjectsMultiDisplay.propTypes = {
  title: PropTypes.string,
  icon: PropTypes.string,
  headers: PropTypes.array,
  rows: PropTypes.array,
  default_view: PropTypes.string,
  pageSize: PropTypes.number,
  available_views: PropTypes.arrayOf(PropTypes.string),
  hideOtherInCharts: PropTypes.bool,
};

export { SubjectsMultiDisplay };

