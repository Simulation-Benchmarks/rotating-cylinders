"""Run the Fenics benchmark for each semantic benchmark configuration."""

import argparse
import logging
import subprocess
import zipfile
from argparse import Namespace
from pathlib import Path

from semantic_benchmark import runner

LOGGER = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
TOOL_NAME = "openfoam"
BENCHMARK_DIR = Path(__file__).resolve().parent

PROVENANCE_REPORT_NAME = "Rotating Cylinders Provenance"
PROVENANCE_REPORT_DESCRIPTION = "Benchmark for rotating cylinders"
PROVENANCE_REPORT_LICENSE = "https://opensource.org/licenses/MIT"
DEFAULT_CRATE_LICENSE = "https://opensource.org/licenses/MIT"
DEFAULT_CRATE_NAME = "rotating-cylinders provenance (OpenFOAM)"
DEFAULT_CRATE_DESCRIPTION = "Benchmark for rotating cylinders"

UNIT_SYMBOLS = {
    "M": "m",
    "RAD-PER-SEC": "rad/s",
}


def parse_arguments() -> Namespace:
    """Parse command-line arguments for the Fenics benchmark runner."""
    parser = argparse.ArgumentParser(
        description=(
            f"Run the {TOOL_NAME} benchmark workflow for all benchmark configurations."
        )
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
        default=f"{TOOL_NAME}-RoCrate.zip",
        help="Filename or path for the generated aggregate RO-Crate zip file.",
    )
    parser.add_argument(
        "--crate-license",
        default=DEFAULT_CRATE_LICENSE,
        help="License URL recorded in the generated aggregate RO-Crate.",
    )
    parser.add_argument(
        "--crate-name",
        default=DEFAULT_CRATE_NAME,
        help="Name recorded in the generated aggregate RO-Crate.",
    )
    parser.add_argument(
        "--crate-description",
        default=DEFAULT_CRATE_DESCRIPTION,
        help="Description recorded in the generated aggregate RO-Crate.",
    )
    return parser.parse_args()


def build_snakemake_command(
    benchmark_dir: Path,
    configuration: str,
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
        "--force",
    ]


def run_snakemake_workflow(
    benchmark_dir: Path,
    configuration: str,
    output_dir: Path,
) -> None:
    """Run the Snakemake workflow normally and then with provenance reporting."""
    base_cmd = build_snakemake_command(benchmark_dir, configuration)
    reporter_args = runner.build_provenance_reporter_args(
        configuration,
        tool_name=TOOL_NAME,
        report_name=PROVENANCE_REPORT_NAME,
        report_description=PROVENANCE_REPORT_DESCRIPTION,
        report_license=PROVENANCE_REPORT_LICENSE,
    )

    subprocess.run(base_cmd, check=True, cwd=output_dir)
    subprocess.run(base_cmd + reporter_args, check=True, cwd=output_dir)


def extract_case_template(benchmark_dir: Path, output_dir: Path) -> None:
    """Extract the OpenFOAM case template into a configuration result directory."""
    template_zip_path = benchmark_dir / "output_template.zip"
    if not template_zip_path.exists():
        raise FileNotFoundError(f"Missing template archive: {template_zip_path}")
    with zipfile.ZipFile(template_zip_path, "r") as zip_ref:
        zip_ref.extractall(output_dir)


def run_configuration(parameter_file: Path, benchmark_dir: Path) -> None:
    """Prepare and execute one benchmark configuration."""
    configuration, output_dir = runner.prepare_configuration(
        parameter_file, benchmark_dir
    )
    extract_case_template(benchmark_dir, output_dir)

    run_snakemake_workflow(benchmark_dir, configuration, output_dir)

    LOGGER.info("Workflow executed successfully for configuration %s.", configuration)


def run_benchmark(args: Namespace) -> None:
    """Run a complete Fenics benchmark workflow from parsed arguments."""
    benchmark = runner.prepare_benchmark(
        args.benchmark_file, BENCHMARK_DIR, UNIT_SYMBOLS
    )

    for parameter_file in sorted(BENCHMARK_DIR.glob("parameters_*.json")):
        run_configuration(parameter_file, BENCHMARK_DIR)

    rocrate_path = args.result_path / args.rocrate_name
    runner.create_aggregate_rocrate(
        args.result_path,
        benchmark,
        rocrate_path,
        software_name=TOOL_NAME,
        crate_license=args.crate_license,
        crate_name=args.crate_name,
        crate_description=args.crate_description,
        validation_dir=args.result_path / "unpacked_rocrate",
    )
    LOGGER.info("Aggregate RO-Crate created at %s.", rocrate_path)


def main() -> None:
    """Parse arguments and run the Fenics benchmark."""
    runner.configure_logging()
    run_benchmark(parse_arguments())


if __name__ == "__main__":
    main()
