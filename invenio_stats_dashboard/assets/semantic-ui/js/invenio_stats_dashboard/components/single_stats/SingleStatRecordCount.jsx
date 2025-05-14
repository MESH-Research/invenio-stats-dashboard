import React from 'react';
import PropTypes from 'prop-types';
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { SingleStatBox } from '../shared_components';
import { formatNumber } from '../../utils';

export const SingleStatRecordCount = ({ value, compactThreshold = 1_000_000 }) => {
  return (
    <SingleStatBox
      title={i18next.t("Records")}
      value={formatNumber(value, 'compact', { compactThreshold })}
      icon="file alternate"
    />
  );
};

SingleStatRecordCount.propTypes = {
  value: PropTypes.number.isRequired,
  compactThreshold: PropTypes.number,
};
