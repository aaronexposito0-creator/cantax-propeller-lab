# Preliminary blade element momentum model

This model estimates an axial, positive-thrust open-water propeller scenario. It is a numerical engineering demonstrator, not a calibrated prediction of the CAD propeller's performance. No measured polars or open-water trials for this geometry are included.

## Geometry and definitions

The radial station table supplies chord weight, pitch, thickness, skew and rake factors. Chord normalization uses the full nominal table:

```text
c(r) = w(r) * EAR * pi * D^2 / (4 * B * integral(w(r) dr))
beta(r) = atan((P/D) * D * pitch_factor(r) / (2*pi*r))
n = RPM/60
omega = 2*pi*n
```

The nominal expanded area ratio is separate from the CAD's trimmed-area estimate. The active hydrodynamic annuli extend from `max(hub_ratio + 0.02, 0.22, minimum r/R)` to `r/R = 0.99`; midpoint integration avoids loss-factor singularities. The default refinement test compares 60 and 120 annuli.

Using the ITTC coefficient definitions:

```text
J    = Va/(n*D)
KT   = T/(rho*n^2*D^4)
KQ   = Q/(rho*n^2*D^5)
P    = omega*Q
eta0 = T*Va/P = J*KT/(2*pi*KQ)
```

See the linked [ITTC open-water procedure](https://www.ittc.info/media/4074/75-02-03-021.pdf). Using these definitions is not an ITTC test or an experimental validation.

## Annular solution

The two unknown disk-induced velocities are axial `u` and tangential `v`. Here `v` is half the far-wake tangential velocity. For radius `r`:

```text
Vx = Va + u
Vtheta = omega*r - v
W = hypot(Vx, Vtheta)
phi = atan2(Vx, Vtheta)
alpha = beta - phi

dT/dr = 0.5*rho*W^2*B*c*(Cl*cos(phi) - Cd*sin(phi))
dQ/dr = 0.5*rho*W^2*B*c*r*(Cl*sin(phi) + Cd*cos(phi))

dT/dr = 4*pi*rho*r*F*u*(Va + u)
dQ/dr = 4*pi*rho*r^2*F*v*(Va + u)
```

The propeller momentum and blade-force balances follow the [BladeAD BEM background](https://bladead.readthedocs.io/en/latest/src/background/bem.html). MATLAB's base `fminsearch` minimizes two normalized residuals per annulus with penalties for negative induced velocities. Both residuals must be below `1e-5` in every annulus. A failed solve is not replaced with a fabricated value.

## Explicit physical approximations

The symmetric thin-airfoil closure uses `Cl = 2*pi*alpha`, with alpha in radians. Its small-angle basis is discussed in [Liburdy's fluid mechanics text](https://open.oregonstate.education/intermediate-fluid-mechanics/chapter/the-panel-method-an-introduction/). This is an analytic inviscid slope, not a polar measured for the generated section.

Friction uses the ITTC-1957 line `Cf = 0.075/(log10(Re)-2)^2`, where `Re = W*c/nu`, with the project's approximation `Cd = 2*Cf`. The [ITTC procedure](https://www.ittc.info/media/11846/75-02-05-01.pdf) supplies the friction relation; applying it to two blade faces is this demonstrator's assumption. It omits pressure drag, calibrated transition, separation and roughness effects, so drag can be optimistic.

`F` is the product of Prandtl tip and hub factors:

```text
Ftip = (2/pi)*acos(exp(-(B/2)*(R-r)/(r*abs(sin(phi)))))
Fhub = (2/pi)*acos(exp(-(B/2)*(r-Rhub)/(Rhub*abs(sin(phi)))))
```

The factor geometry is referenced to [NREL/CP-5000-63217](https://docs.nrel.gov/docs/fy15osti/63217.pdf). That report concerns wind turbines; the propeller balance signs here come from the propeller formulation. No calibrated turbine high-load correction is imported as propeller validation.

## Domain guards and sensitivity

The implementation requires positive RPM and advance speed, positive T/Q, `0 <= eta0 < 1`, section angle `0 <= alpha <= 10 degrees`, `0 <= u/Va <= 2`, `0 <= v/(omega*r) <= 0.5`, `Re >= 20,000`, and maximum thickness/chord no greater than 0.12. These are guards for this approximation. They do not establish a certified physical domain or demonstrate turbulence.

Rejected points retain excluded diagnostic estimates separately; accepted performance fields are null and do not enter ranking or ordinary performance plots. Assumption sensitivity scales lift slope by 0.8/1.2 and drag by 0.5/2.0. The resulting range is not a statistical confidence interval.

The baseline radial refinement changes thrust by approximately 0.02384% and torque by 0.02732%, within the declared 1% numerical criterion. Its normalized annular residual is approximately `3.02e-10`. These verify the solution of the selected equations, not their physical closure.

## Dynamics and exclusions

The Simulink model solves `I*domega/dt = Qmotor - Qprop` with a PI controller, motor torque saturation and a lookup of accepted BEM torque. It uses a step in target speed at 8 s and a 20% load increase at 12 s. Under the lowest admitted BEM speed, startup uses `Q = Qmin*(omega/omega_min)^2` as an explicit scenario extrapolation. Windmilling and possible negative torque at positive advance speed are not described by that extrapolation.

The model records table coverage, torque/energy balances, tracking and motor capacity separately. The 1,000 RPM case passes numerical checks but requires 27.60 N·m to hold its final target against a 25 N·m cap. Such an unfavorable scenario outcome is kept.

Cavitation, ventilation, hull wake, skewed inflow, free surface, hub drag, wake contraction, pressure distributions, 3D blade interaction and aeroelastic deformation are outside the demonstrated scope. Skew/rake do not change this axial BEM's solved hydrodynamics. Depth, salinity and pressure entries are retained as scenario metadata, not a cavitation verdict.

The next physical validation step is comparison with relevant section data and open-water measurements, or a separately validated CFD model. Refining annuli cannot replace those data.
