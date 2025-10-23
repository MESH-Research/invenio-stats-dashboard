// Part of the Invenio-Stats-Dashboard extension for InvenioRDM
// Copyright (C) 2025 Mesh Research
//
// Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
// it under the terms of the MIT License; see LICENSE file for more details.

import React, { useState, useEffect, useMemo } from "react";
import PropTypes from "prop-types";
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { SingleStatBox } from "../shared_components/SingleStatBox";
import { formatNumber, formatDate } from "../../utils";
import { useStatsDashboard } from "../../context/StatsDashboardContext";
import { extractRecordDeltaValue } from "../../utils/singleStatHelpers";

const SingleStatUploaders = ({
  title = i18next.t("Uploaders"),
  icon = "users",
  compactThreshold = 1_000_000,
}) => {
  const { stats, dateRange, recordStartBasis, isLoading } = useStatsDashboard();
  const [description, setDescription] = useState(null);

  useEffect(() => {
    if (dateRange) {
      setDescription(
        i18next.t("from") +
          " " +
          formatDate(dateRange.start, "day", true, dateRange.end),
      );
    }
  }, [dateRange]);

  // Extract uploaders value using the helper function
  const value = useMemo(() => {
    return extractRecordDeltaValue(
      stats,
      recordStartBasis,
      "uploaders",
      "global",
      dateRange,
    );
  }, [stats, recordStartBasis, dateRange]);

  return (
    <SingleStatBox
      title={title}
      value={formatNumber(value, "compact", { compactThreshold })}
      icon={icon}
      isLoading={isLoading}
      {...(description && { description })}
    />
  );
};

SingleStatUploaders.propTypes = {
  title: PropTypes.string,
  icon: PropTypes.string,
  compactThreshold: PropTypes.number,
  width: PropTypes.number,
};

export { SingleStatUploaders };
