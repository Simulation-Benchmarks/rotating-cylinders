# Rotating Cylinders Benchmark

A benchmark for the Navier-Stokes flow between two rotating cylinders (Taylor-Couette flow).

## Problem Definition

This benchmark simulates the flow of a viscous fluid between two concentric rotating cylinders. The inner cylinder rotates with angular velocity $\omega_1$ and the outer cylinder with $\omega_2$. For certain parameter combinations, this setup exhibits the well-known Taylor vortex instability.

## Repository Structure

```
.
├── dumux/                           # DuMux implementation
│   ├── run_benchmark.py             # Main benchmark script
│   ├── convergence_test.py        # Convergence validation test
│   └── Snakefile                    # Snakemake workflow
├── common/                          # Shared postprocessing & provenance scripts
├── docs/                            # Benchmark documentation
├── tests/                           # Test reference data
└── .github/workflows/               # CI configuration
```

## Running the Benchmark

### Using the Python script directly

```bash
cd dumux
python3 run_benchmark.py
python3 convergence_test.py
```

### Using Snakemake

```bash
cd dumux
snakemake --cores all
```

## Implementation: DuMux

The DuMux implementation uses a pre-built container image (`git.iws.uni-stuttgart.de:4567/benchmarks/rotating-cylinders:3.1`) that contains the compiled DuMux application. The `run_benchmark.py` script executes the simulation inside the container via Apptainer/Singularity.

## Acknowledgments

This benchmark was originally developed as part of the [NFDI4Ing Model Validation Platform](https://github.com/BAMresearch/NFDI4IngModelValidationPlatform).
