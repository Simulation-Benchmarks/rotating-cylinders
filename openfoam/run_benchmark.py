"""Run the OpenFOAM benchmark for each semantic benchmark configuration."""

import argparse
import logging
import subprocess
import zipfile
from argparse import Namespace
from pathlib import Path

from semantic_benchmark import runner

LOGGER = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
BENCHMARK_DIR = Path(__file__).resolve().parent

UNIT_SYMBOLS = {
    "M": "m",
    "RAD-PER-SEC": "rad/s",
}


def parse_arguments() -> Namespace:
    """Parse command-line arguments for the OpenFOAM benchmark runner."""
    parser = argparse.ArgumentParser(
        description="Run the benchmark workflow for all benchmark configurations."
    )
    parser.add_argument(
        "--benchmark-file",
        type=Path,
        required=True,
        help="Path to the semantic benchmark JSON-LD file.",
    )
    parser.add_argument(
        "--result-path",
        type=Path,
        required=True,
        help="Path for benchmark results",
    )
    parser.add_argument(
        "--rocrate-name",
        type=str,
        default=None,
        help="Filename or path for the generated main RO-Crate zip file.",
    )
    parser.add_argument(
        "--main-rocrate-profile",
        type=Path,
        default=BENCHMARK_DIR.parent / "provenance" / "profiles" / "main-rocrate-openfoam.yml",
        help="Main RO-Crate profile YAML file.",
    )
    parser.add_argument(
        "--reporter-rocrate-profile",
        type=Path,
        required=True,
        help="Path to the reporter RO-Crate profile YAML file.",
    )
    parser.add_argument(
        "--workflow-path",
        type=Path,
        required=True,
        help="YAML workflow file used as the main RO-Crate entity.",
    )
    return parser.parse_args()


def build_snakemake_command(
    benchmark_dir: Path,
    configuration: str,
    software_version: str,
) -> list[str]:
    """Build the base Snakemake command for one configuration."""
    return [
        "snakemake",
        "-s",
        str(benchmark_dir / "Snakefile"),
        "--use-singularity",
        "--cores",
        "all",
        "--resources",
        "serial_run=1",
        "--singularity-args",
        f"--bind {REPO_ROOT}/openfoam:/openfoam/shared",
        "--config",
        f'conf_name="{configuration}"',
        f"software_version={software_version}",
        "--force",
    ]


def run_snakemake_workflow(
    benchmark_dir: Path,
    configuration: str,
    output_dir: Path,
    software_version: str,
    reporter_rocrate_profile: Path,
) -> None:
    """Run the Snakemake workflow normally and then with provenance reporting."""
    base_cmd = build_snakemake_command(benchmark_dir, configuration, software_version)
    reporter_args = runner.build_subcrate_args(reporter_rocrate_profile)

    subprocess.run(base_cmd, check=True, cwd=output_dir)
    subprocess.run(base_cmd + reporter_args, check=True, cwd=output_dir)


def extract_case_template(benchmark_dir: Path, output_dir: Path) -> None:
    """Extract the OpenFOAM case template into a configuration result directory."""
    template_zip_path = benchmark_dir / "output_template.zip"
    if not template_zip_path.exists():
        raise FileNotFoundError(f"Missing template archive: {template_zip_path}")
    with zipfile.ZipFile(template_zip_path, "r") as zip_ref:
        zip_ref.extractall(output_dir)


def run_configuration(
    parameter_file: Path, benchmark_dir: Path, software_version: str,
    reporter_rocrate_profile: Path,
) -> Path:
    """Prepare and execute one benchmark configuration."""
    configuration, output_dir = runner.prepare_configuration(
        parameter_file, benchmark_dir
    )
    extract_case_template(benchmark_dir, output_dir)

    run_snakemake_workflow(
        benchmark_dir, configuration, output_dir, software_version, reporter_rocrate_profile
    )

    LOGGER.info("Workflow executed successfully for configuration %s.", configuration)
    return runner.reporter_rocrate_path(output_dir)


def run_benchmark(args: Namespace) -> None:
    """Run a complete OpenFOAM benchmark workflow from parsed arguments."""
    benchmark = runner.prepare_benchmark(
        args.benchmark_file, BENCHMARK_DIR, UNIT_SYMBOLS,
        resource_dir=args.benchmark_file.parent,
        main_profile=args.main_rocrate_profile,
    )
    main_metadata = benchmark.main_profile

    subcrate_paths = [
        run_configuration(
            parameter_file, BENCHMARK_DIR, main_metadata.software_version,
            args.reporter_rocrate_profile,
        )
        for parameter_file in sorted(BENCHMARK_DIR.glob("parameters_*.json"))
    ]

    rocrate_name = args.rocrate_name or f'{main_metadata.software_name}-RoCrate.zip'
    rocrate_path = args.result_path / rocrate_name
    runner.create_main_rocrate(
        args.result_path,
        benchmark,
        rocrate_path,
        subcrate_paths=subcrate_paths,
        workflow_path=args.workflow_path,
    )
    LOGGER.info("Main RO-Crate created at %s.", rocrate_path)


def main() -> None:
    """Parse arguments and run the OpenFOAM benchmark."""
    runner.configure_logging()
    run_benchmark(parse_arguments())


if __name__ == "__main__":
    main()
