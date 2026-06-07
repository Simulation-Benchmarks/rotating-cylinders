# Rotating Cylinders Benchmark (Taylor-Couette Flow)

## Problem description

This benchmark simulates the flow of a viscous incompressible fluid confined
between two concentric cylinders. The inner cylinder rotates with angular
velocity $\omega_1$ and the outer cylinder with angular velocity $\omega_2$.
For certain parameter combinations the flow is dominated by viscous shear
(Couette flow); above a critical inner-cylinder Reynolds number the flow
becomes unstable and develops the well-known Taylor vortex pattern.

We work in 2D cylindrical coordinates $(r, \theta)$ in the meridional
$(r, z)$ plane. The annulus has inner radius $r_\mathrm{in}$ and outer radius
$r_\mathrm{out}$, with $\eta = r_\mathrm{in}/r_\mathrm{out}$ the radius ratio.

## Governing equations

The incompressible Navier-Stokes equations in cylindrical coordinates read

$$
\begin{aligned}
\rho\left(\frac{\partial \boldsymbol u}{\partial t} + (\boldsymbol u \cdot \nabla)\boldsymbol u\right) &= -\nabla p + \mu \Delta \boldsymbol u, \\
\nabla \cdot \boldsymbol u &= 0,
\end{aligned}
$$

with density $\rho$ and dynamic viscosity $\mu$. The velocity field is
$\boldsymbol u = (u_r, u_\theta, u_z)$ and $p$ is the pressure.

The non-dimensional control parameters are

- The **Reynolds number** of the inner cylinder
  $\mathrm{Re}_1 = \rho\, \omega_1\, r_\mathrm{in}\, (r_\mathrm{out} - r_\mathrm{in}) / \mu$.
- The **radius ratio** $\eta = r_\mathrm{in}/r_\mathrm{out}$.
- The **aspect ratio** $\Gamma = L / (r_\mathrm{out} - r_\mathrm{in})$, where
  $L$ is the axial length of the domain.
- The **outer-cylinder Reynolds number**
  $\mathrm{Re}_2 = \rho\, \omega_2\, r_\mathrm{out}\, (r_\mathrm{out} - r_\mathrm{in}) / \mu$.

## Domain and boundary conditions

The computational domain is the open annulus
$\Omega = \{(r,\theta,z) \mid r_\mathrm{in} < r < r_\mathrm{out},\; 0 < z < L\}$
in a 2D $(r,z)$ cross-section. The boundary conditions are

$$
\begin{aligned}
\boldsymbol u(r=r_\mathrm{in}) &= (0,\; \omega_1 r_\mathrm{in},\; 0), \\
\boldsymbol u(r=r_\mathrm{out}) &= (0,\; \omega_2 r_\mathrm{out},\; 0), \\
\boldsymbol u(z=0) &= \boldsymbol u(z=L) \quad \text{(periodic)}, \\
p &\text{ pinned at one point to remove the null space.}
\end{aligned}
$$

## Analytical reference: circular Couette flow

For steady, axisymmetric, purely azimuthal flow the analytical solution is

$$
u_\theta^\mathrm{Couette}(r) = A r + \frac{B}{r},
$$

with constants

$$
\begin{aligned}
A &= \frac{\omega_2 r_\mathrm{out}^2 - \omega_1 r_\mathrm{in}^2}{r_\mathrm{out}^2 - r_\mathrm{in}^2}, \\
B &= \frac{(\omega_1 - \omega_2) r_\mathrm{in}^2 r_\mathrm{out}^2}{r_\mathrm{out}^2 - r_\mathrm{in}^2}.
\end{aligned}
$$

This is the reference used to compute the relative $L^2$ error of the velocity
field in the postprocessing step.

## Output metrics

- `l2_error_velocity_rel` — relative $L^2$ error of the velocity field with
  respect to the analytical Couette solution.
- `solution_metrics.json` — per-configuration metrics, written by the
  postprocessing script.

## Table of parameters

### Model parameters

| Parameter             | Description                                |
| --------------------- | ------------------------------------------ |
| $r_\mathrm{in}$[m]    | Inner cylinder radius.                     |
| $r_\mathrm{out}$[m]   | Outer cylinder radius.                     |
| $L$[m]                | Axial length of the domain.                |
| $\rho$[kg/m³]         | Fluid density.                             |
| $\mu$[Pa·s]           | Dynamic viscosity.                         |
| $\omega_1$[rad/s]     | Inner-cylinder angular velocity.           |
| $\omega_2$[rad/s]     | Outer-cylinder angular velocity.           |

### Numerical parameters

| Parameter         | Description                                |
| ----------------- | ------------------------------------------ |
| mesh refinement   | Number / size of cells per configuration.  |
| solver tolerances | Linear and non-linear solver tolerances.   |
| time step         | Time step (for transient runs).           |

## Numerical Results

The generated notebook `notebooks/rotating_cylinders.ipynb` is rebuilt by the
`merge-docs-to-notebooks` GitHub Actions workflow and is uploaded as an
artifact on every push to `main`, PR to `main`, and manual dispatch.

test
