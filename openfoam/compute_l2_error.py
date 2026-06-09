#!/usr/bin/env python3
"""
Compute L2 errors for all rotating-cylinders OpenFOAM configurations.

Matches the DuMux main.cc approach:
  - Full 2D domain integral (all cells, not just a sample line)
  - Cell-centre quadrature (FVM cell-average = 1-point quadrature, weighted by cell area)
  - Pressure offset: subtract (sim - exact) at the first cell, then compute error
  - Velocity: both vx and vy components over all cells

Cell centres are computed from polyMesh points+faces+owner — no writeCellCentres needed.
Fields are parsed directly from the ASCII OpenFOAM field files.

Usage:
    python3 compute_l2_error.py                  # auto-finds ./results/
    python3 compute_l2_error.py <results_dir>    # explicit path
"""

import json
import re
import sys
import numpy as np
from pathlib import Path


# ---------------------------------------------------------------------------
# OpenFOAM ASCII field reader
# ---------------------------------------------------------------------------

def _parse_scalar_list(text: str) -> np.ndarray:
    """Extract the internalField nonuniform scalar list."""
    m = re.search(r'internalField\s+nonuniform\s+List<scalar>\s+\d+\s*\(([^)]+)\)', text, re.S)
    if not m:
        # uniform scalar
        m = re.search(r'internalField\s+uniform\s+([\d.eE+\-]+)', text)
        if m:
            return np.array([float(m.group(1))])
        raise ValueError("Could not parse scalar internalField")
    return np.fromstring(m.group(1), sep='\n')


def _parse_vector_list(text: str) -> np.ndarray:
    """Extract the internalField nonuniform vector list → shape (N, 3)."""
    m = re.search(r'internalField\s+nonuniform\s+List<vector>\s+\d+\s*\((.+?)\)\s*;', text, re.S)
    if not m:
        m2 = re.search(r'internalField\s+uniform\s+\(([\d.eE+\-\s]+)\)', text)
        if m2:
            vals = list(map(float, m2.group(1).split()))
            return np.array([vals])
        raise ValueError("Could not parse vector internalField")
    rows = re.findall(r'\(([\d.eE+\-\s]+)\)', m.group(1))
    return np.array([list(map(float, r.split())) for r in rows])


def read_scalar_field(path: Path) -> np.ndarray:
    return _parse_scalar_list(path.read_text())


def read_vector_field(path: Path) -> np.ndarray:
    """Returns shape (N, 3)."""
    return _parse_vector_list(path.read_text())


# ---------------------------------------------------------------------------
# polyMesh reader — compute cell centres and areas from scratch
# ---------------------------------------------------------------------------

def _read_foam_points(text: str) -> np.ndarray:
    """Parse polyMesh/points -> (N, 3) float array."""
    m = re.search(r'\n(\d+)\s*\n\((.+?)\n\)', text, re.S)
    if not m:
        raise ValueError("Could not parse points list")
    tuples = re.findall(r'\(\s*([\d.eE+\-]+)\s+([\d.eE+\-]+)\s+([\d.eE+\-]+)\s*\)', m.group(2))
    return np.array([[float(a), float(b), float(c)] for a, b, c in tuples])


def _read_foam_faces(text: str) -> list:
    """Parse polyMesh/faces -> list of int-index lists."""
    m = re.search(r'\n(\d+)\s*\n\((.+?)\n\)', text, re.S)
    if not m:
        raise ValueError("Could not parse faces list")
    faces = []
    for fm in re.finditer(r'\d+\(([^)]+)\)', m.group(2)):
        faces.append(list(map(int, fm.group(1).split())))
    return faces


def _read_foam_labels(text: str) -> np.ndarray:
    """Parse polyMesh/owner or neighbour -> 1-D int array."""
    m = re.search(r'\n(\d+)\s*\n\((.+?)\n\)', text, re.S)
    if not m:
        raise ValueError("Could not parse label list")
    return np.array(list(map(int, m.group(2).split())))


def compute_cell_centres_and_areas(mesh_dir: Path):
    """
    Compute cell centres and (2-D) cell areas from polyMesh.
    The mesh is 2-D extruded (z from 0 to some dz); we ignore z.

    Returns:
        centres : (nCells, 2)  x,y cell centres
        areas   : (nCells,)    cell face areas projected to xy-plane
    """
    pts       = _read_foam_points((mesh_dir / "points").read_text())   # (nPoints, 3)
    face_list = _read_foam_faces((mesh_dir / "faces").read_text())     # list of lists
    owner     = _read_foam_labels((mesh_dir / "owner").read_text())    # (nFaces,)
    n_cells = int(owner.max()) + 1

    # accumulate face-centre contributions per cell
    sum_fc  = np.zeros((n_cells, 2))
    count   = np.zeros(n_cells, dtype=int)

    for fi, face in enumerate(face_list):
        fc = pts[face, :2].mean(axis=0)   # face centre (x,y)
        c  = owner[fi]
        sum_fc[c] += fc
        count[c]  += 1

    centres = sum_fc / count[:, None]

    # cell area: sum of triangle areas formed by face edges (shoelace on 2-D projection)
    # For a structured annular mesh each cell is a quad; use face ownership to collect
    # the 4 face-centre vertices and compute area via shoelace.
    # Simpler: use face-centre average as above and compute area from cell vertex polygon.
    # We build cell→vertex list then apply shoelace.
    cell_verts = [set() for _ in range(n_cells)]
    for fi, face in enumerate(face_list):
        c = owner[fi]
        cell_verts[c].update(face)

    # also need neighbour to add their faces
    neighbour_text = (mesh_dir / "neighbour").read_text()
    neighbour = _read_foam_labels(neighbour_text)

    for fi, face in enumerate(face_list):
        if fi < len(neighbour):
            c = neighbour[fi]
            cell_verts[c].update(face)

    areas = np.zeros(n_cells)
    for ci in range(n_cells):
        vids = list(cell_verts[ci])
        vxy  = pts[vids, :2]
        # sort by angle around centroid so shoelace works
        cx, cy = vxy.mean(axis=0)
        angles = np.arctan2(vxy[:, 1] - cy, vxy[:, 0] - cx)
        vxy    = vxy[np.argsort(angles)]
        x, y   = vxy[:, 0], vxy[:, 1]
        areas[ci] = 0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))

    return centres, areas


# ---------------------------------------------------------------------------
# Analytical solution (Taylor-Couette)
# ---------------------------------------------------------------------------

def analytical_v_theta(r, r1, r2, omega1, omega2=0.0):
    A = (omega2 * r2**2 - omega1 * r1**2) / (r2**2 - r1**2)
    B = (omega1 - omega2) * r1**2 * r2**2 / (r2**2 - r1**2)
    return A * r + B / r


def analytical_velocity_xy(x, y, r1, r2, omega1, omega2=0.0):
    """Returns (vx, vy) arrays at cell centres."""
    r       = np.sqrt(x**2 + y**2)
    theta   = np.arctan2(y, x)
    v_theta = analytical_v_theta(r, r1, r2, omega1, omega2)
    vx = -v_theta * np.sin(theta)
    vy =  v_theta * np.cos(theta)
    return vx, vy


def analytical_pressure_kinematic(x, y, r1, r2, omega1, omega2=0.0):
    """Kinematic pressure p/rho (up to constant C)."""
    r = np.sqrt(x**2 + y**2)
    A = (omega2 * r2**2 - omega1 * r1**2) / (r2**2 - r1**2)
    B = (omega1 - omega2) * r1**2 * r2**2 / (r2**2 - r1**2)
    return A**2 * r**2 / 2.0 + 2*A*B * np.log(r) - B**2 / (2*r**2)


# ---------------------------------------------------------------------------
# L2 error (area-weighted, matching DuMux quadrature-over-elements)
# ---------------------------------------------------------------------------

def l2_error_2d(sim, exact, areas):
    """
    Area-weighted L2 error — equivalent to DuMux's element quadrature.
    sim, exact : (N,) scalar  or  (N, dim) vector
    areas      : (N,) cell areas (integration weights)
    """
    diff = sim - exact
    if diff.ndim == 1:
        err2  = np.sum(diff**2  * areas)
        norm2 = np.sum(exact**2 * areas)
    else:
        err2  = np.sum(np.sum(diff**2,  axis=1) * areas)
        norm2 = np.sum(np.sum(exact**2, axis=1) * areas)
    return np.sqrt(err2), np.sqrt(norm2)


# ---------------------------------------------------------------------------
# Per-config processing
# ---------------------------------------------------------------------------

def process_config(case_dir: Path) -> dict | None:
    params_file = case_dir / "parameters.json"
    if not params_file.exists():
        print(f"  [skip] no parameters.json in {case_dir.name}")
        return None

    params = json.loads(params_file.read_text())
    r1     = params["domain"]["r1"]
    r2     = params["domain"]["r2"]
    omega1 = params["problem"]["omega1"]
    omega2 = params["problem"].get("omega2", 0.0)

    # locate latest time directory
    time_dirs = sorted(
        [d for d in case_dir.iterdir()
         if d.is_dir() and re.fullmatch(r'[\d.]+', d.name)],
        key=lambda d: float(d.name)
    )
    if not time_dirs:
        print(f"  [skip] no numeric time directories in {case_dir.name}")
        return None
    time_dir = time_dirs[-1]
    print(f"  Time directory: {time_dir.name}")

    # read fields
    try:
        U_all = read_vector_field(time_dir / "U")   # (N, 3)
        p_sim = read_scalar_field(time_dir / "p")   # (N,)
    except Exception as e:
        print(f"  [skip] field read error: {e}")
        return None

    U_sim = U_all[:, :2]   # drop z

    # compute cell centres and areas from polyMesh
    mesh_dir = case_dir / "constant" / "polyMesh"
    try:
        centres, areas = compute_cell_centres_and_areas(mesh_dir)
    except Exception as e:
        print(f"  [skip] mesh read error: {e}")
        return None

    n = len(p_sim)
    if len(centres) != n:
        print(f"  [skip] cell count mismatch: fields={n}, mesh={len(centres)}")
        return None

    cx, cy = centres[:, 0], centres[:, 1]

    # --- analytical fields at cell centres ---
    vx_ex, vy_ex = analytical_velocity_xy(cx, cy, r1, r2, omega1, omega2)
    U_exact = np.stack([vx_ex, vy_ex], axis=1)

    p_exact = analytical_pressure_kinematic(cx, cy, r1, r2, omega1, omega2)

    # --- pressure offset correction (mirrors DuMux: subtract sim-exact at cell 0) ---
    # DuMux subtracts (sim_p[0] - exact_p[0]) from the entire pressure vector
    p_offset = p_sim[0] - p_exact[0]
    p_sim_corrected = p_sim - p_offset

    # --- area-weighted L2 errors ---
    l2_vel,  norm_vel = l2_error_2d(U_sim,            U_exact, areas)
    l2_p,    norm_p   = l2_error_2d(p_sim_corrected,  p_exact, areas)

    rel_vel = l2_vel / norm_vel if norm_vel > 1e-18 else l2_vel
    rel_p   = l2_p   / norm_p   if norm_p   > 1e-18 else l2_p

    print(f"    velocity L2 rel: {rel_vel:.4e}  |  pressure L2 rel: {rel_p:.4e}")

    metrics = {
        "l2_error_velocity_rel": float(rel_vel),
        "l2_error_pressure_rel": float(rel_p),
    }
    out_path = case_dir / "solution_metrics.json"
    out_path.write_text(json.dumps(metrics, indent=2))
    print(f"    Saved: {out_path.relative_to(case_dir.parent)}")
    return metrics

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) > 1:
        results_dir = Path(sys.argv[1]).resolve()
    # else:
    #     results_dir = Path(__file__).resolve().parent / "results"

    if not results_dir.exists():
        print(f"Error: results directory not found: {results_dir}")
        sys.exit(1)

    print(f"Scanning: {results_dir}\n")

    all_results = []
    for case_dir in sorted(results_dir.iterdir()):
        if not case_dir.is_dir():
            continue
        print(f"Processing: {case_dir.name}")
        metrics = process_config(case_dir)
        if metrics is None:
            continue
        params = json.loads((case_dir / "parameters.json").read_text())
        all_results.append({
            "conf":         case_dir.name,
            "cells_radial": params["grid"]["cells_radial"],
            **metrics,
        })

    if not all_results:
        print("\nNo valid configurations found.")
        sys.exit(1)

    print(f"\nProcessed {len(all_results)} configuration(s).")
    # plot_convergence(all_results, results_dir)


if __name__ == "__main__":
    main()