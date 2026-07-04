# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [Unreleased]

### Added

- Unit test suite (pytest) covering the core comparison logic and the CLI
- `hatch test` / pytest integration in `hatch run lint:check`

### Changed

- Migrated packaging from `setup.py` to `pyproject.toml` with hatch as build backend
- Raised minimum supported Python version to 3.11 (developed and tested with 3.13)
- Added a restrictive lint environment (black, bandit, ruff, flake8, pylint, mypy --strict) via `hatch run lint:check`
- Added GitHub Actions workflows for linting across supported Python versions and for publishing to PyPI via Trusted Publishing
- Relicensed from GPL-3.0-or-later to MIT
- Unreadable files (broken symlinks, missing permissions) are now skipped with
  a warning on stderr instead of aborting the whole comparison
- `folderdiff` CLI now prints a clean error message and exits with status 2
  instead of a raw traceback when the comparison itself fails

### Fixed

- Files with duplicate content could be silently dropped from the result
  when computing moved/removed/added file sets, hiding genuinely removed or
  added files whenever another file with identical content existed
- `--prefix` had no effect when comparing two plain directories; it only
  ever worked for the zip-archive side
- A corrupt zip archive's CRC-32 self-test result was computed but never
  checked, so a bad archive still crashed later with an unhandled exception
- Fixed "profix" typo in the `--prefix` help text

## [0.0.2] - 2023-03-06

### Added

- added long description to python package


## [0.0.1] - 2023-03-06

initial release


[Unreleased]: https://github.com/ssh-mitm/folderdiff/compare/0.0.2...main
[0.0.2]: https://github.com/ssh-mitm/folderdiff/compare/0.0.1...0.0.2
[0.0.1]: https://github.com/ssh-mitm/folderdiff/releases/tag/0.0.1