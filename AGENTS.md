# AGENTS.md

## Build & Test

- Build: `make`
- Python Dependencies: `uv add <package>` (dev) / `uv sync --all-extras` (prod)
- JS Dependencies: `npm install`
- Lint: `ruff .` (Python) / `npm run lint` (JS)
- Test: `./run-tests.sh` (Python with Docker) / `./run-js-tests.sh` (JS)

## Code Style

- Python: Imports grouped (std, third-party, local), types (| not Union), docstrings with args/errors, PEP8 88 chars
- JS: ES6+ syntax, 2-space indentation, Prettier formatting (run `npm run format`)

## Guidelines

- No secrets in code
- Verify tests pass before commit
- Prefer `utils/` for helpers
- Do not modify/delete files without explicit permission
- Do not make external network requests without explicit permission

