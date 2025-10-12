// Part of the Invenio-Stats-Dashboard extension for InvenioRDM
// Copyright (C) 2025 Mesh Research
//
// Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
// it under the terms of the MIT License; see LICENSE file for more details.

import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { StatsMultiDisplay } from '../shared_components/StatsMultiDisplay';
import { useStatsDashboard } from '../../context/StatsDashboardContext';
import { CHART_COLORS } from '../../constants';
import { formatDate } from '../../utils';
import {
  transformMultiDisplayData,
  assembleMultiDisplayRows,
  extractData,
  generateMultiDisplayChartOptions,
} from "../../utils/multiDisplayHelpers";

const SubjectsMultiDisplayDelta = ({
  title = i18next.t("Subjects"),
  icon: labelIcon = "tag",
  pageSize = 10,
  headers = [i18next.t("Subject"), i18next.t("Works")],
  default_view = "pie",
  available_views = ["pie", "bar", "list"],
  ...otherProps
}) => {
  const { stats, recordStartBasis, dateRange, isLoading } = useStatsDashboard();
  const [subtitle, setSubtitle] = useState(null);

  useEffect(() => {
    if (dateRange) {
      setSubtitle(i18next.t("during") + " " + formatDate(dateRange.start, 'day', true, dateRange.end));
    }
  }, [dateRange]);

  // Extract and process subjects data using DELTA data (period-restricted)
  const rawSubjects = extractData(stats, recordStartBasis, 'subjects', 'records', dateRange, true, false);

  const { transformedData, otherData, originalOtherData, totalCount, otherPercentage } = transformMultiDisplayData(
    rawSubjects,
    pageSize,
    'metadata.subjects.subject.id',
    CHART_COLORS.secondary,
    false // hideOtherInCharts - set to true to enable the new behavior
  );
  const rowsWithLinks = assembleMultiDisplayRows(transformedData, otherData);

  // Check if there's any data to display
  const hasData = !isLoading && (transformedData.length > 0 || (otherData && otherData.value > 0));

  const chartOptions = generateMultiDisplayChartOptions(transformedData, otherData, available_views, otherPercentage, originalOtherData);

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
      label={"subjects"}
      isLoading={isLoading}
      hasData={hasData}
      {...otherProps}
    />
  );
};

SubjectsMultiDisplayDelta.propTypes = {
  title: PropTypes.string,
  icon: PropTypes.string,
  headers: PropTypes.array,
  default_view: PropTypes.string,
  pageSize: PropTypes.number,
  available_views: PropTypes.arrayOf(PropTypes.string),
};

export { SubjectsMultiDisplayDelta };
