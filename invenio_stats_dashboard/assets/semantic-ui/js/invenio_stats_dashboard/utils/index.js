// Part of the Invenio-Stats-Dashboard extension for InvenioRDM
// Copyright (C) 2025 Mesh Research
//
// Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
// it under the terms of the MIT License; see LICENSE file for more details.

// Exports
export * from "./numbers";
export * from "./dates";
export * from "./filters";
export * from "./multiDisplayHelpers";

function kebabToCamel(str) {
	return str.replace(/-./g, (x) => x[1].toUpperCase());
}

export { kebabToCamel };

