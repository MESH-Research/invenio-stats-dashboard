import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { SingleStatBox } from '../shared_components/SingleStatBox';
import { formatNumber, filterByDateRange, formatDate } from '../../utils';
import { useStatsDashboard } from '../../context/StatsDashboardContext';

const SingleStatViews = ({ title = i18next.t("Views"), icon = "eye", compactThreshold = 1_000_000 }) => {
  const { stats, dateRange } = useStatsDashboard();
  const [description, setDescription] = useState(null);

  useEffect(() => {
    if (dateRange) {
      setDescription(i18next.t("from") + " " + formatDate(dateRange.start, true, true, dateRange.end) + " " + i18next.t("to") + " " + formatDate(dateRange.end, true));
    }
  }, [dateRange]);

  const filteredData = filterByDateRange(stats.views, dateRange);
  const value = filteredData?.reduce((sum, point) => sum + point.value, 0) || 0;

  return (
    <SingleStatBox
      title={title}
      value={formatNumber(value, 'compact', { compactThreshold })}
      icon={icon}
      {...(description && { description })}
    />
  );
};

SingleStatViews.propTypes = {
  title: PropTypes.string,
  icon: PropTypes.string,
  compactThreshold: PropTypes.number,
};

export { SingleStatViews };
