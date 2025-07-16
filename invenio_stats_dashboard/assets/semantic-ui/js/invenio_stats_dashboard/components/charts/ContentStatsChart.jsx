import React from "react";
import PropTypes from "prop-types";
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { RECORD_START_BASES } from "../../constants";
import { useStatsDashboard } from "../../context/StatsDashboardContext";
import { filterByDateRange } from "../../utils";
import { StatsChart } from "../shared_components/StatsChart";

const makeDataPoints = (series, dateRange) => {
  return filterByDateRange(series, dateRange)?.map((point) => [
          point.date,
          point.value,
          point.resourceTypes,
          point.subjectHeadings,
        ]) || [];
}

/**
 * Component that displays record content changes over time.
 *
 * Incoming data is provided by the StatsDashboardContext.stats object.
 * This component uses the new data structure from transformApiData which contains:
 * - stats.recordDeltaDataAdded, stats.recordDeltaDataCreated, stats.recordDeltaDataPublished
 * - stats.recordSnapshotDataAdded, stats.recordSnapshotDataCreated, stats.recordSnapshotDataPublished
 *
 * Each data object contains global data with records, uploaders, and dataVolume metrics.
 *
 * @param {Object} props - The component props.
 * @param {string} props.title - The title of the chart.
 * @param {number} props.height - The height of the chart.
 */
const ContentStatsChart = ({ title = undefined, height = 300, ...otherProps }) => {
  const { dateRange, stats, recordStartBasis } = useStatsDashboard();

  // Helper function to extract data from the new structure
  const extractDataFromDelta = (deltaData, metric) => {
    if (!deltaData || !deltaData.global || !deltaData.global[metric]) {
      return [];
    }

    // Handle both single data point and array of data points
    if (Array.isArray(deltaData.global[metric])) {
      // Single data point format: [date, value]
      const [date, value] = deltaData.global[metric];
      return [{
        date: date,
        value: value,
        resourceTypes: [],
        subjectHeadings: [],
      }];
    } else if (Array.isArray(deltaData.global[metric][0])) {
      // Array of data points format: [[date, value], [date, value], ...]
      return deltaData.global[metric].map(([date, value]) => ({
        date: date,
        value: value,
        resourceTypes: [],
        subjectHeadings: [],
      }));
    }

    return [];
  };

  const displaySeries = {
    [RECORD_START_BASES.ADDED]: [{
      name: i18next.t("Added Records"),
      data: extractDataFromDelta(stats.recordDeltaDataAdded, 'records'),
    },
    {
      name: i18next.t("Active Uploaders"),
      data: extractDataFromDelta(stats.recordDeltaDataAdded, 'uploaders'),
    },
    {
      name: i18next.t("Uploaded Data"),
      data: extractDataFromDelta(stats.recordDeltaDataAdded, 'dataVolume'),
      valueType: "filesize",
    }],
    [RECORD_START_BASES.CREATED]: [{
      name: i18next.t("Created Records"),
      data: extractDataFromDelta(stats.recordDeltaDataCreated, 'records'),
    },
    {
      name: i18next.t("Active Uploaders"),
      data: extractDataFromDelta(stats.recordDeltaDataCreated, 'uploaders'),
    },
    {
      name: i18next.t("Uploaded Data"),
      data: extractDataFromDelta(stats.recordDeltaDataCreated, 'dataVolume'),
      valueType: "filesize",
    }],
    [RECORD_START_BASES.PUBLISHED]: [{
      name: i18next.t("Published Records"),
      data: extractDataFromDelta(stats.recordDeltaDataPublished, 'records'),
    },
    {
      name: i18next.t("Active Uploaders"),
      data: extractDataFromDelta(stats.recordDeltaDataPublished, 'uploaders'),
    },
    {
      name: i18next.t("Uploaded Data"),
      data: extractDataFromDelta(stats.recordDeltaDataPublished, 'dataVolume'),
      valueType: "filesize",
    }],
  }

  // Transform the data points into the format expected by StatsChart
  const transformedData = displaySeries[recordStartBasis].map((series) => {
    series.data = makeDataPoints(series.data, dateRange);
    return series;
  });

  return (
    <StatsChart title={title} data={transformedData} height={height} {...otherProps} />
  );
};

ContentStatsChart.propTypes = {
  title: PropTypes.string,
};

export { ContentStatsChart };
