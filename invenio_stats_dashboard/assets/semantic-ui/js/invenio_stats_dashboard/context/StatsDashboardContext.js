// Part of the Invenio-Stats-Dashboard extension for InvenioRDM
// Copyright (C) 2025 Mesh Research
//
// Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
// it under the terms of the MIT License; see LICENSE file for more details.

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