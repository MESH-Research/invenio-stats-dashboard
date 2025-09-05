import React, { useEffect, useRef } from "react";
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { Statistic, Icon, Loader, Message } from "semantic-ui-react";
import { PropTypes } from "prop-types";

const SingleStatBox = ({ title, value, icon = undefined, description, isLoading = false, hasData = true }) => {
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

  // If no data and not loading, show a no-data message instead of the statistic
  if (!isLoading && !hasData) {
    return (
      <div className="stats-single-stat-container centered rel-mb-2 rel-mt-2">
        <Message info size="small">
          <Message.Header>{i18next.t("No Data")}</Message.Header>
          <p>{i18next.t("No data available")}</p>
        </Message>
      </div>
    );
  }

  return (
    <div
      className="stats-single-stat-container centered rel-mb-2 rel-mt-2"
      role="region"
      aria-label={title}
      aria-describedby={descriptionId}
    >
      {isLoading ? (
        <div className="stats-single-stat-loading-container">
          <Loader active size="large" />
        </div>
      ) : (
        <Statistic>
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
      )}
    </div>
  );
};

SingleStatBox.propTypes = {
  title: PropTypes.string.isRequired,
  value: PropTypes.string.isRequired,
  icon: PropTypes.string,
  description: PropTypes.string,
  isLoading: PropTypes.bool,
  hasData: PropTypes.bool,
};

export { SingleStatBox };
