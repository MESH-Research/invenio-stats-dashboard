import React from "react";
import ReactDOM from "react-dom";
import { StatsDashboard } from "./StatsDashboard";
import { CommunityStatsDashboardLayout } from "./CommunityStatsDashboardLayout";
import { GlobalStatsDashboardLayout } from "./GlobalStatsDashboardLayout";
import { testStats } from "./testData";

// Initialize the dashboard if the container exists
const domContainer = document.getElementById("stats-dashboard");
console.log("domContainer", domContainer);
if (domContainer) {
  const config = JSON.parse(domContainer.dataset.dashboardConfig || '{}');
  console.log("config", config);
  const community = JSON.parse(domContainer.dataset.community || '{}');
  console.log("community", community);

  let DashboardComponent;
  switch (config.dashboard_type) {
    case "community":
      DashboardComponent = CommunityStatsDashboardLayout;
      break;
    case "global":
      DashboardComponent = GlobalStatsDashboardLayout;
      break;
    default:
      DashboardComponent = StatsDashboard;
  }
  console.log("DashboardComponent", DashboardComponent);

  ReactDOM.render(
    <DashboardComponent
      community={community}
      dashboardConfig={config}
      stats={testStats}
    />,
    domContainer
  );
}

// Export all components
export * from './components';
export * from './api';
export * from './utils';
export { CommunityStatsDashboardLayout, GlobalStatsDashboardLayout, StatsDashboard };
