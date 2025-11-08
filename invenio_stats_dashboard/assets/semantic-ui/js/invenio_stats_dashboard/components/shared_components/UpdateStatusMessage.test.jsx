/**
 * Part of Invenio-Stats-Dashboard
 * Copyright (C) 2025 Mesh Research
 *
 * Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
 * it under the terms of the MIT License; see LICENSE file for more details.
 */

import React from "react";
import { render, screen } from "@testing-library/react";
import { UpdateStatusMessage } from "./UpdateStatusMessage";

jest.mock("../../utils/dates", () => ({
  formatCacheTimestamp: jest.fn((timestamp) =>
    new Date(timestamp).toLocaleString(),
  ),
}));

describe("UpdateStatusMessage", () => {
  it("should return null when not updating and no lastUpdated", () => {
    const { container } = render(
      <UpdateStatusMessage isUpdating={false} lastUpdated={null} />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("should show last updated when not updating", () => {
    const timestamp = Date.now();
    render(<UpdateStatusMessage isUpdating={false} lastUpdated={timestamp} />);

    expect(screen.getByText(/Last updated:/)).toBeInTheDocument();
    expect(screen.queryByText(/Updating data/)).not.toBeInTheDocument();
  });

  it("should show updating message when isLoading is false and isUpdating is true", () => {
    const timestamp = Date.now();
    render(
      <UpdateStatusMessage
        isUpdating={true}
        isLoading={false}
        lastUpdated={timestamp}
      />,
    );

    expect(screen.getByText(/Last updated:/)).toBeInTheDocument();
    expect(screen.getByText(/Updating data/)).toBeInTheDocument();
  });

  it("should not show updating message when isLoading is true and isUpdating is true", () => {
    const timestamp = Date.now();
    render(
      <UpdateStatusMessage
        isUpdating={true}
        isLoading={true}
        lastUpdated={timestamp}
      />,
    );

    expect(screen.getByText(/Last updated:/)).toBeInTheDocument();
    expect(screen.queryByText(/Updating data/)).not.toBeInTheDocument();
  });

  it("should show only updating message when updating but no lastUpdated", () => {
    render(
      <UpdateStatusMessage isUpdating={true} isLoading={false} lastUpdated={null} />,
    );

    expect(screen.queryByText(/Last updated:/)).not.toBeInTheDocument();
    expect(screen.getByText(/Updating data/)).toBeInTheDocument();
  });
});

