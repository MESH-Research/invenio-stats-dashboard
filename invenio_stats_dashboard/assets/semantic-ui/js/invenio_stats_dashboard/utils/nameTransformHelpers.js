/**
 * Name transformation utilities for chart display
 *
 * This module provides utilities for transforming names and labels for better
 * display in charts, particularly for license/rights data where long names
 * need to be abbreviated while preserving full names for tooltips.
 */

/**
 * Transform license ID to display-friendly short form
 * @param {string} id - The license ID
 * @returns {string} - The transformed short form
 */
const transformLicenseId = (id) => {
  if (!id) return id;

  // Creative Commons licenses: convert to uppercase with hyphens
  if (id.startsWith('cc-')) {
    return id.toUpperCase();
  }

  // Common license patterns: capitalize appropriately
  if (id === 'mit') return 'MIT';
  if (id === 'isc') return 'ISC';
  if (id === 'arr') return 'ARR';
  if (id.startsWith('apache-')) return 'Apache-' + id.split('-')[1];
  if (id.startsWith('gpl-')) return 'GPL-' + id.split('-')[1];
  if (id.startsWith('lgpl-')) return 'LGPL-' + id.split('-')[1];
  if (id.startsWith('bsd-')) return 'BSD-' + id.split('-')[1];
  if (id.startsWith('mpl-')) return 'MPL-' + id.split('-')[1];
  if (id.startsWith('epl-')) return 'EPL-' + id.split('-')[1];

  // Default: return as-is
  return id;
};

/**
 * Check if a license ID should use short form (has known abbreviation)
 * @param {string} id - The license ID
 * @returns {boolean} - Whether to use short form
 */
const shouldUseShortForm = (id) => {
  if (!id) return false;

  // Creative Commons licenses
  if (id.startsWith('cc-')) return true;

  // Common licenses with known short forms
  const shortFormLicenses = ['mit', 'isc', 'arr', 'unlicense'];
  if (shortFormLicenses.includes(id)) return true;

  // License families with patterns
  const licenseFamilies = ['apache-', 'gpl-', 'lgpl-', 'bsd-', 'mpl-', 'epl-'];
  return licenseFamilies.some(family => id.startsWith(family));
};

/**
 * Get both short and long forms of a license label
 * @param {string} id - The license ID
 * @param {string} label - The full license label
 * @returns {Object} - Object with short and long forms
 */
export const getLicenseLabelForms = (id, label) => {
  if (shouldUseShortForm(id)) {
    const shortForm = transformLicenseId(id);
    return {
      short: shortForm,
      long: label,
      isAbbreviated: true
    };
  }

  return {
    short: label,
    long: label,
    isAbbreviated: false
  };
};

/**
 * Transform item data for chart display with appropriate name forms
 * @param {Object} item - The data item
 * @param {string} searchField - The search field being processed
 * @param {string} currentLanguage - Current language for localization
 * @param {Function} extractLocalizedLabel - Function to extract localized labels
 * @returns {Object} - Object with transformed name data
 */
export const transformItemForChart = (item, searchField, currentLanguage, extractLocalizedLabel) => {
  const itemName = item.name || item.id;
  const localizedName = extractLocalizedLabel(itemName, currentLanguage);

  // Get both short and long forms for license/rights labels
  const labelForms = searchField === 'metadata.rights.id'
    ? getLicenseLabelForms(item.id, localizedName)
    : { short: localizedName, long: localizedName, isAbbreviated: false };

  return {
    name: labelForms.short,
    fullName: labelForms.long,
    isAbbreviated: labelForms.isAbbreviated,
    id: item.id,
    originalName: localizedName
  };
};
