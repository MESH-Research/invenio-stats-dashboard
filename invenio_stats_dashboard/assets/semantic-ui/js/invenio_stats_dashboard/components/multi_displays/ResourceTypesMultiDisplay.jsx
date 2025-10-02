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

const ResourceTypesMultiDisplay = ({
  title = i18next.t("Resource Types"),
  icon: labelIcon = "file",
  headers = [i18next.t("Work Type"), i18next.t("Works")],
  default_view = "pie",
  pageSize = 10,
  available_views = ["pie", "bar", "list"],
  ...otherProps
}) => {
  const { stats, recordStartBasis, dateRange } = useStatsDashboard();

  // Extract and process resource types data
  const rawResourceTypes = extractRecordBasedData(stats, recordStartBasis, 'resourceTypes', dateRange);

  const { transformedData, otherData, totalCount } = transformMultiDisplayData(
    rawResourceTypes,
    pageSize,
    'metadata.resource_type.id',
    CHART_COLORS.secondary
  );
  const rowsWithLinks = assembleMultiDisplayRows(transformedData, otherData);

  const getChartOptions = () => {
    return generateMultiDisplayChartOptions(transformedData, otherData, available_views);
  };

  return (
    <StatsMultiDisplay
      title={title}
      icon={labelIcon}
      label={"resource-types"}
      headers={headers}
      rows={rowsWithLinks}
      chartOptions={getChartOptions()}
      defaultViewMode={default_view}
      onEvents={{
        click: (params) => {
          if (params.data && params.data.id) {
            window.open(`/search?q=metadata.resource_type.id:${params.data.id}`, '_blank');
          }
        }
      }}
      {...otherProps}
    />
  );
};

ResourceTypesMultiDisplay.propTypes = {
  title: PropTypes.string,
  icon: PropTypes.string,
  headers: PropTypes.array,
  rows: PropTypes.array,
  default_view: PropTypes.string,
  available_views: PropTypes.arrayOf(PropTypes.string),
};

export { ResourceTypesMultiDisplay };