// Part of the Invenio-Stats-Dashboard extension for InvenioRDM
// Copyright (C) 2025 Mesh Research
//
// Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
// it under the terms of the MIT License; see LICENSE file for more details.

import React, { useState, useEffect, useMemo } from 'react';
import PropTypes from 'prop-types';
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { SingleStatBox } from '../shared_components/SingleStatBox';
import { formatNumber, formatDate } from '../../utils';
import { useStatsDashboard } from '../../context/StatsDashboardContext';
import { extractRecordSnapshotValue } from '../../utils/singleStatHelpers';

const SingleStatDataVolumeCumulative = ({ title = i18next.t("Cumulative Data Volume"), icon = "database", compactThreshold = 1_000_000 }) => {
  const { stats, dateRange, recordStartBasis, binary_sizes, isLoading } = useStatsDashboard();
  const [description, setDescription] = useState(null);

  useEffect(() => {
    if (dateRange) {
      setDescription(i18next.t("as of") + " " + formatDate(dateRange.end, 'day', true));
    }
  }, [dateRange]);

  // Extract cumulative data volume value using the helper function
  const value = useMemo(() => {
    return extractRecordSnapshotValue(
      stats,
      recordStartBasis,
      'dataVolume',
      'global',
      dateRange
    );
  }, [stats, recordStartBasis, dateRange]);

  return (
    <SingleStatBox
      title={title}
      value={formatNumber(value, 'filesize', { binary: binary_sizes, compactThreshold })}
      icon={icon}
      isLoading={isLoading}
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