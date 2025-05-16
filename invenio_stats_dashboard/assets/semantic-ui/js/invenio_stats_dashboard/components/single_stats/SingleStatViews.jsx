import React from 'react';
import PropTypes from 'prop-types';
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { SingleStatBox } from '../shared_components/SingleStatBox';
import { formatNumber } from '../../utils';
import { useStatsDashboard } from '../../context/StatsDashboardContext';

const SingleStatViews = ({ title = i18next.t("Views"), icon = "eye", compactThreshold = 1_000_000 }) => {
  const { stats } = useStatsDashboard();
  const value = stats.views?.reduce((sum, point) => sum + point.value, 0) || 0;

  return (
    <SingleStatBox
      title={title}
      value={formatNumber(value, 'compact', { compactThreshold })}
      icon={icon}
    />
  );
};

SingleStatViews.propTypes = {
  title: PropTypes.string,
  icon: PropTypes.string,
  compactThreshold: PropTypes.number,
};

export { SingleStatViews };
