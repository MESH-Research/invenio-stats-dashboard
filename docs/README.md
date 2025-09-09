# Documentation

This directory contains the Sphinx documentation for the `invenio-stats-dashboard` project.

## Building the Documentation

### Prerequisites

Install the documentation dependencies:

```bash
pip install -e ".[docs]"
```

### Local Development

To build the documentation locally:

```bash
cd docs
make html
```

The built documentation will be available in `docs/build/html/`.

### Live Reload

For development with live reload:

```bash
cd docs
sphinx-autobuild source build/html
```

## Documentation Structure

- `source/` - Source files for the documentation
  - `index.rst` - Main documentation index
  - `overview.md` - Project overview and features
  - `architecture.md` - System architecture and design
  - `setup.md` - Installation and setup instructions
  - `usage.md` - Usage guide and examples
  - `configuration.md` - Configuration reference
  - `cli.md` - Command-line interface reference
  - `api.md` - API reference and configuration variables
  - `changelog.md` - Project changelog
- `build/` - Built documentation (generated)
- `Makefile` - Build automation

## Contributing

When adding or modifying documentation:

1. Update the appropriate source files in `source/`
2. Test the build locally with `make html`
3. Check that all links work and formatting is correct
4. Submit a pull request

## Deployment

The documentation is automatically built and deployed to GitHub Pages when changes are pushed to the `main` branch. The deployment is handled by the GitHub Actions workflow in `.github/workflows/documentation.yml`.
