import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { SingleStatBox } from '../shared_components/SingleStatBox';
import { formatNumber, filterByDateRange, formatDate } from '../../utils';
import { useStatsDashboard } from '../../context/StatsDashboardContext';

const SingleStatRecordCountCumulative = ({ title = i18next.t("Cumulative Records"), icon = "file alternate", compactThreshold = 1_000_000 }) => {
  const { stats, dateRange } = useStatsDashboard();
  const [description, setDescription] = useState(null);

  useEffect(() => {
    if (dateRange) {
      setDescription(i18next.t("as of") + " " + formatDate(dateRange.end, true));
    }
  }, [dateRange]);

  // Helper function to extract cumulative record count data from the new structure
  const extractCumulativeRecordCountData = () => {
    if (!stats.recordSnapshotDataAdded || !stats.recordSnapshotDataAdded.global || !stats.recordSnapshotDataAdded.global.records) {
      return [];
    }

    // Handle array of data points format: [[date, value], [date, value], ...]
    if (Array.isArray(stats.recordSnapshotDataAdded.global.records) && stats.recordSnapshotDataAdded.global.records.length > 0) {
      return stats.recordSnapshotDataAdded.global.records.map(([date, value]) => ({
        date: date,
        value: value,
        resourceTypes: [],
        subjectHeadings: [],
      }));
    }

    return [];
  };

  const filteredData = filterByDateRange(extractCumulativeRecordCountData(), dateRange);

  // Only sort if the last item's date is not the end of the filter dateRange
  let dataToUse = filteredData;
  if (filteredData.length > 0 && dateRange) {
    const lastItemDate = new Date(filteredData[filteredData.length - 1].date);
    const endDate = new Date(dateRange.end);
    if (lastItemDate.getTime() !== endDate.getTime()) {
      dataToUse = filteredData.sort((a, b) => new Date(a.date) - new Date(b.date));
    }
  }

  const value = dataToUse?.length > 0
    ? dataToUse[dataToUse.length - 1].value
    : 0;

  return (
    <SingleStatBox
      title={title}
      value={formatNumber(value, 'compact', { compactThreshold })}
      icon={icon}
      {...(description && { description })}
    />
  );
};

SingleStatRecordCountCumulative.propTypes = {
  title: PropTypes.string,
  icon: PropTypes.string,
  compactThreshold: PropTypes.number,
};

export { SingleStatRecordCountCumulative };