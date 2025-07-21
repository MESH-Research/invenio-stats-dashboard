import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { SingleStatBox } from '../shared_components/SingleStatBox';
import { formatNumber, filterByDateRange, formatDate } from '../../utils';
import { useStatsDashboard } from '../../context/StatsDashboardContext';
import { getSnapshotLatest } from '../../api/dataTransformer';

const SingleStatViewsCumulative = ({ title = i18next.t("Cumulative Views"), icon = "eye", compactThreshold = 1_000_000 }) => {
  const { stats, dateRange } = useStatsDashboard();
  const [description, setDescription] = useState(null);

  useEffect(() => {
    if (dateRange) {
      setDescription(i18next.t("as of") + " " + formatDate(dateRange.end, 'day', true));
    }
  }, [dateRange]);

  // Get cumulative views data using the centralized helper function
  const value = getSnapshotLatest(
    stats.usageSnapshotData?.global?.views,
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

SingleStatViewsCumulative.propTypes = {
  title: PropTypes.string,
  icon: PropTypes.string,
  compactThreshold: PropTypes.number,
};

export { SingleStatViewsCumulative };