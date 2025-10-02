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

const RightsMultiDisplay = ({
  title = i18next.t("Rights"),
  icon: labelIcon = "copyright",
  headers = [i18next.t("Rights"), i18next.t("Works")],
  default_view = "pie",
  pageSize = 10,
  available_views = ["pie", "bar", "list"],
  ...otherProps
}) => {
  const { stats, recordStartBasis, dateRange, isLoading } = useStatsDashboard();

  const rawRights = extractRecordBasedData(stats, recordStartBasis, 'rights', dateRange);

  const { transformedData, otherData, totalCount } = transformMultiDisplayData(
    rawRights,
    pageSize,
    'metadata.rights.id',
    CHART_COLORS.secondary
  );
  const rowsWithLinks = assembleMultiDisplayRows(transformedData, otherData);

  // Check if there's any data to display
  const hasData = !isLoading && (transformedData.length > 0 || (otherData && otherData.value > 0));


  const chartOptions = generateMultiDisplayChartOptions(transformedData, otherData, available_views);

  return (
    <StatsMultiDisplay
      title={title}
      icon={labelIcon}
      headers={headers}
      default_view={default_view}
      available_views={available_views}
      pageSize={pageSize}
      totalCount={totalCount}
      chartOptions={chartOptions}
      rows={rowsWithLinks}
      label={"rights"}
      isLoading={isLoading}
      hasData={hasData}
      {...otherProps}
    />
  );
};

RightsMultiDisplay.propTypes = {
  title: PropTypes.string,
  icon: PropTypes.string,
  headers: PropTypes.array,
  default_view: PropTypes.string,
  pageSize: PropTypes.number,
  available_views: PropTypes.array,
};

export { RightsMultiDisplay };
