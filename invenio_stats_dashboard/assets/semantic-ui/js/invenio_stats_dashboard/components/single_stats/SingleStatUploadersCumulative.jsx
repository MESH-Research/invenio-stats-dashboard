import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { SingleStatBox } from '../shared_components/SingleStatBox';
import { formatNumber, formatDate } from '../../utils';
import { useStatsDashboard } from '../../context/StatsDashboardContext';
import { extractRecordSnapshotValue } from '../../utils/singleStatHelpers';

const SingleStatUploadersCumulative = ({ title = i18next.t("Cumulative Uploaders"), icon = "users", compactThreshold = 1_000_000 }) => {
  const { stats, dateRange, recordStartBasis } = useStatsDashboard();
  const [description, setDescription] = useState(null);

  useEffect(() => {
    if (dateRange) {
      setDescription(i18next.t("as of") + " " + formatDate(dateRange.end, 'day', true));
    }
  }, [dateRange]);

  // Extract cumulative uploaders value using the helper function
  const value = extractRecordSnapshotValue(
    stats,
    recordStartBasis,
    'uploaders',
    'global',
    dateRange
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

SingleStatUploadersCumulative.propTypes = {
  title: PropTypes.string,
  icon: PropTypes.string,
  compactThreshold: PropTypes.number,
};

export { SingleStatUploadersCumulative };