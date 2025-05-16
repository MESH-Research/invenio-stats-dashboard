import React from 'react';
import PropTypes from 'prop-types';
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { SingleStatBox } from '../shared_components/SingleStatBox';
import { formatNumber } from '../../utils';
import { useStatsDashboard } from '../../context/StatsDashboardContext';

const SingleStatDataVolume = ({ title = i18next.t("Data Volume"), icon = "database", compactThreshold = 1_000_000 }) => {
  const { stats } = useStatsDashboard();
  const value = stats.dataVolume?.reduce((sum, point) => sum + point.value, 0) || 0;
  const binary = stats.use_binary_filesize;

  return (
    <SingleStatBox
      title={title}
      value={formatNumber(value, 'filesize', { binary })}
      icon={icon}
    />
  );
};

SingleStatDataVolume.propTypes = {
  title: PropTypes.string,
  icon: PropTypes.string,
  compactThreshold: PropTypes.number,
};

export { SingleStatDataVolume };
