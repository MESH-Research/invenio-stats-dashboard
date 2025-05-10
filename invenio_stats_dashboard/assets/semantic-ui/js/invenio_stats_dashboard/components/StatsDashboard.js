import React, { useState } from "react";
import PropTypes from "prop-types";
import { Container } from "semantic-ui-react";
import { i18next } from "@translations/i18next";

export const StatsDashboard = ({ config, stats }) => {
  const all_versions = stats.all_versions;
  const [totalViews, setTotalViews] = useState(all_versions.unique_views);
  const [totalDownloads, setTotalDownloads] = useState(all_versions.unique_downloads);
  const [totalDataVolume, setTotalDataVolume] = useState(all_versions.data_volume);
  const [totalUploads, setTotalUploads] = useState(all_versions.total_uploads);
  const [totalUsers, setTotalUsers] = useState(all_versions.total_users);
  const [totalCommunities, setTotalCommunities] = useState(all_versions.total_communities);
  const [totalLanguages, setTotalLanguages] = useState(all_versions.total_languages);


  const binary_sizes = !config?.APP_RDM_DISPLAY_DECIMAL_FILE_SIZES;

  return (
    <Container fluid>
      <h2>Stats Dashboard</h2>
      {/* Add your dashboard content here */}

      <div class="ui tiny two statistics rel-mt-1">

        <div class="ui statistic">
          <div class="value">
            { totalViews|compact_number(max_value=1_000_000) }
          </div>
          <div class="label">
            <i aria-hidden="true" class="eye icon"></i>
            { i18next.t("Total views") }
          </div>
        </div>

        <div class="ui statistic">
          <div class="value">
            { totalDownloads|compact_number(max_value=1_000_000) }
          </div>
          <div class="label">
            <i aria-hidden="true" class="download icon"></i>
            { i18next.t("Total downloads") }
          </div>
        </div>
      </div>

      <div class="ui accordion rel-mt-1 centered">
        <div class="title">
          <i class="caret right icon" aria-hidden="true"></i>
          <span
            tabindex="0"
            class="trigger"
            data-open-text={ i18next.t("Show more details") }
            data-close-text={ i18next.t("Show less details") }
          >
            { i18next.t("Show more details") }
          </span>
        </div>

        <div class="content">
          <table id="record-statistics" class="ui definition table fluid">
            <thead>
              <tr>
                <th></th>
                <th class="right aligned">{ i18next.t("All versions") }</th>
                <th class="right aligned">{ i18next.t("This version") }</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>
                  { i18next.t("Views") }
                  <i
                    tabindex="0"
                    role="button"
                    style="position:relative"
                    class="popup-trigger question circle small icon"
                    aria-expanded="false"
                    aria-label="{{ _('More info') }}"
                    data-variation="mini inverted"
                  >
                  </i>
                  <p role="tooltip" class="popup-content ui flowing popup transition hidden">
                    { i18next.t("Total views") }
                  </p>
                </td>
                <td data-label={ i18next.t("All versions") } class="right aligned">{ stats_popup(all_versions.unique_views) }</td>
                <td data-label={ i18next.t("This version") } class="right aligned">{ stats_popup(this_version.unique_views) }</td>
              </tr>
              <tr>
                <td>
                  { i18next.t("Downloads") }
                  <i
                    tabindex="0"
                    role="button"
                    style="position:relative"
                    class="popup-trigger question circle small icon"
                    aria-expanded="false"
                    aria-label="{{ _('More info') }}"
                    data-variation="mini inverted"
                  >
                  </i>
                  <p role="tooltip" class="popup-content ui flowing popup transition hidden">
                    { i18next.t("Total downloads") }
                  </p>
                </td>
                <td data-label={ i18next.t("All versions") } class="right aligned">{ stats_popup(all_versions.unique_downloads) }</td>
                <td data-label={ i18next.t("This version") } class="right aligned">{ stats_popup(this_version.unique_downloads) }</td>
              </tr>
              <tr>
                <td>
                  { i18next.t("Data volume") }
                  <i
                    tabindex="0"
                    role="button"
                    style="position:relative"
                    class="popup-trigger question circle small icon"
                    aria-expanded="false"
                    aria-label="{{ _('More info') }}"
                    data-variation="mini inverted"
                  >
                  </i>
                  <p role="tooltip" class="popup-content ui flowing popup transition hidden">
                    { i18next.t("Total data volume") }
                  </p>
                </td>

                <td data-label={ i18next.t("All versions") } class="right aligned">{ all_versions.data_volume|filesizeformat(binary=binary_sizes) }</td>
                <td data-label={ i18next.t("This version") } class="right aligned">{ this_version.data_volume|filesizeformat(binary=binary_sizes) }</td>
              </tr>
            </tbody>
          </table>
          <p class="text-align-center rel-mt-1">
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
