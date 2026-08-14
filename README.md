# Rotating Cylinders Benchmark

[![REUSE status](https://api.reuse.software/badge/github.com/Simulation-Benchmarks/rotating-cylinders)](https://api.reuse.software/info/github.com/Simulation-Benchmarks/rotating-cylinders)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21922264.svg)](https://doi.org/10.5281/zenodo.21922264)

A benchmark for the Navier-Stokes flow between two rotating cylinders
(Taylor-Couette flow).

## Problem Description

This benchmark simulates the flow of a viscous fluid between two concentric
rotating cylinders. The inner cylinder rotates with angular velocity
$\omega_1$ and the outer cylinder with $\omega_2$. For certain parameter
combinations, this setup exhibits the well-known Taylor vortex instability.

Metrics reported for each run:
- **Relative L2 pressure error** against the analytical Couette-flow solution
- **Relative L2 velocity error** against the analytical Couette-flow solution

See [documentation](docs/benchmark-documentation.md) for the full
mathematical formulation.

## Simulation Tools

Implementations are provided for two CFD frameworks, each with its own
subdirectory and Snakemake workflow:

| Tool | Directory |
|------|-----------|
| DuMux | `dumux/` |
| OpenFOAM | `openfoam/` |

Each implementation varies the radial resolution and stores results as
RO-Crates uploaded to RoHub for provenance tracking.

## Shared Benchmark Package

Reusable semantic benchmark, RO-Crate, and RoHub helpers are provided by the
external Python package `semantic-benchmark`.

The local `provenance/` scripts keep repository-specific configuration and
command-line entrypoints for this rotating-cylinders benchmark.

## Interactive Benchmark Evaluation

The provenance notebook under `notebooks/RoCrate.ipynb` fetches run data from
RoHub and plots the two convergence metrics against the number of radial cells.

Click the badge to open the pre-built notebook on Binder and explore the
provenance plots interactively:

[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/Simulation-Benchmarks/rotating-cylinders/main?labpath=notebooks%2Fbenchmark-results.ipynb)

## Acknowledgments

This benchmark was originally developed as part of the
[NFDI4Ing Model Validation Platform](https://github.com/BAMresearch/NFDI4IngModelValidationPlatform).

## License

This repository follows the [REUSE](https://reuse.software/) specification.
License information is provided per file via [REUSE.toml](./REUSE.toml).
In short:

- Source code files (`.py`, `Snakefile*`, `.github/workflows/*.yml`, `postBuild`) are licensed under the [MIT License](./LICENSES/MIT.txt).
- Documentation (`.md`) is licensed under [CC-BY-4.0](./LICENSES/CC-BY-4.0.txt).
- Data, configuration, and generated artifacts (`.json`, `.yml`, `.toml`, `.ipynb`, `.zip`) are licensed under [CC0-1.0](./LICENSES/CC0-1.0.txt).

## Citation

Please see [`CITATION.cff`](./CITATION.cff) for citation metadata, including the concept DOI and versioned DOIs archived on Zenodo.
