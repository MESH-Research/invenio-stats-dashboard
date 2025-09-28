import React, { useState } from "react";
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { Segment, Dropdown, Button, Icon } from "semantic-ui-react";
import PropTypes from "prop-types";
import { downloadStatsSeriesWithFilename, SERIALIZATION_FORMATS } from "../../api/api";
import { DASHBOARD_TYPES } from "../../constants";
import { useStatsDashboard } from "../../context/StatsDashboardContext";

const ReportSelector = ({ defaultFormat }) => {
  const [selectedReport, setSelectedReport] = useState(defaultFormat);
  const [isOpen, setIsOpen] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);

  // Get current dashboard context
  const { communityId, dashboardType, dateRange, dateBasis } = useStatsDashboard();

  const handleReportChange = (e, { value }) => {
    setSelectedReport(value);
    setIsOpen(false);
  };

  const handleReportDownload = async () => {
    if (!selectedReport) return;

    setIsDownloading(true);

    try {
      // Map UI format names to API format constants
      const formatMapping = {
        'csv': SERIALIZATION_FORMATS.CSV,
        'excel': SERIALIZATION_FORMATS.EXCEL,
        'json': SERIALIZATION_FORMATS.JSON_BROTLI,
        'xml': SERIALIZATION_FORMATS.XML,
      };

      const format = formatMapping[selectedReport];
      if (!format) {
        throw new Error(`Unsupported format: ${selectedReport}`);
      }

      // Format dates for API
      const startDate = dateRange?.start ? dateRange.start.toISOString().split('T')[0] : null;
      const endDate = dateRange?.end ? dateRange.end.toISOString().split('T')[0] : null;

      await downloadStatsSeriesWithFilename({
        communityId: communityId || 'global',
        dashboardType: dashboardType || DASHBOARD_TYPES.GLOBAL,
        format,
        startDate,
        endDate,
        dateBasis: dateBasis || 'added',
      });

      console.log(`Successfully downloaded ${selectedReport} report`);
    } catch (error) {
      console.error('Error downloading report:', error);
      // You could add a toast notification here
    } finally {
      setIsDownloading(false);
    }
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
            text: "CSV (Compressed)",
            value: "csv",
          },
          {
            key: "excel",
            text: "Excel (Compressed)",
            value: "excel",
          },
          {
            key: "json",
            text: "JSON (Compressed)",
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
          loading={isDownloading}
          disabled={isDownloading}
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
