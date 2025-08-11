import React from "react";
import ReactDOM from "react-dom";
import { StatsDashboardPage } from "./StatsDashboardPage";
import { StatsDashboardLayout } from "./StatsDashboardLayout";
import { CommunityStatsDashboardLayout } from "./CommunityStatsDashboardLayout";
import { GlobalStatsDashboardLayout } from "./GlobalStatsDashboardLayout";
import { testStatsData } from "./components/test_data";

// Initialize the dashboard if the container exists
const domContainer = document.getElementById("stats-dashboard");
console.log("domContainer", domContainer);
if (domContainer) {
  const config = JSON.parse(domContainer.dataset.dashboardConfig || "{}");
  console.log("config", config);
  console.log("community", domContainer.dataset.community);
  const community = ["None", null, undefined].includes(domContainer.dataset.community)
    ? null
    : JSON.parse(domContainer.dataset.community);

  let DashboardComponent;
  switch (config.dashboard_type) {
    case "community":
      DashboardComponent = CommunityStatsDashboardLayout;
      break;
    case "global":
      DashboardComponent = GlobalStatsDashboardLayout;
      break;
    default:
      DashboardComponent = StatsDashboardLayout;
  }

  // Determine whether to use test data or real API data
  const useTestData = config.use_test_data !== false; // Default to true

  ReactDOM.render(
    <DashboardComponent
      {...(community && { community })}
      dashboardConfig={config}
      {...(useTestData && { stats: testStatsData })}
    />,
    domContainer
  );
}

// Export all components
export * from "./components";
export * from "./api";
export * from "./utils";
export * from "./context";
export {
  CommunityStatsDashboardLayout,
  GlobalStatsDashboardLayout,
  StatsDashboardPage,
  StatsDashboardLayout,
  testStatsData,
};
