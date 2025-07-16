import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { SingleStatBox } from '../shared_components/SingleStatBox';
import { formatNumber, filterByDateRange, formatDate } from '../../utils';
import { useStatsDashboard } from '../../context/StatsDashboardContext';

const SingleStatTraffic = ({ title = i18next.t("Traffic"), icon = "chart line", compactThreshold = 1_000_000 }) => {
  const { stats, binary_sizes, dateRange } = useStatsDashboard();
  const [description, setDescription] = useState(null);

  useEffect(() => {
    if (dateRange) {
      setDescription(i18next.t("from") + " " + formatDate(dateRange.start, true, true, dateRange.end) + " " + i18next.t("to") + " " + formatDate(dateRange.end, true));
    }
  }, [dateRange]);

  // Helper function to extract traffic data from the new structure
  const extractTrafficData = () => {
    if (!stats.usageDeltaData || !stats.usageDeltaData.global || !stats.usageDeltaData.global.dataVolume) {
      return [];
    }

    const [date, value] = stats.usageDeltaData.global.dataVolume;
    return [{
      date: date,
      value: value,
      resourceTypes: [],
      subjectHeadings: [],
    }];
  };

  const filteredData = filterByDateRange(extractTrafficData(), dateRange);
  const value = filteredData?.reduce((sum, point) => sum + point.value, 0) || 0;

  return (
    <SingleStatBox
      title={title}
      value={formatNumber(value, 'filesize', { binary: binary_sizes, compactThreshold })}
      icon={icon}
      {...(description && { description })}
    />
  );
};

SingleStatTraffic.propTypes = {
  title: PropTypes.string,
  icon: PropTypes.string,
  compactThreshold: PropTypes.number,
};

export { SingleStatTraffic };
