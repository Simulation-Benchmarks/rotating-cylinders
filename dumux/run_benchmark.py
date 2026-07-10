"""Run the dumux benchmark for each semantic benchmark configuration."""

import argparse
import json
import logging
import shutil
import subprocess
from argparse import Namespace
from pathlib import Path

from semantic_benchmark.semantics import BenchmarkLoader, SemanticBenchmark, TextParameter
import semantic_benchmark.rocrate as rocrate

LOG_FORMAT = "%(levelname)s:%(name)s:%(message)s"
LOGGER = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
TOOL_NAME = "dumux"
BENCHMARK_DIR = Path(__file__).resolve().parent

PROVENANCE_REPORTER_NAME = "metadata4ing"
PROVENANCE_REPORT_NAME = "Rotating Cylinders Provenance"
PROVENANCE_REPORT_DESCRIPTION = "Benchmark for rotating cylinders"
PROVENANCE_REPORT_LICENSE = "https://opensource.org/licenses/MIT"
PROVENANCE_PROFILE = "provenance-run-crate-0.5"
DEFAULT_CRATE_LICENSE = "https://opensource.org/licenses/MIT"
DEFAULT_CRATE_NAME = f"NFDI4Ing Provenance ({TOOL_NAME})"
DEFAULT_CRATE_DESCRIPTION = "Benchmark for rotating cylinders"

UNIT_SYMBOLS = {
    "unit:M": "m",
    "unit:RAD-PER-SEC": "rad/s",
}


def configure_logging() -> None:
    """Configure default logging for command-line benchmark runs."""
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)


def build_default_rocrate_name() -> str:
    """Build the default aggregate RO-Crate filename."""
    return f"{TOOL_NAME}-RoCrate.zip"


def parse_arguments() -> Namespace:
    """Parse command-line arguments for the Fenics benchmark runner."""
    parser = argparse.ArgumentParser(
        description=(
            f"Run the {TOOL_NAME} benchmark workflow for all benchmark "
            "configurations."
        )
    )
    parser.add_argument(
        "--benchmark-file",
        type=Path,
        required=True,
        help="Path to the semantic benchmark JSON-LD file.",
    )
    parser.add_argument(
        "--benchmark-zip",
        type=Path,
        required=False,
        help="Path to the zipped benchmark archive to extract.",
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
        default=build_default_rocrate_name(),
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


def parameter_json_key(parameter) -> str:
    """Build the parameters.json key, including the unit suffix when present."""
    unit_symbol = UNIT_SYMBOLS.get(parameter.unit)
    if unit_symbol:
        return f"{parameter.label}[{unit_symbol}]"
    return parameter.label


def parameter_json_value(parameter):
    """Extract the scalar value stored in a benchmark parameter object."""
    if isinstance(parameter, TextParameter):
        return parameter.string_value
    return getattr(parameter, "numerical_value", None)


def load_benchmark(benchmark_file: Path) -> SemanticBenchmark:
    """Load the semantic benchmark description from a JSON-LD file."""
    return BenchmarkLoader(benchmark_file).load()


def create_parameter_files_from_benchmark(
    benchmark: SemanticBenchmark,
    output_dir: Path,
) -> None:
    """Create parameters_*.json files from the benchmark configuration objects."""
    for stale_file in output_dir.glob("parameters_*.json"):
        stale_file.unlink()

    for configuration in benchmark.parameter_sets:
        if not configuration.identifier:
            continue

        payload = {"configuration": configuration.identifier}
        for parameter in configuration.parts:
            payload[parameter_json_key(parameter)] = parameter_json_value(parameter)

        parameter_file = output_dir / f"parameters_{configuration.identifier}.json"
        with open(parameter_file, "w") as outfile:
            json.dump(payload, outfile, indent=4)
            outfile.write("\n")


def load_parameter_file(parameter_file: Path) -> dict:
    """Load a generated parameter JSON file."""
    with open(parameter_file, "r") as infile:
        return json.load(infile)


def create_configuration_output_dir(benchmark_dir: Path, configuration: str) -> Path:
    """Create and return the result directory for a benchmark configuration."""
    output_dir = benchmark_dir / "results" / configuration
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def create_parameter_file(configuration_data: dict, output_dir: Path) -> None:
    """Write the selected configuration as parameters.json in the result directory."""
    with open(output_dir / "parameters.json", "w") as outfile:
        json.dump(configuration_data, outfile, indent=2)


def copy_benchmark_files_to_output_dir(benchmark_dir: Path, output_dir: Path) -> None:
    """Copy benchmark workflow files into a configuration result directory."""
    for item in benchmark_dir.iterdir():
        if not item.is_file():
            continue

        if item.name.startswith("parameters_") and item.suffix == ".json":
            continue

        shutil.copy(item, output_dir / item.name)


def build_snakemake_command(
    benchmark_dir: Path,
    configuration: str,
) -> list[str]:
    """Build the base Snakemake command for one configuration."""
    return [
        "snakemake",
        "-s", str(benchmark_dir/"Snakefile"),
        "--use-singularity",
        "--cores", "all",
        "--resources", "serial_run=1",
        "--singularity-args", f"--bind {REPO_ROOT}/dumux:/dumux/shared",
        "--config", f'conf_name="{configuration}"',
        "--force",
    ]


def build_provenance_reporter_args(configuration: str) -> list[str]:
    """Build Snakemake reporter arguments for the metadata4ing provenance crate."""
    return [
        "--reporter",
        PROVENANCE_REPORTER_NAME,
        "--report-metadata4ing-filename",
        f"{TOOL_NAME}-{configuration}",
        "--report-metadata4ing-name",
        PROVENANCE_REPORT_NAME,
        "--report-metadata4ing-description",
        PROVENANCE_REPORT_DESCRIPTION,
        "--report-metadata4ing-license",
        PROVENANCE_REPORT_LICENSE,
        "--report-metadata4ing-profile",
        PROVENANCE_PROFILE,
    ]


def run_snakemake_workflow(
    benchmark_dir: Path,
    configuration: str,
    output_dir: Path
) -> None:
    """Run the Snakemake workflow normally and then with provenance reporting."""
    base_cmd = build_snakemake_command(benchmark_dir, configuration)
    reporter_args = build_provenance_reporter_args(configuration)

    subprocess.run(base_cmd, check=True, cwd=output_dir)
    subprocess.run(base_cmd + reporter_args, check=True, cwd=output_dir)


def run_configuration(
    parameter_file: Path,
    benchmark_dir: Path,
) -> None:
    """Prepare and execute one benchmark configuration."""
    configuration_data = load_parameter_file(parameter_file)
    configuration = configuration_data.get("configuration")
    if not configuration:
        raise ValueError(f"Missing configuration value in {parameter_file}")

    output_dir = create_configuration_output_dir(benchmark_dir, configuration)

    create_parameter_file(configuration_data, output_dir)
    copy_benchmark_files_to_output_dir(benchmark_dir, output_dir)

    run_snakemake_workflow(
        benchmark_dir,
        configuration,
        output_dir
    )

    LOGGER.info("Workflow executed successfully for configuration %s.", configuration)


def create_aggregate_rocrate(
    results_dir: Path,
    benchmark: SemanticBenchmark,
    rocrate_path: Path,
    crate_license: str,
    crate_name: str,
    crate_description: str,
) -> None:
    """Create one aggregate RO-Crate from all per-configuration result crates."""
    rocrate.create_main_ro(
        path=str(results_dir),
        benchmark_object=benchmark,
        rocrate_path=str(rocrate_path),
        software_name=TOOL_NAME,
        crate_license=crate_license,
        crate_name=crate_name,
        crate_description=crate_description,
        validation_profile=PROVENANCE_PROFILE,
        validation_dir=results_dir / "unpacked_rocrate",
    )
    LOGGER.info("Aggregate RO-Crate created at %s.", rocrate_path)


def run_benchmark(args: Namespace) -> None:
    """Run a complete Fenics benchmark workflow from parsed arguments."""
    configure_logging()

    benchmark = load_benchmark(args.benchmark_file)
    create_parameter_files_from_benchmark(benchmark, BENCHMARK_DIR)

    for parameter_file in sorted(BENCHMARK_DIR.glob("parameters_*.json")):
        run_configuration(parameter_file, BENCHMARK_DIR)

    create_aggregate_rocrate(
        args.result_path,
        benchmark,
        rocrate_path=args.result_path / args.rocrate_name,
        crate_license=args.crate_license,
        crate_name=args.crate_name,
        crate_description=args.crate_description,
    )


def main() -> None:
    """Parse arguments and run the Fenics benchmark."""
    configure_logging()
    run_benchmark(parse_arguments())


if __name__ == "__main__":
    main()
