# Rotating Cylinders Benchmark

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

See [docs/rotating-cylinders.md](docs/rotating-cylinders.md) for the full
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

[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/Simulation-Benchmarks/rotating-cylinders/main?labpath=notebooks%2Frotating_cylinders.ipynb)

## Acknowledgments

This benchmark was originally developed as part of the
[NFDI4Ing Model Validation Platform](https://github.com/BAMresearch/NFDI4IngModelValidationPlatform).
