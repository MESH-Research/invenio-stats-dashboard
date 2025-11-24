// Part of the Invenio-Stats-Dashboard extension for InvenioRDM
// Copyright (C) 2025 Mesh Research
//
// Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
// it under the terms of the MIT License; see LICENSE file for more details.

/**
 * Lightens and desaturates a hex color by mixing with white and gray
 * @param {string} hex - Hex color string (e.g., "#c95f22")
 * @param {number} whiteMix - Amount to mix with white (0-1, default 0.3 for lighter)
 * @param {number} grayMix - Amount to mix with gray for desaturation (0-1, default 0.05)
 * @returns {string} - Modified hex color string
 */
export const lightenAndDesaturate = (hex, whiteMix = 0.3, grayMix = 0.05) => {
  const cleanHex = hex.replace("#", "");
  const r = parseInt(cleanHex.substring(0, 2), 16);
  const g = parseInt(cleanHex.substring(2, 4), 16);
  const b = parseInt(cleanHex.substring(4, 6), 16);
  
  // Calculate gray value for desaturation
  const gray = Math.round((r + g + b) / 3);
  
  // Mix with white (lighten) and gray (desaturate)
  const newR = Math.round(r * (1 - whiteMix - grayMix) + 255 * whiteMix + gray * grayMix);
  const newG = Math.round(g * (1 - whiteMix - grayMix) + 255 * whiteMix + gray * grayMix);
  const newB = Math.round(b * (1 - whiteMix - grayMix) + 255 * whiteMix + gray * grayMix);
  
  const toHex = (n) => {
    const hex = Math.min(255, Math.max(0, Math.round(n))).toString(16);
    return hex.length === 1 ? "0" + hex : hex;
  };
  
  return `#${toHex(newR)}${toHex(newG)}${toHex(newB)}`;
};

