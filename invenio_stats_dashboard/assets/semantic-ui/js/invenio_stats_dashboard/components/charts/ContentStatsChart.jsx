import React from "react";
import PropTypes from "prop-types";
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { RECORD_START_BASES } from "../../constants";
import { useStatsDashboard } from "../../context/StatsDashboardContext";
import { StatsChart } from "../shared_components/StatsChart";


/**
 * Component that displays record content changes over time.
 *
 * Incoming data is provided by the StatsDashboardContext.stats object.
 * This component uses the new data structure from transformApiData which contains:
 * - stats.recordDeltaDataAdded, stats.recordDeltaDataCreated, stats.recordDeltaDataPublished
 *
 * Each data object is a RecordDeltaData object, which contains sets of data series--
 * for global metrics and for a variety of categorized subcount metrics. Each set
 * contains a set of data series, including series for records, uploaders,
 * and dataVolume.
 *
 * @param {Object} props - The component props.
 * @param {string} props.title - The title of the chart.
 * @param {number} props.height - The height of the chart.
 */
const ContentStatsChart = ({ title = undefined, height = 300, ...otherProps }) => {
  const { stats, recordStartBasis } = useStatsDashboard();

  const seriesCategoryMap = {
    [RECORD_START_BASES.ADDED]: stats.recordDeltaDataAdded,
    [RECORD_START_BASES.CREATED]: stats.recordDeltaDataCreated,
    [RECORD_START_BASES.PUBLISHED]: stats.recordDeltaDataPublished,
  };

  const seriesSelectorOptions = {
    [RECORD_START_BASES.ADDED]: [
        { value: 'records', text: i18next.t("Added Records") },
        { value: 'uploaders', text: i18next.t("Active Uploaders") },
        { value: 'dataVolume', text: i18next.t("Uploaded Data"), valueType: 'filesize' }
    ],
    [RECORD_START_BASES.CREATED]: [
        { value: 'records', text: i18next.t("Created Records") },
        { value: 'uploaders', text: i18next.t("Active Uploaders") },
        { value: 'dataVolume', text: i18next.t("Uploaded Data"), valueType: 'filesize' }
    ],
    [RECORD_START_BASES.PUBLISHED]: [
        { value: 'records', text: i18next.t("Published Records") },
        { value: 'uploaders', text: i18next.t("Active Uploaders") },
        { value: 'dataVolume', text: i18next.t("Uploaded Data"), valueType: 'filesize' }
    ],
  };

  const data = seriesCategoryMap[recordStartBasis];
  const options = seriesSelectorOptions[recordStartBasis];

  return (
    <StatsChart
      title={title}
      data={data}
      seriesSelectorOptions={options}
      height={height}
      {...otherProps} />
  );
};

ContentStatsChart.propTypes = {
  title: PropTypes.string,
  height: PropTypes.number,
};

export { ContentStatsChart };
