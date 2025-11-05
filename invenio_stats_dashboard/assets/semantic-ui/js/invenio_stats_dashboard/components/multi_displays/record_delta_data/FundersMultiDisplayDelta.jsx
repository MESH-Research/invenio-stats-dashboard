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
  transformMultiDisplayData,
  assembleMultiDisplayRows,
  extractData,
  generateMultiDisplayChartOptions
} from "../../../utils/multiDisplayHelpers";

const FundersMultiDisplayDelta = ({
  title = i18next.t("Funders"),
  icon: labelIcon = "money bill",
  headers = [i18next.t("Funder"), i18next.t("Works")],
  default_view = "pie",
  pageSize = 10,
  available_views = ["pie", "bar", "list"],
  hideOtherInCharts = false,
  ...otherProps
}) => {
  const { stats, recordStartBasis, dateRange, isLoading } = useStatsDashboard();
  const [subtitle, setSubtitle] = useState(null);

  useEffect(() => {
    if (dateRange) {
      setSubtitle(i18next.t("during") + " " + formatDate(dateRange.start, 'day', true, dateRange.end));
    }
  }, [dateRange]);

  // Extract and process funders data using DELTA data (period-restricted)
  const rawFunders = extractData(stats, recordStartBasis, 'funders', 'records', dateRange, true, false);

  const { transformedData, otherData, originalOtherData, totalCount, otherPercentage } = transformMultiDisplayData(
    rawFunders,
    pageSize,
    'metadata.funding.funder.name',
    CHART_COLORS.secondary,
    hideOtherInCharts
  );
  const rowsWithLinks = assembleMultiDisplayRows(transformedData, otherData);


  const chartOptions = generateMultiDisplayChartOptions(transformedData, otherData, available_views, otherPercentage, originalOtherData, hideOtherInCharts);

  return (
    <StatsMultiDisplay
      title={title}
      subtitle={subtitle}
      icon={labelIcon}
      headers={headers}
      default_view={default_view}
      available_views={available_views}
      pageSize={pageSize}
      totalCount={totalCount}
      chartOptions={chartOptions}
      rows={rowsWithLinks}
      label={"funders"}
      isLoading={isLoading}
      {...otherProps}
    />
  );
};

FundersMultiDisplayDelta.propTypes = {
  title: PropTypes.string,
  icon: PropTypes.string,
  headers: PropTypes.array,
  default_view: PropTypes.string,
  pageSize: PropTypes.number,
  available_views: PropTypes.arrayOf(PropTypes.string),
  hideOtherInCharts: PropTypes.bool,
};

export { FundersMultiDisplayDelta };
