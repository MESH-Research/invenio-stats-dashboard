import React, { useState } from "react";
import PropTypes from "prop-types";
import { Container } from "semantic-ui-react";
import { i18next } from "@translations/i18next";
import { formatNumber } from "../utils/numbers";

const StatsPopup = ({ number, compactThreshold }) => {
  const localizedNumber = formatNumber(number, 'default');
  const compactNumber = formatNumber(number, 'compact', { compactThreshold });
  return localizedNumber !== compactNumber ? (
    <div>
      <span
        tabindex="0"
        role="button"
        className="popup-trigger compact-number"
        aria-expanded="false"
        aria-label={ i18next.t("See the full number") }
        data-variation="mini"
      >
        { compactNumber }
      </span>
      <p role="tooltip" className="popup-content ui flowing popup transition hidden">
        { localizedNumber }
      </p>
    </div>
  ) : (
    localizedNumber
  );
};

const StatsDashboard = ({ config, stats }) => {
  const all_versions = {
    unique_views: 1000000,
    unique_downloads: 1000000,
    data_volume: 1000000,
    total_uploads: 1000000,
    total_users: 1000000,
    total_communities: 1000000,
    total_languages: 1000000,
  };
  const [totalViews, setTotalViews] = useState(all_versions.unique_views);
  const [totalDownloads, setTotalDownloads] = useState(all_versions.unique_downloads);
  const [totalDataVolume, setTotalDataVolume] = useState(all_versions.data_volume);
  const [totalUploads, setTotalUploads] = useState(all_versions.total_uploads);
  const [totalUsers, setTotalUsers] = useState(all_versions.total_users);
  const [totalCommunities, setTotalCommunities] = useState(all_versions.total_communities);
  const [totalLanguages, setTotalLanguages] = useState(all_versions.total_languages);
  const this_version = all_versions;

  const binary_sizes = !config?.APP_RDM_DISPLAY_DECIMAL_FILE_SIZES;

  return (
    <Container fluid>
      <h2>Stats Dashboard</h2>
      {/* Add your dashboard content here */}

      <div className="ui tiny two statistics rel-mt-1">
        <div className="ui statistic">
          <div className="value">
            { formatNumber(totalViews, 'compact', { compactThreshold: 1_000_000 }) }
          </div>
          <div className="label">
            <i aria-hidden="true" className="eye icon"></i>
            { i18next.t("Total views") }
          </div>
        </div>

        <div className="ui statistic">
          <div className="value">
            { formatNumber(totalDownloads, 'compact', { compactThreshold: 1_000_000 }) }
          </div>
          <div className="label">
            <i aria-hidden="true" className="download icon"></i>
            { i18next.t("Total downloads") }
          </div>
        </div>
      </div>

      <div className="dashboard-stat-container">
        <h2>Stats Dashboard</h2>
        <div className="dashboard-stat-item">
          <div className="ui segment bottom attached">
            Hello world
          </div>
        </div>
      </div>

      <div className="ui accordion rel-mt-1 centered">
        <div className="title">
          <i className="caret right icon" aria-hidden="true"></i>
          <span
            className="trigger"
            data-open-text={ i18next.t("Show more details") }
            data-close-text={ i18next.t("Show less details") }
          >
            { i18next.t("Show more details") }
          </span>
        </div>

        <div className="content">
          <table id="record-statistics" className="ui definition table fluid">
            <thead>
              <tr>
                <th></th>
                <th className="right aligned">{ i18next.t("All versions") }</th>
                <th className="right aligned">{ i18next.t("This version") }</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>
                  { i18next.t("Views") }
                  <i
                    role="button"
                    className="popup-trigger question circle small icon"
                    aria-expanded="false"
                    aria-label={ i18next.t("More info") }
                    data-variation="mini inverted"
                  >
                  </i>
                  <p role="tooltip" className="popup-content ui flowing popup transition hidden">
                    { i18next.t("Total views") }
                  </p>
                </td>
                <td data-label={ i18next.t("All versions") } className="right aligned">
                  <StatsPopup number={all_versions.unique_views} compactThreshold={10_000_000} />
                </td>
                <td data-label={ i18next.t("This version") } className="right aligned">
                  <StatsPopup number={this_version.unique_views} compactThreshold={10_000_000} />
                </td>
              </tr>
              <tr>
                <td>
                  { i18next.t("Downloads") }
                  <i
                    role="button"
                    className="popup-trigger question circle small icon"
                    aria-expanded="false"
                    aria-label={ i18next.t("More info") }
                    data-variation="mini inverted"
                  >
                  </i>
                  <p role="tooltip" className="popup-content ui flowing popup transition hidden">
                    { i18next.t("Total downloads") }
                  </p>
                </td>
                <td data-label={ i18next.t("All versions") } className="right aligned">{ <StatsPopup number={all_versions.unique_downloads} compactThreshold={10_000_000} /> }</td>
                <td data-label={ i18next.t("This version") } className="right aligned">{ <StatsPopup number={this_version.unique_downloads} compactThreshold={10_000_000} /> }</td>
              </tr>
              <tr>
                <td>
                  { i18next.t("Data volume") }
                  <i
                    role="button"
                    className="popup-trigger question circle small icon"
                    aria-expanded="false"
                    aria-label={ i18next.t("More info") }
                    data-variation="mini inverted"
                  >
                  </i>
                  <p role="tooltip" className="popup-content ui flowing popup transition hidden">
                    { i18next.t("Total data volume") }
                  </p>
                </td>

                <td data-label={ i18next.t("All versions") } className="right aligned">{ formatNumber(all_versions.data_volume, 'filesize', { binary: binary_sizes }) }</td>
                <td data-label={ i18next.t("This version") } className="right aligned">{ formatNumber(this_version.data_volume, 'filesize', { binary: binary_sizes }) }</td>
              </tr>
            </tbody>
          </table>
          <p className="text-align-center rel-mt-1">
            <small>
              <a href="/help/statistics">{ i18next.t("More info on how stats are collected.") }...</a>
            </small>
          </p>
        </div>

      </div>

    </Container>
  );
};

StatsDashboard.propTypes = {
  config: PropTypes.object.isRequired,
};

export { StatsDashboard };
