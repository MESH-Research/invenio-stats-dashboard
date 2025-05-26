import React, { useEffect, useRef } from "react";
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { Statistic, Icon } from "semantic-ui-react";
import { PropTypes } from "prop-types";

const SingleStatBox = ({ title, value, icon = undefined, description }) => {
  const descriptionId = description ? `${title.toLowerCase().replace(/\s+/g, '-')}-description` : null;
  const valueRef = useRef(null);

  useEffect(() => {
    const adjustFontSize = () => {
      const element = valueRef.current;
      if (!element) return;

      const parent = element.parentElement;
      const parentWidth = parent.offsetWidth;
      const elementWidth = element.offsetWidth;

      if (elementWidth > parentWidth) {
        const scale = parentWidth / elementWidth;
        element.style.transform = `scale(${Math.max(0.7, scale)})`;
      } else {
        element.style.transform = 'scale(1)';
      }
    };

    adjustFontSize();
    window.addEventListener('resize', adjustFontSize);
    return () => window.removeEventListener('resize', adjustFontSize);
  }, [value]);

  return (
    <Statistic
      className="stats-single-stat-container centered rel-mb-2 rel-mt-2"
      role="region"
      aria-label={title}
      aria-describedby={descriptionId}
    >
      <Statistic.Value
        ref={valueRef}
        className="stats-single-stat-value"
        aria-label={`${value} ${title}`}
      >
        {value}
      </Statistic.Value>
      <Statistic.Label className="stats-single-stat-header mt-5">
        {icon && <Icon name={icon} aria-hidden="true" className="mr-10" />}
        {title}
      </Statistic.Label>
      {description && (
        <Statistic.Label
          id={descriptionId}
          className="stats-single-stat-description mt-5"
          aria-label={description}
        >
          {description}
        </Statistic.Label>
      )}
    </Statistic>
  );
};

SingleStatBox.propTypes = {
  title: PropTypes.string.isRequired,
  value: PropTypes.string.isRequired,
  icon: PropTypes.string,
  description: PropTypes.string,
};

export { SingleStatBox };
