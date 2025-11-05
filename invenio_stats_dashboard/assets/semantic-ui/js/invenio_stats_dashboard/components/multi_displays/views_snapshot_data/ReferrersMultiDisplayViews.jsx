// Part of the Invenio-Stats-Dashboard extension for InvenioRDM
// Copyright (C) 2025 Mesh Research
//
// Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
// it under the terms of the MIT License; see LICENSE file for more details.

import React from "react";
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { StatsMultiDisplay } from "../../shared_components/StatsMultiDisplay";
import { PropTypes } from "prop-types";
import { useStatsDashboard } from "../../../context/StatsDashboardContext";
import { CHART_COLORS } from "../../../constants";
import {
  transformMultiDisplayData,
  assembleMultiDisplayRows,
  extractData,
  generateMultiDisplayChartOptions
} from "../../../utils/multiDisplayHelpers";

const ReferrersMultiDisplayViews = ({
  title = i18next.t("Referrers"),
  icon: labelIcon = "external alternate",
  headers = [i18next.t("Referrer"), i18next.t("Visits")],
  default_view = "pie",
  pageSize = 10,
  available_views = ["pie", "bar", "list"],
  ...otherProps
}) => {
  const { stats, dateRange } = useStatsDashboard();

  const rawReferrers = extractData(stats, null, 'referrersByView', 'views', dateRange, false, true);
  const globalData = extractData(stats, null, 'global', 'views', dateRange, false, true);

  const { transformedData, otherData, totalCount } = transformMultiDisplayData(
    rawReferrers,
    pageSize,
    "metadata.referrer.id",
    CHART_COLORS.secondary,
    false, // hideOtherInCharts
    globalData,
    false // isDelta = false for snapshot data
  );
  const rowsWithLinks = assembleMultiDisplayRows(transformedData, otherData);

  const chartOptions = generateMultiDisplayChartOptions(transformedData, otherData, available_views);

  return (
    <StatsMultiDisplay
      title={title}
      icon={labelIcon}
      label={"referrers"}
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

ReferrersMultiDisplayViews.propTypes = {
  title: PropTypes.string,
  icon: PropTypes.string,
  headers: PropTypes.array,
  default_view: PropTypes.string,
  pageSize: PropTypes.number,
  available_views: PropTypes.arrayOf(PropTypes.string),
};

export { ReferrersMultiDisplayViews };
