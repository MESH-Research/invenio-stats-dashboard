import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { SingleStatBox } from '../shared_components/SingleStatBox';
import { formatNumber, filterByDateRange, formatDate } from '../../utils';
import { useStatsDashboard } from '../../context/StatsDashboardContext';
import { getDeltaTotal } from '../../api/dataTransformer';

const SingleStatDownloads = ({ title = i18next.t("Downloads"), icon = "download", compactThreshold = 1_000_000 }) => {
  const { stats, dateRange } = useStatsDashboard();
  const [description, setDescription] = useState(null);

  useEffect(() => {
    if (dateRange) {
      setDescription(i18next.t("from") + " " + formatDate(dateRange.start, 'day', true, dateRange.end) + " " + i18next.t("to") + " " + formatDate(dateRange.end, 'day', true));
    }
  }, [dateRange]);

  // Get downloads data using the centralized helper function
  const value = getDeltaTotal(
    stats.usageDeltaData?.global?.downloads,
    dateRange,
    filterByDateRange
  );

  return (
    <SingleStatBox
      title={title}
      value={formatNumber(value, 'compact', { compactThreshold })}
      icon={icon}
      {...(description && { description })}
    />
  );
};

SingleStatDownloads.propTypes = {
  title: PropTypes.string,
  icon: PropTypes.string,
  compactThreshold: PropTypes.number,
};

export { SingleStatDownloads };
