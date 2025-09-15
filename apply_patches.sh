#!/bin/bash

# Script to apply patches from invenio-stats-dashboard to site-packages
# This script copies patch files to their corresponding locations in the virtual environment
#
# Usage: ./apply_patches.sh [venv_path]
#   venv_path: Optional path to python environment directory (default: ./.venv)

set -e  # Exit on any error

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PATCHES_DIR="${SCRIPT_DIR}/invenio_stats_dashboard/patches"

# Use command line argument for venv path, or default to .venv in script directory
if [ $# -eq 1 ]; then
    VENV_DIR="$1"
    # If relative path, make it relative to script directory
    if [[ "$VENV_DIR" != /* ]]; then
        VENV_DIR="${SCRIPT_DIR}/${VENV_DIR}"
    fi
else
    VENV_DIR="${SCRIPT_DIR}/.venv"
fi

# Check if .venv directory exists
if [ ! -d "$VENV_DIR" ]; then
    echo "Error: Virtual environment directory not found at $VENV_DIR"
    exit 1
fi

echo "Using virtual environment: $VENV_DIR"

# Find site-packages directory for Python 3.12
SITE_PACKAGES=$(find "$VENV_DIR" -name "site-packages" -type d | head -1)

if [ -z "$SITE_PACKAGES" ]; then
    echo "Error: site-packages directory not found in $VENV_DIR"
    exit 1
fi

echo "Found site-packages at: $SITE_PACKAGES"

# Function to copy patch files recursively
copy_patches() {
    local source_dir="$1"
    local target_base="$2"
    local package_name="$3"

    echo "Processing patches for $package_name..."

    # Find the corresponding package directory in site-packages
    # Look for exact package name at the top level of site-packages, not in subdirectories
    local package_dir="$SITE_PACKAGES/$package_name"

    # If not found at top level, fall back to search but prefer top-level matches
    if [ ! -d "$package_dir" ]; then
        package_dir=$(find "$SITE_PACKAGES" -maxdepth 1 -name "$package_name" -type d | head -1)
    fi

    if [ -z "$package_dir" ]; then
        echo "Warning: Package directory for $package_name not found in site-packages"
        return
    fi

    echo "Found package directory: $package_dir"

    # Copy files recursively, preserving directory structure
    find "$source_dir" -type f -name "*.py" | while read -r patch_file; do
        # Get relative path from the source directory
        local rel_path="${patch_file#$source_dir/}"

        # Construct target path
        local target_file="$package_dir/$rel_path"
        local target_dir=$(dirname "$target_file")

        # Create target directory if it doesn't exist
        mkdir -p "$target_dir"

        # Copy the file
        echo "Copying: $patch_file -> $target_file"
        cp "$patch_file" "$target_file"
    done
}

# Apply patches for invenio_rdm_records
if [ -d "$PATCHES_DIR/invenio_rdm_records" ]; then
    copy_patches "$PATCHES_DIR/invenio_rdm_records" "$SITE_PACKAGES" "invenio_rdm_records"
else
    echo "Warning: invenio_rdm_records patches directory not found"
fi

# Apply patches for invenio_requests
if [ -d "$PATCHES_DIR/invenio_requests" ]; then
    copy_patches "$PATCHES_DIR/invenio_requests" "$SITE_PACKAGES" "invenio_requests"
else
    echo "Warning: invenio_requests patches directory not found"
fi

echo "Patch application completed!"
echo ""
echo "Summary of applied patches:"
echo "=========================="

# Show what was copied
if [ -d "$PATCHES_DIR/invenio_rdm_records" ]; then
    echo "invenio_rdm_records patches:"
    find "$PATCHES_DIR/invenio_rdm_records" -name "*.py" -exec echo "  - {}" \;
fi

if [ -d "$PATCHES_DIR/invenio_requests" ]; then
    echo "invenio_requests patches:"
    find "$PATCHES_DIR/invenio_requests" -name "*.py" -exec echo "  - {}" \;
fi
