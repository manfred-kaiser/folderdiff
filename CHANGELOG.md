# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [Unreleased]

### Changed

- Migrated packaging from `setup.py` to `pyproject.toml` with hatch as build backend
- Raised minimum supported Python version to 3.11 (developed and tested with 3.13)
- Added a restrictive lint environment (black, bandit, ruff, flake8, pylint, mypy --strict) via `hatch run lint:check`
- Added GitHub Actions workflows for linting across supported Python versions and for publishing to PyPI via Trusted Publishing

## [0.0.2] - 2023-03-06

### Added

- added long description to python package


## [0.0.1] - 2023-03-06

initial release


[Unreleased]: https://github.com/ssh-mitm/folderdiff/compare/0.0.2...main
[0.0.2]: https://github.com/ssh-mitm/folderdiff/compare/0.0.1...0.0.2
[0.0.1]: https://github.com/ssh-mitm/folderdiff/releases/tag/0.0.1