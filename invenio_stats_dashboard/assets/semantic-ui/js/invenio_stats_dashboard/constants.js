export const DASHBOARD_TYPES = {
  GLOBAL: "global",
  COMMUNITY: "community",
};

export const RECORD_START_BASES = {
  ADDED: "added",
  CREATED: "created",
  PUBLISHED: "published",
};

// Color arrays for charts and visualizations
export const CHART_COLORS = {
  // Main color palette
  primary: [
    ["blue", "#276f86"], // Blue teal
    ["red", "#b54f1e"], // Red
    ["teal", "#547d7d"], // Teal
    ["purple", "#581c87"], // Purple
    ["yellow", "#b29017"], // Yellow
    ["green", "#1C4036"], // Dark green
    ["olive", "#6c7839"], // Olive
    ["grey", "#808080"], // Grey
  ],

  // Alternative color palette
  secondary: [
    ["blue", "#3189a2"], // Lighter blue teal
    ["red", "#c95f22"], // Lighter red
    ["teal", "#669999"], // Lighter teal
    ["purple", "#6b2ca3"], // Lighter purple
    ["yellow", "#c8a41b"], // Lighter yellow
    ["green", "#2c5c4c"], // Lighter green
    ["olive", "#7c8a43"], // Lighter olive
    ["grey", "#808080"], // Lighter grey
  ],

  // Pastel color palette
  pastel: [
    ["green", "#e8f0ee"], // Pastel green
    ["teal", "#e6efef"], // Pastel teal
    ["purple", "#efe6f0"], // Pastel purple
    ["olive", "#f0f1e6"], // Pastel olive
    ["yellow", "#f5f0e6"], // Pastel yellow
    ["blue", "#e6f0f5"], // Pastel blue teal
    ["red", "#f5e6e0"], // Pastel red
  ],
};

// UI Colors
export const UI_COLORS = {
  background: {
    primary: "#eff6f4",
    secondary: "#f8f9fa",
  },
  border: {
    primary: "#DEEEEA",
  },
  text: {
    primary: "#547d7d",
    secondary: "#1C4036",
  },
};

// Chart configuration constants
export const CHART_CONFIG = {
  defaultHeight: 400,
  defaultWidth: "100%",
  animationDuration: 1000,
  tooltipDelay: 200,
};

// Date range constants
export const DATE_RANGE = {
  defaultPeriod: "30days",
  maxHistoryYears: 15,
};

// Export all constants as a single object
export default {
  CHART_COLORS,
  UI_COLORS,
  CHART_CONFIG,
  DATE_RANGE,
};