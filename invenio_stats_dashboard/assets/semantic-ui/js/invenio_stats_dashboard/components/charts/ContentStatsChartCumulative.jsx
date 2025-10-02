import React, { useMemo } from 'react';
import PropTypes from 'prop-types';
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { StatsChart } from '../shared_components/StatsChart';
import { useStatsDashboard } from '../../context/StatsDashboardContext';
import { RECORD_START_BASES } from '../../constants';

/**
 * Cumulative content stats chart.
 *
 * This chart shows the cumulative growth of the community or whole repository
 * over time. It renders a bar chart with cumulative statistics for records,
 * data volume, and uploaders. The chart is interactive and allows users to
 * select which metric to display. It also allows users to view the data
 * subdivided based on each record's metadata properties such as access
 * status, creator's affiliation, file type, and visitor country.
 *
 * @param {Object} props - The component props.
 * @param {string} [props.title] - The chart title.
 * @param {number} [props.height] - The chart height.
 * @param {string} [props.chartType] - The chart type (bar or line). Defaults to "bar".
 */
const ContentStatsChartCumulative = ({ title = undefined, height = 300, chartType = "bar", ...otherProps }) => {
  const { stats, recordStartBasis } = useStatsDashboard();

  const yearlyData = useMemo(() => {
    if (!stats || !Array.isArray(stats)) return null;

    return stats.map(yearlyStats => {
      const seriesCategoryMap = {
        [RECORD_START_BASES.ADDED]: yearlyStats?.recordSnapshotDataAdded,
        [RECORD_START_BASES.CREATED]: yearlyStats?.recordSnapshotDataCreated,
        [RECORD_START_BASES.PUBLISHED]: yearlyStats?.recordSnapshotDataPublished,
      };
      return seriesCategoryMap[recordStartBasis];
    }).filter(Boolean); // Remove null/undefined entries
  }, [stats, recordStartBasis]);

  const seriesSelectorOptions = {
    [RECORD_START_BASES.ADDED]: [
        { value: 'records', text: i18next.t("Records") },
        { value: 'fileCount', text: i18next.t("Files") },
        { value: 'dataVolume', text: i18next.t("Data Volume"), valueType: 'filesize' },
        { value: 'uploaders', text: i18next.t("Uploaders") }
    ],
    [RECORD_START_BASES.CREATED]: [
        { value: 'records', text: i18next.t("Records") },
        { value: 'fileCount', text: i18next.t("Files") },
        { value: 'dataVolume', text: i18next.t("Data Volume"), valueType: 'filesize' },
        { value: 'uploaders', text: i18next.t("Uploaders") }
    ],
    [RECORD_START_BASES.PUBLISHED]: [
        { value: 'records', text: i18next.t("Records") },
        { value: 'fileCount', text: i18next.t("Files") },
        { value: 'dataVolume', text: i18next.t("Data Volume"), valueType: 'filesize' },
        { value: 'uploaders', text: i18next.t("Uploaders") }
    ],
  };

  const data = yearlyData;
  const options = seriesSelectorOptions[recordStartBasis];

  return (
    <StatsChart
      title={title || i18next.t('Cumulative Growth')}
      data={data}
      seriesSelectorOptions={options}
      height={height}
      chartType={chartType}
      {...otherProps}
    />
  );
};

ContentStatsChartCumulative.propTypes = {
  title: PropTypes.string,
  height: PropTypes.number,
};

export { ContentStatsChartCumulative };