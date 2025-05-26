import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { SingleStatBox } from '../shared_components/SingleStatBox';
import { formatNumber, filterByDateRange, formatDate } from '../../utils';
import { useStatsDashboard } from '../../context/StatsDashboardContext';

const SingleStatDataVolumeCumulative = ({ title = i18next.t("Cumulative Data Volume"), icon = "database", compactThreshold = 1_000_000 }) => {
  const { stats, dateRange, binary_sizes } = useStatsDashboard();
  const [description, setDescription] = useState(null);

  useEffect(() => {
    console.log("dateRange in SingleStatDataVolumeCumulative", dateRange);
    if (dateRange) {
      setDescription(i18next.t("as of") + " " + formatDate(dateRange.end, true));
    }
  }, [dateRange]);

  // Get the last value in the date range
  const filteredData = filterByDateRange(stats.dataVolume, dateRange);
  const value = filteredData?.length > 0
    ? filteredData[filteredData.length - 1].value
    : 0;

  return (
    <SingleStatBox
      title={title}
      value={formatNumber(value, 'filesize', { binary: binary_sizes, compactThreshold })}
      icon={icon}
      {...(description && { description })}
    />
  );
};

SingleStatDataVolumeCumulative.propTypes = {
  title: PropTypes.string,
  icon: PropTypes.string,
  compactThreshold: PropTypes.number,
};

export { SingleStatDataVolumeCumulative };