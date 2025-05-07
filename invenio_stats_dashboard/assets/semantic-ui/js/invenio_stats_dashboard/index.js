import React from "react";
import ReactDOM from "react-dom";
import { StatsDashboard } from "./components/StatsDashboard";

const domContainer = document.getElementById("stats-dashboard");
const config = JSON.parse(domContainer.dataset.invenioConfig);

ReactDOM.render(<StatsDashboard config={config} />, domContainer);