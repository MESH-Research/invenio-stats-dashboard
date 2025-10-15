// Part of the Invenio-Stats-Dashboard extension for InvenioRDM
// Copyright (C) 2025 Mesh Research
//
// Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
// it under the terms of the MIT License; see LICENSE file for more details.

import React, { useState, useEffect } from "react";
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { StatsMultiDisplay } from "../shared_components/StatsMultiDisplay";
import { PropTypes } from "prop-types";
import { useStatsDashboard } from "../../context/StatsDashboardContext";
import { CHART_COLORS, RECORD_START_BASES } from '../../constants';
import { formatDate } from "../../utils";
import {
  transformMultiDisplayData,
  assembleMultiDisplayRows,
  extractData,
  generateMultiDisplayChartOptions
} from "../../utils/multiDisplayHelpers";

const LanguagesMultiDisplayDelta = ({
  title = i18next.t("Languages"),
  icon: labelIcon = "language",
  headers = [i18next.t("Language"), i18next.t("Works")],
  default_view = "pie",
  pageSize = 10,
  available_views = ["pie", "bar", "list"],
  hideOtherInCharts = false,
  ...otherProps
}) => {
  const { stats, recordStartBasis, dateRange } = useStatsDashboard();
  const [subtitle, setSubtitle] = useState(null);

  useEffect(() => {
    if (dateRange) {
      setSubtitle(i18next.t("during") + " " + formatDate(dateRange.start, 'day', true, dateRange.end));
    }
  }, [dateRange]);

  // Extract and process languages data using DELTA data (period-restricted)
  const rawLanguages = extractData(stats, recordStartBasis, 'languages', 'records', dateRange, true, false);

  const { transformedData, otherData, originalOtherData, totalCount, otherPercentage } = transformMultiDisplayData(
    rawLanguages,
    pageSize,
    'metadata.languages.title',
    CHART_COLORS.secondary,
    hideOtherInCharts
  );
  const rowsWithLinks = assembleMultiDisplayRows(transformedData, otherData);

  const chartOptions = generateMultiDisplayChartOptions(transformedData, otherData, available_views, otherPercentage, originalOtherData, hideOtherInCharts);

  const hasData = !isLoading && (transformedData.length > 0 || (otherData && otherData.value > 0));

  return (
    <StatsMultiDisplay
      title={title}
      subtitle={subtitle}
      icon={labelIcon}
      label={"languages"}
      headers={headers}
      rows={rowsWithLinks}
        chartOptions={chartOptions}
      defaultViewMode={default_view}
      hasData={hasData}
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

LanguagesMultiDisplayDelta.propTypes = {
  title: PropTypes.string,
  icon: PropTypes.string,
  headers: PropTypes.array,
  default_view: PropTypes.string,
  pageSize: PropTypes.number,
  available_views: PropTypes.arrayOf(PropTypes.string),
  hideOtherInCharts: PropTypes.bool,
};

export { LanguagesMultiDisplayDelta };
