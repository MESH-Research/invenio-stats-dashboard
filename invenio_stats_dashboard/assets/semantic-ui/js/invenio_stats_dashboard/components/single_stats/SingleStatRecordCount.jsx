import React from 'react';
import PropTypes from 'prop-types';
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { SingleStatBox } from '../shared_components/SingleStatBox';
import { formatNumber, filterByDateRange } from '../../utils';
import { useStatsDashboard } from '../../context/StatsDashboardContext';

const SingleStatRecordCount = ({ title = i18next.t("Total Records"), icon = "file alternate", compactThreshold = 1_000_000 }) => {
  const { stats, dateRange } = useStatsDashboard();
  const filteredData = filterByDateRange(stats.recordCount, dateRange);
  const value = filteredData?.reduce((sum, point) => sum + point.value, 0) || 0;

  return (
    <SingleStatBox
      title={title}
      value={formatNumber(value, 'compact', { compactThreshold })}
      icon={icon}
    />
  );
};

SingleStatRecordCount.propTypes = {
  title: PropTypes.string,
  icon: PropTypes.string,
  compactThreshold: PropTypes.number,
};

export { SingleStatRecordCount };
