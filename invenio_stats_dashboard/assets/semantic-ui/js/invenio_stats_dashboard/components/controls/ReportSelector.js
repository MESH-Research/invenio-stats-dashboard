import React, { useState } from "react";
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { Segment, Dropdown, Button, Icon } from "semantic-ui-react";
import PropTypes from "prop-types";

const ReportSelector = ({ defaultFormat }) => {
  const [selectedReport, setSelectedReport] = useState(defaultFormat);
  const [isOpen, setIsOpen] = useState(false);

  const handleReportChange = (e, { value }) => {
    setSelectedReport(value);
    setIsOpen(false);
  };

  const handleReportDownload = () => {
    console.log("Download report");
  };

  const handleMenuOpen = () => {
    setIsOpen(true);
    const menuElement = document.querySelector('.stats-dashboard-report-dropdown .menu');
    if (menuElement) {
      menuElement.style.position = 'absolute';
      menuElement.style.zIndex = '1000';
    }
  };

  const handleMenuClose = () => {
    setIsOpen(false);
    setTimeout(() => {
      const menuElement = document.querySelector('.stats-dashboard-report-dropdown .menu');
      const selectorElement = document.querySelector('.stats-dashboard-report-dropdown');
      if (menuElement) {
        menuElement.style = '';
      }
      if (selectorElement) {
        selectorElement.style = '';
      }
    }, 100);
  };

  return (
    <Segment className="stats-dashboard-report-selector rel-mt-1 rel-mb-1 communities-detail-stats-sidebar-segment">
      <label
        id="stats-dashboard-report-label"
        htmlFor="stats-dashboard-report-dropdown"
        className="stats-dashboard-field-label"
      >
        {i18next.t("generate report")}
      </label>
      <Dropdown
        id="stats-dashboard-report-dropdown"
        fluid
        selection
        placeholder={i18next.t("Select")}
        className="stats-dashboard-report-dropdown"
        value={selectedReport}
        onChange={handleReportChange}
        closeOnBlur={true}
        closeOnChange={false}
        selectOnBlur={true}
        options={[
          {
            key: "csv",
            text: "CSV",
            value: "csv",
          },
          {
            key: "excel",
            text: "Excel",
            value: "excel",
          },
          {
            key: "pdf",
            text: "PDF",
            value: "pdf",
          },
          {
            key: "json",
            text: "JSON",
            value: "json",
          },
          {
            key: "xml",
            text: "XML",
            value: "xml",
          },
        ]}
        open={isOpen}
        onOpen={handleMenuOpen}
        onClose={handleMenuClose}
        onBlur={handleMenuClose}
      />
      {selectedReport && (
        <Button
          className="stats-dashboard-report-button"
          onClick={handleReportDownload}
          classNames="mt-10"
          icon
          labelPosition="right"
        >
          {i18next.t("Download")}
        </Button>
      )}
    </Segment>
  );
};

ReportSelector.propTypes = {
  defaultFormat: PropTypes.string,
};

export { ReportSelector };
