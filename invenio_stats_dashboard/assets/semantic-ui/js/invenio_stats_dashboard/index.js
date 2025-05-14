import React from "react";
import ReactDOM from "react-dom";
import { StatsDashboard } from "./StatsDashboard";
import { testStats } from "./testData";

// Export all components
export * from './components';
export { StatsDashboard };

// Initialize the dashboard if the container exists
const domContainer = document.getElementById("stats-dashboard");
if (domContainer) {
  const config = JSON.parse(domContainer.dataset.invenioConfig || '{}');
  ReactDOM.render(
    <StatsDashboard
      config={config}
      stats={testStats}
      title="Test Dashboard"
      description="This is a test dashboard with dummy data"
    />,
    domContainer
  );
}