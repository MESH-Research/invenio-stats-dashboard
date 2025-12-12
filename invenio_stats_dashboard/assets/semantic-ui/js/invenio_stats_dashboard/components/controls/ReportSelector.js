import React, { useState } from "react";
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { Segment, Dropdown, Button, Icon, Loader, Popup } from "semantic-ui-react";
import PropTypes from "prop-types";
import {
  downloadStatsSeriesWithFilename,
  SERIALIZATION_FORMATS,
} from "../../api/api";
import { DASHBOARD_TYPES } from "../../constants";
import { useStatsDashboard } from "../../context/StatsDashboardContext";
import { packageStatsAsCompressedJson } from "../../utils";

const ReportSelector = ({ defaultFormat }) => {
  const [selectedReport, setSelectedReport] = useState(defaultFormat);
  const [isOpen, setIsOpen] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);

  // Get current dashboard context
  const { community, dashboardType, dateRange, recordStartBasis, stats } =
    useStatsDashboard();

  const handleReportChange = (e, { value }) => {
    setSelectedReport(value);
  };

  const handleReportDownload = async () => {
    if (!selectedReport) return;

    setIsDownloading(true);

    try {
      // Format dates for filename and/or API requests
      const startDate = dateRange?.start
        ? dateRange.start.toISOString().split("T")[0]
        : null;
      const endDate = dateRange?.end
        ? dateRange.end.toISOString().split("T")[0]
        : null;

      // Handle JSON downloads using cached data
      if (selectedReport === "json") {
        // Check if we have stats data available
        if (!stats || stats.length === 0) {
          throw new Error("No statistics data available for download. Please ensure the dashboard has loaded data.");
        }

        await packageStatsAsCompressedJson(
          stats,
          community?.id || "global",
          dashboardType || DASHBOARD_TYPES.GLOBAL,
          recordStartBasis || "added",
          startDate,
          endDate
        );

        console.log("Successfully downloaded JSON report from cached data as tar.gz archive");
        return;
      }

      // Handle other formats using API requests
      const formatMapping = {
        csv: SERIALIZATION_FORMATS.CSV,
        excel: SERIALIZATION_FORMATS.EXCEL,
        xml: SERIALIZATION_FORMATS.XML,
      };

      const format = formatMapping[selectedReport];
      if (!format) {
        throw new Error(`Unsupported format: ${selectedReport}`);
      }

      await downloadStatsSeriesWithFilename({
        communityId: community?.id || "global",
        dashboardType: dashboardType || DASHBOARD_TYPES.GLOBAL,
        format,
        startDate,
        endDate,
        dateBasis: recordStartBasis || "added",
      });

      console.log(`Successfully downloaded ${selectedReport} report`);
    } catch (error) {
      console.error("Error downloading report:", error);
      // You could add a toast notification here
    } finally {
      setIsDownloading(false);
    }
  };

  const handleMenuOpen = () => {
    setIsOpen(true);
    const menuElement = document.querySelector(
      ".stats-dashboard-report-dropdown .menu",
    );
    if (menuElement) {
      menuElement.style.position = "absolute";
      menuElement.style.zIndex = "1000";
    }
  };

  const handleMenuClose = () => {
    setIsOpen(false);
    setTimeout(() => {
      const menuElement = document.querySelector(
        ".stats-dashboard-report-dropdown .menu",
      );
      const selectorElement = document.querySelector(
        ".stats-dashboard-report-dropdown",
      );
      if (menuElement) {
        menuElement.style = "";
      }
      if (selectorElement) {
        selectorElement.style = "";
      }
    }, 100);
  };

  const handleKeyDown = (e) => {
    if (isOpen && e.key === 'Enter') {
      e.preventDefault();
      setIsOpen(false);
    }
  };

  return (
    <Segment className="stats-dashboard-report-selector rel-mt-1 rel-mb-1 communities-detail-stats-sidebar-segment">
      <label
        id="stats-dashboard-report-label"
        htmlFor="stats-dashboard-report-dropdown"
        className="stats-dashboard-field-label"
      >
        {i18next.t("generate report")}
        <Popup
          content={i18next.t("Includes complete time-series data for the currently selected time period.")}
          trigger={<Icon name="info circle" style={{ marginLeft: '0.5rem', cursor: 'help' }} />}
          position="top center"
          size="small"
        />
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
        onKeyDown={handleKeyDown}
      />
      {selectedReport && (
        <div>
          <Button
            className="stats-dashboard-report-button mt-10"
            content={i18next.t("Download")}
            onClick={handleReportDownload}
            classNames="mt-10"
            icon={"download"}
            labelPosition="right"
            disabled={isDownloading}
          />
          {isDownloading && (
            <>
            <Loader active inline="centered" size="small" className="mt-10" />
            <div className="stats-dashboard-download-message mt-5 centered">
              {i18next.t("Preparing your download. This may take a minute.")}
            </div>
            </>
          )}
        </div>
      )}
    </Segment>
  );
};

ReportSelector.propTypes = {
  defaultFormat: PropTypes.string,
};

export { ReportSelector };
