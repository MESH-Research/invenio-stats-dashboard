import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { SingleStatBox } from '../shared_components/SingleStatBox';
import { formatNumber, formatDate } from '../../utils';
import { useStatsDashboard } from '../../context/StatsDashboardContext';
import { extractUsageSnapshotValue } from '../../utils/singleStatHelpers';

const SingleStatDownloadsCumulative = ({ title = i18next.t("Cumulative Downloads"), icon = "download", compactThreshold = 1_000_000 }) => {
  const { stats, dateRange, isLoading } = useStatsDashboard();
  const [description, setDescription] = useState(null);

  useEffect(() => {
    if (dateRange) {
      setDescription(i18next.t("as of") + " " + formatDate(dateRange.end, 'day', true));
    }
  }, [dateRange]);

  // Extract cumulative downloads value using the helper function
  const value = extractUsageSnapshotValue(
    stats,
    'downloads',
    'global',
    dateRange
  );

  return (
    <SingleStatBox
      title={title}
      value={formatNumber(value, 'compact', { compactThreshold })}
      icon={icon}
      isLoading={isLoading}
      {...(description && { description })}
    />
  );
};

SingleStatDownloadsCumulative.propTypes = {
  title: PropTypes.string,
  icon: PropTypes.string,
  compactThreshold: PropTypes.number,
};

export { SingleStatDownloadsCumulative };