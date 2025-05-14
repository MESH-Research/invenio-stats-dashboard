import React from 'react';
import PropTypes from 'prop-types';
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { SingleStatBox } from '../shared_components';
import { formatNumber } from '../../utils';

export const SingleStatUploaders = ({ value, compactThreshold = 1_000_000 }) => {
  return (
    <SingleStatBox
      title={i18next.t("Uploaders")}
      value={formatNumber(value, 'compact', { compactThreshold })}
      icon="upload"
    />
  );
};

SingleStatUploaders.propTypes = {
  value: PropTypes.number.isRequired,
  compactThreshold: PropTypes.number,
};
