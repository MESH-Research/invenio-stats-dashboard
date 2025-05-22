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

  return (
    <Segment className="stats-dashboard-report-selector rel-mt-1 rel-mb-1 communities-detail-stats-sidebar-segment">
      <label
        id="stats-dashboard-report-label"
        htmlFor="stats-dashboard-report-dropdown"
        className="stats-dashboard-field-label"
      >
        {i18next.t("generate report")}
      </label>
        <Button.Group
          className="stats-dashboard-report-button"
          onClick={handleReportDownload}
          classNames="mt-10"
          icon
          labelPosition="right"
        >
          <Dropdown
            id="stats-dashboard-report-dropdown"
            fluid
            selection
            placeholder={i18next.t("Select")}
            className="stats-dashboard-report-dropdown"
            value={selectedReport}
            onChange={handleReportChange}
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
            onOpen={() => setIsOpen(true)}
            onClose={() => {
            console.log("closing");
            setIsOpen(false);

            // Clear menu styles after a delay
            setTimeout(() => {
                const menuElement = document.querySelector('.stats-dashboard-report-dropdown .menu');
                if (menuElement) {
                menuElement.style = '';
                }
            }, 100);
            }}
            onBlur={() => {
            console.log("blur");

            // Clear menu styles after a delay
            setTimeout(() => {
                const menuElement = document.querySelector('.stats-dashboard-report-dropdown .menu');
                if (menuElement) {
                menuElement.style = '';
                }
            }, 100);
            }}
        />
        <Button>{i18next.t("Download")}</Button>
      </Button.Group>
    </Segment>
  );
};

ReportSelector.propTypes = {
  defaultFormat: PropTypes.string,
};

export { ReportSelector };