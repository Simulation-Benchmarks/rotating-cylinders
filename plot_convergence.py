"""
plot_convergence.py
-------------------
General convergence plotting script for the rotating-cylinders benchmark.

Place this file at:
    benchmarks/rotating-cylinders/plot_convergence.py

It auto-discovers every solver subfolder that contains a results/ directory,
reads solution_metrics.json and parameters.json from each case, and produces:

  1. One plot per solver  →  <solver>/results/solution_metrics_plot.png
  2. One combined plot    →  rotating-cylinders/convergence_comparison.png
"""

import json
import matplotlib.pyplot as plt
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
root_dir    = Path(__file__).resolve().parent   # rotating-cylinders/
results_key = "results"                         # expected subfolder name

# ---------------------------------------------------------------------------
# Discover solvers: any direct subdirectory that contains a results/ folder
# ---------------------------------------------------------------------------
solvers = sorted(
    d for d in root_dir.iterdir()
    if d.is_dir() and (d / results_key).is_dir()
)

if not solvers:
    print("No solver directories with a 'results/' folder found. Exiting.")
    exit(1)

print(f"Found solvers: {[s.name for s in solvers]}\n")

# ---------------------------------------------------------------------------
# Helper: load all cases for one solver
# ---------------------------------------------------------------------------
def load_solver_results(solver_dir: Path) -> list[dict]:
    """Return a list of result dicts sorted by cells_radial (or conf name)."""
    results_dir = solver_dir / results_key
    all_results = []

    for case_dir in results_dir.iterdir():
        if not case_dir.is_dir():
            continue
        metrics_file = case_dir / "solution_metrics.json"
        params_file  = case_dir / "parameters.json"

        if not metrics_file.exists():
            print(f"  [skip] no solution_metrics.json in {solver_dir.name}/{case_dir.name}")
            continue

        metrics = json.loads(metrics_file.read_text())
        params  = json.loads(params_file.read_text()) if params_file.exists() else {}

        all_results.append({
            "conf":         case_dir.name,
            "cells_radial": params.get("grid", {}).get("cells_radial"),
            "pressure_error": metrics.get("l2_error_pressure_rel"),
            "velocity_error": metrics.get("l2_error_velocity_rel"),
        })

    if not all_results:
        return all_results

    # Sort by cells_radial when available, otherwise by conf name
    if all(d["cells_radial"] is not None for d in all_results):
        all_results.sort(key=lambda d: d["cells_radial"])
    else:
        all_results.sort(key=lambda d: d["conf"])

    return all_results

# ---------------------------------------------------------------------------
# Helper: draw a single-solver convergence plot
# ---------------------------------------------------------------------------
def plot_single_solver(solver_name: str, data: list[dict], save_path: Path) -> None:
    confs    = [d["conf"]            for d in data]
    p_errors = [d["pressure_error"]  for d in data]
    v_errors = [d["velocity_error"]  for d in data]

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(confs, p_errors, marker="o", linewidth=1.5,
            label=r"Relative $L^2$ Error — Pressure")
    ax.plot(confs, v_errors, marker="s", linewidth=1.5,
            label=r"Relative $L^2$ Error — Velocity")

    ax.set_yscale("log")
    ax.set_xlabel("Configuration")
    ax.set_ylabel(r"Relative $L^2$ Error")
    ax.set_title(f"{solver_name.capitalize()} Rotating Cylinders — Convergence Summary")
    ax.legend()
    ax.grid(True, which="both", linestyle="-", alpha=0.3)
    plt.xticks(rotation=45)
    plt.tight_layout()

    fig.savefig(save_path, dpi=150)
    plt.close(fig)
    print(f"  Saved: {save_path.relative_to(root_dir)}")

# ---------------------------------------------------------------------------
# 1. Per-solver plots
# ---------------------------------------------------------------------------
print("--- Per-solver plots ---")
solver_data = {}   # name → list[dict]  (kept for the combined plot)

for solver_dir in solvers:
    data = load_solver_results(solver_dir)
    if not data:
        print(f"  [skip] no valid cases for {solver_dir.name}")
        continue

    solver_data[solver_dir.name] = data
    save_path = solver_dir / results_key / "solution_metrics_plot.png"
    plot_single_solver(solver_dir.name, data, save_path)

# ---------------------------------------------------------------------------
# 2. Combined comparison plot
# ---------------------------------------------------------------------------
print("\n--- Combined comparison plot ---")

if len(solver_data) < 2:
    print("  Only one solver with data — skipping combined plot.")
else:
    # Use a distinct marker per solver so lines stay distinguishable in B&W too
    markers = ["o", "s", "^", "D", "v", "P", "X", "*"]

    fig, axes = plt.subplots(1, 2, figsize=(16, 6), sharey=False)

    for ax, error_key, field in zip(
        axes,
        ["pressure_error", "velocity_error"],
        ["Pressure", "Velocity"],
    ):
        for idx, (solver_name, data) in enumerate(solver_data.items()):
            confs  = [d["conf"]          for d in data]
            errors = [d[error_key]       for d in data]
            marker = markers[idx % len(markers)]
            ax.plot(confs, errors, marker=marker, linewidth=1.5, label=solver_name.capitalize())

        ax.set_yscale("log")
        ax.set_xlabel("Configuration")
        ax.set_ylabel(r"Relative $L^2$ Error")
        ax.set_title(f"Convergence Comparison — {field}")
        ax.legend()
        ax.grid(True, which="both", linestyle="-", alpha=0.3)
        plt.setp(ax.get_xticklabels(), rotation=45)

    fig.suptitle("Rotating Cylinders — Solver Convergence Comparison", fontsize=14)
    plt.tight_layout()

    combined_path = root_dir / "convergence_comparison.png"
    fig.savefig(combined_path, dpi=150)
    plt.close(fig)
    print(f"  Saved: {combined_path.relative_to(root_dir)}")

print("\nDone.")
