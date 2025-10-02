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
import { CHART_COLORS, RECORD_START_BASES } from '../../constants';
import {
  transformMultiDisplayData,
  assembleMultiDisplayRows,
  extractRecordBasedData,
  generateMultiDisplayChartOptions
} from "../../utils/multiDisplayHelpers";

const AffiliationsMultiDisplay = ({
  title = i18next.t("Affiliations"),
  icon: labelIcon = "university",
  headers = [i18next.t("Affiliation"), i18next.t("Works")],
  default_view,
  pageSize = 10,
  available_views = ["list", "pie", "bar"],
  ...otherProps
}) => {
  const { stats, recordStartBasis, dateRange, isLoading } = useStatsDashboard();

  // Extract and process affiliations data
  const rawAffiliations = extractRecordBasedData(stats, recordStartBasis, 'affiliations', dateRange);

  const { transformedData, otherData, totalCount } = transformMultiDisplayData(
    rawAffiliations,
    pageSize,
    'metadata.affiliations.affiliation',
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
      label={"affiliations"}
      headers={headers}
      rows={rowsWithLinks}
      chartOptions={chartOptions}
      defaultViewMode={default_view || available_views[0]}
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

AffiliationsMultiDisplay.propTypes = {
  title: PropTypes.string,
  icon: PropTypes.string,
  headers: PropTypes.array,
  rows: PropTypes.array,
  default_view: PropTypes.string,
  available_views: PropTypes.arrayOf(PropTypes.string),
};

export { AffiliationsMultiDisplay };