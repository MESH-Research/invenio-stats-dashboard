import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { SingleStatBox } from '../shared_components/SingleStatBox';
import { formatNumber, filterByDateRange, formatDate } from '../../utils';
import { useStatsDashboard } from '../../context/StatsDashboardContext';
import { getSnapshotLatest } from '../../api/dataTransformer';

const SingleStatTrafficCumulative = ({ title = i18next.t("Cumulative Traffic"), icon = "chart line", compactThreshold = 1_000_000 }) => {
  const { stats, binary_sizes, dateRange } = useStatsDashboard();
  const [description, setDescription] = useState(null);

  useEffect(() => {
    if (dateRange) {
      setDescription(i18next.t("as of") + " " + formatDate(dateRange.end, 'day', true));
    }
  }, [dateRange]);

  // Get cumulative traffic data using the centralized helper function
  const value = getSnapshotLatest(
    stats.usageSnapshotData?.global?.dataVolume,
    dateRange,
    filterByDateRange
  );

  return (
    <SingleStatBox
      title={title}
      value={formatNumber(value, 'filesize', { binary: binary_sizes, compactThreshold })}
      icon={icon}
      {...(description && { description })}
    />
  );
};

SingleStatTrafficCumulative.propTypes = {
  title: PropTypes.string,
  icon: PropTypes.string,
  compactThreshold: PropTypes.number,
};

export { SingleStatTrafficCumulative };