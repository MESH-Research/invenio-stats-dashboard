// Part of the Invenio-Stats-Dashboard extension for InvenioRDM
// Copyright (C) 2025 Mesh Research
//
// Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
// it under the terms of the MIT License; see LICENSE file for more details.

import React, { useState, useEffect } from "react";
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { StatsMultiDisplay } from "../../shared_components/StatsMultiDisplay";
import { PropTypes } from "prop-types";
import { useStatsDashboard } from "../../../context/StatsDashboardContext";
import { CHART_COLORS } from "../../../constants";
import { formatDate } from "../../../utils";
import {
  transformCountryMultiDisplayData,
  assembleMultiDisplayRows,
  extractData,
  generateMultiDisplayChartOptions
} from "../../../utils/multiDisplayHelpers";

const CountriesMultiDisplayViews = ({
  title = i18next.t("Countries"),
  icon: labelIcon = "globe",
  headers = [i18next.t("Country"), i18next.t("Visits")],
  default_view = "pie",
  pageSize = 10,
  available_views = ["pie", "bar", "list"],
  hideOtherInCharts = false,
  ...otherProps
}) => {
  const { stats, dateRange } = useStatsDashboard();
  const [subtitle, setSubtitle] = useState(null);

  useEffect(() => {
    if (dateRange) {
      setSubtitle(i18next.t("as of") + " " + formatDate(dateRange.end, 'day', true));
    }
  }, [dateRange]);

  // Extract and process countries data
  const rawCountries = extractData(stats, null, 'countriesByView', 'views', dateRange, false, true);
  const globalData = extractData(stats, null, 'global', 'views', dateRange, false, true);

  const { transformedData, otherData, originalOtherData, totalCount, otherPercentage } = transformCountryMultiDisplayData(
    rawCountries,
    pageSize,
    "metadata.country.id",
    CHART_COLORS.secondary,
    hideOtherInCharts,
    globalData,
    false // isDelta = false for snapshot data
  );
  const rowsWithLinks = assembleMultiDisplayRows(transformedData, otherData);

  const chartOptions = generateMultiDisplayChartOptions(transformedData, otherData, available_views, otherPercentage, originalOtherData, hideOtherInCharts);

  return (
    <StatsMultiDisplay
      title={title}
      subtitle={subtitle}
      icon={labelIcon}
      label={"countries"}
      headers={headers}
      rows={rowsWithLinks}
        chartOptions={chartOptions}
      defaultViewMode={default_view}
      isDelta={false}
      dateRangeEnd={dateRange?.end}
      metricType="views"
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

CountriesMultiDisplayViews.propTypes = {
  title: PropTypes.string,
  icon: PropTypes.string,
  headers: PropTypes.array,
  default_view: PropTypes.string,
  pageSize: PropTypes.number,
  available_views: PropTypes.arrayOf(PropTypes.string),
  hideOtherInCharts: PropTypes.bool,
  width: PropTypes.number,
};

export { CountriesMultiDisplayViews };
