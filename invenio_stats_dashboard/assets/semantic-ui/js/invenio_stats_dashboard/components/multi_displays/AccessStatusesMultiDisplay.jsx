// Part of the Invenio-Stats-Dashboard extension for InvenioRDM
// Copyright (C) 2025 Mesh Research
//
// Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
// it under the terms of the MIT License; see LICENSE file for more details.

import React from "react";
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { StatsMultiDisplay } from "../shared_components/StatsMultiDisplay";
import { PropTypes } from "prop-types";
import { useStatsDashboard } from "../../context/StatsDashboardContext";
import { CHART_COLORS } from '../../constants';
import {
  transformMultiDisplayData,
  assembleMultiDisplayRows,
  extractRecordBasedData,
  generateMultiDisplayChartOptions
} from "../../utils/multiDisplayHelpers";

const AccessStatusesMultiDisplay = ({
  title = i18next.t("Access Rights"),
  icon: labelIcon = "lock",
  headers = [i18next.t("Access Right"), i18next.t("Works")],
  default_view = "pie",
  pageSize = 10,
  available_views = ["pie", "bar", "list"],
  ...otherProps
}) => {
  const { stats, recordStartBasis, dateRange, isLoading } = useStatsDashboard();

  const rawAccessStatuses = extractRecordBasedData(stats, recordStartBasis, 'accessStatuses', dateRange);

  const { transformedData, otherData, totalCount } = transformMultiDisplayData(
    rawAccessStatuses,
    pageSize,
    'metadata.access_status.id',
    CHART_COLORS.secondary
  );
  const rowsWithLinks = assembleMultiDisplayRows(transformedData, otherData);

  const hasData = !isLoading && (transformedData.length > 0 || (otherData && otherData.value > 0));

  const chartOptions = generateMultiDisplayChartOptions(transformedData, otherData, available_views);

  return (
    <StatsMultiDisplay
      title={title}
      icon={labelIcon}
      label={"access-rights"}
      headers={headers}
      rows={rowsWithLinks}
      chartOptions={chartOptions}
      defaultViewMode={default_view}
      isLoading={isLoading}
      hasData={hasData}
      onEvents={{
        click: (params) => {
          if (params.data && params.data.id) {
            window.open(params.data.link, '_blank');
          }
        }
      }}
      {...otherProps}
    />
  );
};

AccessStatusesMultiDisplay.propTypes = {
  title: PropTypes.string,
  icon: PropTypes.string,
  headers: PropTypes.array,
  rows: PropTypes.array,
  default_view: PropTypes.string,
  available_views: PropTypes.arrayOf(PropTypes.string),
};

export { AccessStatusesMultiDisplay };