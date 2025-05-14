import React from 'react';
import PropTypes from 'prop-types';
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { SingleStatBox } from '../shared_components';
import { formatNumber } from '../../utils';

export const SingleStatDataVolume = ({ value, binary = false }) => {
  return (
    <SingleStatBox
      title={i18next.t("Data volume")}
      value={formatNumber(value, 'filesize', { binary })}
      icon="file"
    />
  );
};

SingleStatDataVolume.propTypes = {
  value: PropTypes.number.isRequired,
  binary: PropTypes.bool,
};
