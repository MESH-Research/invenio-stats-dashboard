/**
 * Part of Invenio-Stats-Dashboard
 * Copyright (C) 2025 Mesh Research
 *
 * Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
 * it under the terms of the MIT License; see LICENSE file for more details.
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { StatsDashboardDisabledMessage } from './StatsDashboardDisabledMessage';

// Mock i18next
const mockT = jest.fn((key) => key);
jest.mock('@translations/invenio_stats_dashboard/i18next', () => {
  const mockT = jest.fn((key) => key);
  return {
    i18next: {
      t: mockT,
    },
    __mockT: mockT, // Export for test access
  };
});

describe('StatsDashboardDisabledMessage', () => {
  let mockT;

  beforeEach(() => {
    jest.clearAllMocks();
    // Get the mock function from the module
    const i18nextModule = require('@translations/invenio_stats_dashboard/i18next');
    mockT = i18nextModule.__mockT || i18nextModule.i18next.t;
    mockT.mockImplementation((key) => key);
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('Basic Rendering', () => {
    it('should render the message content', () => {
      const message = 'The dashboard is disabled.';
      render(
        <StatsDashboardDisabledMessage
          msg={message}
          dashboardType="global"
        />
      );

      expect(screen.getByText(message)).toBeInTheDocument();
    });

    it('should render the translated header', () => {
      render(
        <StatsDashboardDisabledMessage
          msg="Dashboard disabled"
          dashboardType="global"
        />
      );

      expect(mockT).toHaveBeenCalledWith('Dashboard Not Enabled');
      expect(screen.getByText('Dashboard Not Enabled')).toBeInTheDocument();
    });

    it('should render Message component with info type', () => {
      const { container } = render(
        <StatsDashboardDisabledMessage
          msg="Dashboard disabled"
          dashboardType="global"
        />
      );

      // Semantic UI Message component with info prop renders with 'info' class
      const messageElement = container.querySelector('.ui.info.message');
      expect(messageElement).toBeInTheDocument();
    });
  });

  describe('CSS Classes and Styling', () => {
    it('should apply correct container class for global dashboard', () => {
      const { container } = render(
        <StatsDashboardDisabledMessage
          msg="Dashboard disabled"
          dashboardType="global"
        />
      );

      // Semantic UI Container renders as a div with the className
      const containerElement = container.querySelector('.ui.container');
      expect(containerElement).toHaveClass('grid');
      expect(containerElement).toHaveClass('global-stats-dashboard');
      expect(containerElement).toHaveClass('stats-dashboard-container');
    });

    it('should apply correct container class for community dashboard', () => {
      const { container } = render(
        <StatsDashboardDisabledMessage
          msg="Dashboard disabled"
          dashboardType="community"
        />
      );

      const containerElement = container.querySelector('.ui.container');
      expect(containerElement).toHaveClass('grid');
      expect(containerElement).toHaveClass('community-stats-dashboard');
      expect(containerElement).toHaveClass('stats-dashboard-container');
    });

    it('should apply rel-mb-2 class for global dashboard', () => {
      const { container } = render(
        <StatsDashboardDisabledMessage
          msg="Dashboard disabled"
          dashboardType="global"
        />
      );

      const containerElement = container.querySelector('.ui.container');
      expect(containerElement).toHaveClass('rel-mb-2');
      expect(containerElement).not.toHaveClass('rel-m-2');
    });

    it('should apply rel-m-2 class for community dashboard', () => {
      const { container } = render(
        <StatsDashboardDisabledMessage
          msg="Dashboard disabled"
          dashboardType="community"
        />
      );

      const containerElement = container.querySelector('.ui.container');
      expect(containerElement).toHaveClass('rel-m-2');
      expect(containerElement).not.toHaveClass('rel-mb-2');
    });
  });

  describe('ID Attribute', () => {
    it('should set correct id for global dashboard', () => {
      const { container } = render(
        <StatsDashboardDisabledMessage
          msg="Dashboard disabled"
          dashboardType="global"
        />
      );

      const containerElement = container.querySelector('.ui.container');
      expect(containerElement).toHaveAttribute('id', 'global-stats-dashboard');
    });

    it('should set correct id for community dashboard', () => {
      const { container } = render(
        <StatsDashboardDisabledMessage
          msg="Dashboard disabled"
          dashboardType="community"
        />
      );

      const containerElement = container.querySelector('.ui.container');
      expect(containerElement).toHaveAttribute('id', 'community-stats-dashboard');
    });
  });

  describe('Structure and Layout', () => {
    it('should render Container, Grid.Row, and Grid.Column in correct hierarchy', () => {
      const { container } = render(
        <StatsDashboardDisabledMessage
          msg="Dashboard disabled"
          dashboardType="global"
        />
      );

      expect(container.querySelector('.ui.container')).toBeInTheDocument();
      expect(container.querySelector('.ui.grid .row')).toBeInTheDocument();
      expect(container.querySelector('.ui.info.message')).toBeInTheDocument();
    });

    it('should render Grid.Column inside Grid.Row', () => {
      const { container } = render(
        <StatsDashboardDisabledMessage
          msg="Dashboard disabled"
          dashboardType="global"
        />
      );

      const gridRow = container.querySelector('.ui.grid .row');
      const gridColumn = container.querySelector('.ui.grid .row .column');
      const message = container.querySelector('.ui.info.message');
      
      expect(gridRow).toContainElement(gridColumn);
      expect(gridColumn).toContainElement(message);
    });
  });

  describe('Different Dashboard Types', () => {
    it('should handle global dashboard type correctly', () => {
      const { container } = render(
        <StatsDashboardDisabledMessage
          msg="Global dashboard is disabled"
          dashboardType="global"
        />
      );

      const containerElement = container.querySelector('.ui.container');
      expect(containerElement).toHaveClass('global-stats-dashboard');
      expect(containerElement).toHaveAttribute('id', 'global-stats-dashboard');
      expect(containerElement).toHaveClass('rel-mb-2');
      expect(screen.getByText('Global dashboard is disabled')).toBeInTheDocument();
    });

    it('should handle community dashboard type correctly', () => {
      const { container } = render(
        <StatsDashboardDisabledMessage
          msg="Community dashboard is disabled"
          dashboardType="community"
        />
      );

      const containerElement = container.querySelector('.ui.container');
      expect(containerElement).toHaveClass('community-stats-dashboard');
      expect(containerElement).toHaveAttribute('id', 'community-stats-dashboard');
      expect(containerElement).toHaveClass('rel-m-2');
      expect(screen.getByText('Community dashboard is disabled')).toBeInTheDocument();
    });
  });

  describe('Message Content Variations', () => {
    it('should render long message content', () => {
      const longMessage =
        'The global statistics dashboard must be enabled by the administrators. Please contact your system administrator to enable this feature.';
      render(
        <StatsDashboardDisabledMessage
          msg={longMessage}
          dashboardType="global"
        />
      );

      expect(screen.getByText(longMessage)).toBeInTheDocument();
    });

    it('should render short message content', () => {
      const shortMessage = 'Dashboard disabled';
      render(
        <StatsDashboardDisabledMessage
          msg={shortMessage}
          dashboardType="global"
        />
      );

      expect(screen.getByText(shortMessage)).toBeInTheDocument();
    });

    it('should render message with special characters', () => {
      const specialMessage = 'Dashboard is disabled. Contact admin@example.com for help.';
      render(
        <StatsDashboardDisabledMessage
          msg={specialMessage}
          dashboardType="global"
        />
      );

      expect(screen.getByText(specialMessage)).toBeInTheDocument();
    });
  });
});

