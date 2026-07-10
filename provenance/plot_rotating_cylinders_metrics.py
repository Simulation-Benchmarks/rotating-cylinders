import argparse
import logging
from typing import Sequence

import matplotlib.pyplot as plt
import pandas as pd

from plot_metrics import load_and_query_rohub, parse_args

LOG_FORMAT = "%(levelname)s:%(name)s:%(message)s"
LOGGER = logging.getLogger(__name__)

BENCHMARK_NAME = "rotating-cylinders"
PARAMETERS = ["cells_radial"]
METRICS = ["l2_error_pressure_rel", "l2_error_velocity_rel"]
X_AXIS_LABEL = "Radial Cells"
Y_AXIS_LABEL = "Relative L2 Error"
PLOT_TITLE = "Rotating Cylinders Convergence"
OUTPUT_FILE_TEMPLATE = "{tool}-convergence-plot.png"


def parse_workflow_args(argv=None):
    """Parse only the arguments that vary in the benchmark workflow."""
    parser = argparse.ArgumentParser(
        description="Plot the rotating-cylinders convergence metrics from RoHub."
    )
    parser.add_argument(
        "--tool",
        type=str,
        required=True,
        help="Tool name used to filter RoHub results",
    )
    parser.add_argument(
        "--output-file",
        type=str,
        default=None,
        help="Final visualization file.",
    )
    parser.add_argument(
        "--use-production-rohub",
        action="store_true",
        default=False,
        help="Use production RoHub instead of the development instance.",
    )
    parser.add_argument(
        "--code-repository-url",
        type=str,
        default=None,
        help="Optional Git branch URL used to filter RoHub results.",
    )
    return parser.parse_args(argv)


def build_plot_args(args):
    """Build the full argument namespace used by the shared RoHub query helper."""
    argv = [
        "--benchmark-name",
        BENCHMARK_NAME,
        "--parameters",
        *PARAMETERS,
        "--metrics",
        *METRICS,
        "--tool",
        args.tool,
        "--x-axis-label",
        X_AXIS_LABEL,
        "--y-axis-label",
        Y_AXIS_LABEL,
        "--plot-title",
        f"{PLOT_TITLE} ({args.tool})",
        "--output-file",
        args.output_file or OUTPUT_FILE_TEMPLATE.format(tool=args.tool),
        "--log-y",
        "true",
    ]

    if args.use_production_rohub:
        argv.append("--use-production-rohub")

    if args.code_repository_url:
        argv.extend(["--code-repository-url", args.code_repository_url])

    return parse_args(argv)


def prepare_convergence_data(
    data: pd.DataFrame,
    parameters: Sequence[str],
    metrics: Sequence[str],
) -> pd.DataFrame:
    """Select and coerce the columns needed for the convergence plot."""
    required_columns = ["tool_name", *parameters, *metrics]
    missing_columns = [col for col in required_columns if col not in data.columns]
    if missing_columns:
        raise ValueError(
            "Cannot plot because these columns are missing: "
            + ", ".join(missing_columns)
        )

    df = data.loc[:, required_columns].copy()
    for column in [*parameters, *metrics]:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    df = df.dropna(subset=[*parameters, *metrics]).sort_values(parameters[0])
    if df.empty:
        raise RuntimeError("No numeric rotating-cylinders convergence data found.")

    return df.reset_index(drop=True)


def plot_convergence(data: pd.DataFrame, args) -> None:
    """Plot pressure and velocity relative L2 errors against radial cells."""
    x_column = PARAMETERS[0]
    pressure_metric, velocity_metric = METRICS

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(
        data[x_column],
        data[pressure_metric],
        marker="o",
        linewidth=1.5,
        label="Pressure",
    )
    ax.plot(
        data[x_column],
        data[velocity_metric],
        marker="s",
        linewidth=1.5,
        label="Velocity",
    )

    x_ticks = sorted(data[x_column].unique())
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel(args.x_axis_label)
    ax.set_ylabel(args.y_axis_label)
    ax.set_title(args.plot_title)
    ax.set_xticks(x_ticks)
    ax.set_xticklabels(
        [str(int(x)) if float(x).is_integer() else str(x) for x in x_ticks]
    )
    ax.grid(True, which="both", linestyle="-", alpha=0.3)
    ax.legend()
    fig.tight_layout()

    if args.output_file:
        fig.savefig(args.output_file, dpi=150)
        LOGGER.info("Plot saved to: %s", args.output_file)
    else:
        plt.show()

    plt.close(fig)


def main():
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    args = build_plot_args(parse_workflow_args())
    provenance_df = load_and_query_rohub(args, PARAMETERS, METRICS)
    convergence_df = prepare_convergence_data(provenance_df, PARAMETERS, METRICS)
    plot_convergence(convergence_df, args)


if __name__ == "__main__":
    main()
