import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { SingleStatBox } from '../shared_components/SingleStatBox';
import { formatNumber, formatDate } from '../../utils';
import { useStatsDashboard } from '../../context/StatsDashboardContext';
import { extractRecordDeltaValue } from '../../utils/singleStatHelpers';

const SingleStatRecordCount = ({ title = i18next.t("Records"), icon = "file", compactThreshold = 1_000_000 }) => {
  const { stats, dateRange, recordStartBasis, isLoading } = useStatsDashboard();
  const [description, setDescription] = useState(null);

  useEffect(() => {
    if (dateRange) {
      setDescription(i18next.t("from") + " " + formatDate(dateRange.start, 'day', true, dateRange.end) + " " + i18next.t("to") + " " + formatDate(dateRange.end, 'day', true));
    }
  }, [dateRange]);

  // Extract record count value using the new helper function
  const value = extractRecordDeltaValue(
    stats,
    recordStartBasis,
    'records',
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

SingleStatRecordCount.propTypes = {
  title: PropTypes.string,
  icon: PropTypes.string,
  compactThreshold: PropTypes.number,
};

export { SingleStatRecordCount };
