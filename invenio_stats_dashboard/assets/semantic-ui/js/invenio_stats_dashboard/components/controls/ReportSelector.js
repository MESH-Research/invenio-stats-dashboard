import React, { useState } from "react";
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { Segment, Dropdown, Button, Icon } from "semantic-ui-react";
import PropTypes from "prop-types";

const ReportSelector = () => {
  const [selectedReport, setSelectedReport] = useState(null);
  const handleReportChange = (e, { value }) => {
    setSelectedReport(value);
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
      <Dropdown
        id="stats-dashboard-report-dropdown"
        fluid
        selection
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
      />
      {selectedReport && (
        <Button
          className="stats-dashboard-report-button"
          onClick={handleReportDownload}
        >
          <Icon name="download" />
          {i18next.t("Download report")}
        </Button>
      )}
    </Segment>
  );
};

ReportSelector.propTypes = {};

export { ReportSelector };