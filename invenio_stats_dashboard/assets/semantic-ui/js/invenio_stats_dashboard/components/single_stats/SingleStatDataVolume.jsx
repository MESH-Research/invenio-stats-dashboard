import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { SingleStatBox } from '../shared_components/SingleStatBox';
import { formatNumber, filterByDateRange, formatDate } from '../../utils';
import { useStatsDashboard } from '../../context/StatsDashboardContext';
import { getDeltaTotal } from '../../api/dataTransformer';

const SingleStatDataVolume = ({ title = i18next.t("Data Volume"), icon = "database", compactThreshold = 1_000_000 }) => {
  const { stats, dateRange } = useStatsDashboard();
  const [description, setDescription] = useState(null);

  useEffect(() => {
    if (dateRange) {
      setDescription(i18next.t("from") + " " + formatDate(dateRange.start, 'day', true, dateRange.end) + " " + i18next.t("to") + " " + formatDate(dateRange.end, 'day', true));
    }
  }, [dateRange]);

  // Get data volume using the centralized helper function
  const value = getDeltaTotal(
    stats.recordDeltaDataAdded?.global?.dataVolume,
    dateRange,
    filterByDateRange
  );

  return (
    <SingleStatBox
      title={title}
      value={formatNumber(value, 'filesize', { compactThreshold })}
      icon={icon}
      {...(description && { description })}
    />
  );
};

SingleStatDataVolume.propTypes = {
  title: PropTypes.string,
  icon: PropTypes.string,
  compactThreshold: PropTypes.number,
};

export { SingleStatDataVolume };
