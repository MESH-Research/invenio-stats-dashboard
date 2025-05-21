import React from 'react';
import PropTypes from 'prop-types';
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { SingleStatBox } from '../shared_components/SingleStatBox';
import { formatNumber, filterByDateRange } from '../../utils';
import { useStatsDashboard } from '../../context/StatsDashboardContext';

const SingleStatDataVolumeCumulative = ({ title = i18next.t("Cumulative Data Volume"), icon = "database", compactThreshold = 1_000_000 }) => {
  const { stats, dateRange, binary_sizes } = useStatsDashboard();

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
    />
  );
};

SingleStatDataVolumeCumulative.propTypes = {
  title: PropTypes.string,
  icon: PropTypes.string,
  compactThreshold: PropTypes.number,
};

export { SingleStatDataVolumeCumulative };