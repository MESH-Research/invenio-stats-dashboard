import React from 'react';
import PropTypes from 'prop-types';
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { SingleStatBox } from '../shared_components/SingleStatBox';
import { formatNumber, filterByDateRange } from '../../utils';
import { useStatsDashboard } from '../../context/StatsDashboardContext';

const SingleStatRecordCountCumulative = ({ title = i18next.t("Cumulative Records"), icon = "file alternate", compactThreshold = 1_000_000 }) => {
  const { stats, dateRange } = useStatsDashboard();
  const filteredData = filterByDateRange(stats.recordCount, dateRange);

  // Get the last value in the date range
  const value = filteredData?.length > 0
    ? filteredData[filteredData.length - 1].value
    : 0;

  return (
    <SingleStatBox
      title={title}
      value={formatNumber(value, 'compact', { compactThreshold })}
      icon={icon}
    />
  );
};

SingleStatRecordCountCumulative.propTypes = {
  title: PropTypes.string,
  icon: PropTypes.string,
  compactThreshold: PropTypes.number,
};

export { SingleStatRecordCountCumulative };