// Color arrays for charts and visualizations
export const CHART_COLORS = {
  // Main color palette
  primary: [
    "#1C4036", // Dark green
    "#547d7d", // Teal
    "#581c87", // Purple
    "#6c7839", // Olive
    "#b29017", // Yellow
    "#276f86", // Blue teal
    "#b54f1e", // Red
  ],

  // Alternative color palette
  secondary: [
    "#2c5c4c", // Lighter green
    "#669999", // Lighter teal
    "#6b2ca3", // Lighter purple
    "#7c8a43", // Lighter olive
    "#c8a41b", // Lighter yellow
    "#3189a2", // Lighter blue teal
    "#c95f22", // Lighter red
  ],

  // Pastel color palette
  pastel: [
    "#e8f0ee", // Pastel green
    "#e6efef", // Pastel teal
    "#efe6f0", // Pastel purple
    "#f0f1e6", // Pastel olive
    "#f5f0e6", // Pastel yellow
    "#e6f0f5", // Pastel blue teal
    "#f5e6e0", // Pastel red
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