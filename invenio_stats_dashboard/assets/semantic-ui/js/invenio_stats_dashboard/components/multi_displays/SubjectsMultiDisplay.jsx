// Part of the Invenio-Stats-Dashboard extension for InvenioRDM
// Copyright (C) 2025 Mesh Research
//
// Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
// it under the terms of the MIT License; see LICENSE file for more details.

import React from 'react';
import PropTypes from 'prop-types';
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { StatsMultiDisplay } from '../shared_components/StatsMultiDisplay';
import { useStatsDashboard } from '../../context/StatsDashboardContext';
import { CHART_COLORS } from '../../constants';
import {
  transformMultiDisplayData,
  assembleMultiDisplayRows,
  extractRecordBasedData,
  generateMultiDisplayChartOptions,
} from "../../utils/multiDisplayHelpers";

const SubjectsMultiDisplay = ({
  title = i18next.t("Subjects"),
  icon: labelIcon = "tag",
  pageSize = 10,
  headers = [i18next.t("Subject"), i18next.t("Works")],
  default_view = "pie",
  available_views = ["pie", "bar", "list"],
  ...otherProps
}) => {
  const { stats, dateRange, isLoading } = useStatsDashboard();

  const rawSubjects = extractRecordBasedData(stats, 'added', 'subjects', dateRange);

  const { transformedData, otherData, totalCount } = transformMultiDisplayData(
    rawSubjects,
    pageSize,
    'metadata.subjects.subject.id',
    CHART_COLORS.secondary
  );
  const rowsWithLinks = assembleMultiDisplayRows(transformedData, otherData);

  const hasData = !isLoading && (transformedData.length > 0 || (otherData && otherData.value > 0));

  const chartOptions = generateMultiDisplayChartOptions(transformedData, otherData, available_views);

  return (
    <StatsMultiDisplay
      title={title}
      icon={labelIcon}
      label={"subjects"}
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

SubjectsMultiDisplay.propTypes = {
  title: PropTypes.string,
  icon: PropTypes.string,
  headers: PropTypes.array,
  rows: PropTypes.array,
  default_view: PropTypes.string,
  pageSize: PropTypes.number,
  available_views: PropTypes.arrayOf(PropTypes.string),
};

export { SubjectsMultiDisplay };