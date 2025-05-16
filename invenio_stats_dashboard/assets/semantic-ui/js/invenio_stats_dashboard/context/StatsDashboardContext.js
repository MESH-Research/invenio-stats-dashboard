import React, { createContext, useContext } from 'react';

const StatsDashboardContext = createContext(null);

const StatsDashboardProvider = ({ children, value }) => {
  return (
    <StatsDashboardContext.Provider value={value}>
      {children}
    </StatsDashboardContext.Provider>
  );
};

const useStatsDashboard = () => {
  const context = useContext(StatsDashboardContext);
  if (!context) {
    throw new Error('useStatsDashboard must be used within a StatsDashboardProvider');
  }
  return context;
};

export { StatsDashboardContext, StatsDashboardProvider, useStatsDashboard };