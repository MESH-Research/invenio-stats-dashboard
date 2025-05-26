import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { SingleStatBox } from '../shared_components/SingleStatBox';
import { formatNumber, filterByDateRange, formatDate } from '../../utils';
import { useStatsDashboard } from '../../context/StatsDashboardContext';

const SingleStatRecordCountCumulative = ({ title = i18next.t("Cumulative Records"), icon = "file alternate", compactThreshold = 1_000_000 }) => {
  const { stats, dateRange } = useStatsDashboard();
  const [description, setDescription] = useState(null);

  useEffect(() => {
    if (dateRange) {
      setDescription(i18next.t("as of") + " " + formatDate(dateRange.end, true));
    }
  }, [dateRange]);

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
      {...(description && { description })}
    />
  );
};

SingleStatRecordCountCumulative.propTypes = {
  title: PropTypes.string,
  icon: PropTypes.string,
  compactThreshold: PropTypes.number,
};

export { SingleStatRecordCountCumulative };