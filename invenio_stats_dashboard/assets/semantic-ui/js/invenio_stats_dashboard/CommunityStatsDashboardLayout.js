/**
 * Community stats dashboard layout
 *
 * Part of Invenio-Stats-Dashboard
 * Copyright (C) 2025 Mesh Research
 *
 * Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
 * it under the terms of the MIT License; see LICENSE file for more details.
 */
import React, { useState } from "react";
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { Button, ButtonGroup, Grid, Header, Transition } from "semantic-ui-react";
import { StatsDashboard } from "./StatsDashboard";
import PropTypes from "prop-types";

/**
 * Community stats dashboard layout
 */
const CommunityStatsDashboardLayout = ({ community, dashboardConfig, stats }) => {
  const [selectedTab, setSelectedTab] = useState("content");

  const handleTabChange = (e, { value }) => {
    setSelectedTab(value);
  };

  return (
    <Grid id="communities-detail-stats-dashboard" class={`communities-detail-body rel-m-2 ${community.slug}`}>
      <Grid.Row>
        <Grid.Column width={3} className="communities-detail-left-sidebar">
          <Header as="h2" className="stats-dashboard-header">
            {dashboardConfig.title || i18next.t("Community Statistics")}
          </Header>
          <ButtonGroup vertical>
            <Button value="content" onClick={handleTabChange} active={selectedTab === "content"}>
              {i18next.t("Content")}
            </Button>
            <Button value="traffic" onClick={handleTabChange} active={selectedTab === "traffic"}>
              {i18next.t("Traffic")}
            </Button>
          </ButtonGroup>
        </Grid.Column>
        <Grid.Column width={13} className="communities-detail-body communities-detail-stats">
          <Transition.Group animation="fade" duration={{ show: 1000, hide: 20 }}>
            {selectedTab === "content" && (
              <StatsDashboard
                community={community}
                dashboardConfig={dashboardConfig}
                stats={stats}
                variant={"content"}
                key="content"
              />
            )}
            {selectedTab === "traffic" && (
              <StatsDashboard
                community={community}
                dashboardConfig={dashboardConfig}
                stats={stats}
                variant={"traffic"}
                key="traffic"
              />
            )}
          </Transition.Group>
        </Grid.Column>
      </Grid.Row>
    </Grid>
  );
};

CommunityStatsDashboardLayout.propTypes = {
  community: PropTypes.object.isRequired,
  dashboardConfig: PropTypes.object.isRequired,
  stats: PropTypes.object.isRequired,
};

export { CommunityStatsDashboardLayout };
