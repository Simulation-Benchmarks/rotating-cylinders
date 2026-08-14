# Changelog

All notable changes to this project are documented in this file.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- Replaced the Zenodo DOI placeholder with the real DOI (`10.5281/zenodo.21922264`) in `README.md`, `CITATION.cff`, and `codemeta.json`, now that the GitHub–Zenodo integration has archived v0.1.0.

## [0.1.0] - 2026-08-13

### Added
- FAIR4RS metadata: `CITATION.cff` (CFF 1.2.0) and `codemeta.json` (CodeMeta 2.0) including all authors and contributors.
- REUSE-compliant licensing: `LICENSES/MIT.txt`, `LICENSES/CC-BY-4.0.txt`, `LICENSES/CC0-1.0.txt`, and `REUSE.toml` for bulk license annotations.
- GitHub Actions workflow `.github/workflows/reuse.yml` that runs `reuse lint`, generates JSON and SPDX reports, and uploads them as artifacts.
- Pre-commit hook (`fsfe/reuse-tool`) so REUSE violations are caught locally before they reach CI.
- Zenodo DOI placeholder badge in `README.md`; the first release will be archived on Zenodo via the GitHub–Zenodo integration.

### Notes
- This is the first tagged release. Source code files are released under MIT, documentation under CC-BY-4.0, and data/config/generated artifacts under CC0-1.0.
- After Zenodo assigns the real DOI, replace the placeholder DOIs in `README.md`, `CITATION.cff`, and `codemeta.json`.

[Unreleased]: https://github.com/Simulation-Benchmarks/rotating-cylinders/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Simulation-Benchmarks/rotating-cylinders/releases/tag/v0.1.0
