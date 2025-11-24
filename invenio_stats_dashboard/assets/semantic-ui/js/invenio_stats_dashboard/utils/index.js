// Part of the Invenio-Stats-Dashboard extension for InvenioRDM
// Copyright (C) 2025 Mesh Research
//
// Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
// it under the terms of the MIT License; see LICENSE file for more details.

// Exports
export * from "./numbers";
export * from "./dates";
export * from "./filters";
export * from "./chartHelpers";
export * from "./multiDisplayHelpers";
export * from "./jsonDownloadSerializer";
export * from "./i18n";
export * from "./colorHelpers";

function kebabToCamel(str) {
	return str.replace(/-./g, (x) => x[1].toUpperCase());
}

export { kebabToCamel };

