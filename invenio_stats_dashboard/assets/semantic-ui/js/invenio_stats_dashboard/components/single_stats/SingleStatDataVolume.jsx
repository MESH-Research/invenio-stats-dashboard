import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { SingleStatBox } from '../shared_components/SingleStatBox';
import { formatNumber, filterByDateRange, formatDate } from '../../utils';
import { useStatsDashboard } from '../../context/StatsDashboardContext';

const SingleStatDataVolume = ({ title = i18next.t("Data Volume"), icon = "database", compactThreshold = 1_000_000 }) => {
  const { stats, dateRange } = useStatsDashboard();
  const [description, setDescription] = useState(null);

  useEffect(() => {
    if (dateRange) {
      setDescription(i18next.t("from") + " " + formatDate(dateRange.start, true, true, dateRange.end) + " " + i18next.t("to") + " " + formatDate(dateRange.end, true));
    }
  }, [dateRange]);

  // Helper function to extract data volume from the new structure
  const extractDataVolumeData = () => {
    if (!stats.recordDeltaDataAdded || !stats.recordDeltaDataAdded.global || !stats.recordDeltaDataAdded.global.dataVolume) {
      return [];
    }

    const [date, value] = stats.recordDeltaDataAdded.global.dataVolume;
    return [{
      date: date,
      value: value,
      resourceTypes: [],
      subjectHeadings: [],
    }];
  };

  const filteredData = filterByDateRange(extractDataVolumeData(), dateRange);
  const value = filteredData?.reduce((sum, point) => sum + point.value, 0) || 0;

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
