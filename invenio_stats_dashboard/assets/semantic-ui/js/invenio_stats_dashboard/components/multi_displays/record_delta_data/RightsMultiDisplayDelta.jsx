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

const RightsMultiDisplayDelta = ({
  title = i18next.t("Rights"),
  icon: labelIcon = "copyright",
  headers = [i18next.t("Rights"), i18next.t("Works")],
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

  // Extract and process rights data using DELTA data (period-restricted)
  const rawRights = extractData(stats, recordStartBasis, 'rights', 'records', dateRange, true, false);

  const { transformedData, otherData, originalOtherData, totalCount, otherPercentage } = transformMultiDisplayData(
    rawRights,
    pageSize,
    'metadata.rights.id',
    CHART_COLORS.secondary,
    hideOtherInCharts,
    null,
    true, // isDelta = true for delta data
  );
  const rowsWithLinks = assembleMultiDisplayRows(transformedData, otherData);


  const chartOptions = generateMultiDisplayChartOptions(transformedData, otherData, available_views, otherPercentage, originalOtherData, hideOtherInCharts);

  return (
    <StatsMultiDisplay
      title={title}
      subtitle={subtitle}
      icon={labelIcon}
      headers={headers}
      defaultViewMode={default_view}
      available_views={available_views}
      pageSize={pageSize}
      totalCount={totalCount}
      chartOptions={chartOptions}
      rows={rowsWithLinks}
      label={"rights"}
      isLoading={isLoading}
      hideOtherInCharts={hideOtherInCharts}
      {...otherProps}
    />
  );
};

RightsMultiDisplayDelta.propTypes = {
  title: PropTypes.string,
  icon: PropTypes.string,
  headers: PropTypes.array,
  default_view: PropTypes.string,
  pageSize: PropTypes.number,
  available_views: PropTypes.array,
  hideOtherInCharts: PropTypes.bool,
};

export { RightsMultiDisplayDelta };
