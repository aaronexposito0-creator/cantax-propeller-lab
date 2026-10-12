# System architecture

CantaX is a file-based local workflow orchestrator. It does not require a ChatGPT session, a cloud calculation service or an MCP server. Each application performs a defined part of the calculation and exchanges explicit engineering files with the next stage.

## Stages and responsibilities

| Stage | Executed by | Inputs | Main outputs |
|---|---|---|---|
| Input validation | Python and Excel COM | Workbook, mapping, material configuration | Case JSON, validated radial table, readback evidence |
| Geometry | FreeCAD embedded Python | Case and candidate family | FCStd, STEP, STL, tessellation, geometry checks |
| Hydrodynamics | MATLAB batch | Case and family | BEM JSON, section loads, curves CSV, figures |
| Shaft dynamics | Simulink | BEM lookup and scenario controls | SLX, time histories, balance and resimulation checks |
| Mesh | Gmsh CLI | Reopened BASE STEP | Two MSH files, volume/topology/quality checks |
| Elastic estimate | CalculiX CLI | Mesh, material, annular loads, speed | INP, solver outputs, reactions, stresses and displacement |
| Independent definitions | Octave and Scilab CLI | MATLAB loads and operating inputs | Recalculated coefficients, power, units and verification JSON |
| Presentation | Python and spreadsheet authoring runtime | Structured results and geometry | Result workbook, figures and PDF |

The public spreadsheet authoring backend uses openpyxl, separately from Excel COM: authoring creates a workbook, while native Excel calculates and inspects it during a full run. The original installation used a different authoring runtime. Its native Excel checks are historical evidence; the public backend has its own packaging and compatibility tests.

## Data contracts

`case.json` contains geometry, operating conditions, selected material, screening constraints, radial station definitions and dynamic scenario settings. `family.json` expands that case into named alternatives. Candidate identifiers join CAD and hydrodynamic results; a missing candidate is an error rather than a guessed match.

Result categories remain separate:

- `cad_results.json`: solid validity, volume, area, bounding box, clipping and format round trips.
- `hydro_results.json`: BASE and alternative estimates, accepted/excluded domains, sensitivities and discretization checks.
- `dynamics_result.json`: numerical checks, tracking, motor capacity and lookup coverage.
- `structure_results.json`: mesh checks, analytical benchmark and BASE-only preliminary elasticity.
- `octave_verification.json` and `scilab_verification.json`: definitions and unit checks against the calculated loads.

Selected historical data is under `examples/verified_runs/`. Those examples are immutable calculation evidence; they are not a command to overwrite the source results or run a solver automatically.

## Units and geometry

Public inputs and calculation records use SI: meters, kilograms, seconds, newtons, newton-meters and watts. Rotational input is explicitly RPM; the calculation uses `n = RPM / 60` and `omega = 2*pi*n`.

FreeCAD builds the solid in millimeters. Reported lengths, areas and volumes are converted by `1e-3`, `1e-6` and `1e-9` respectively. STEP import for meshing explicitly targets meters. STL coordinates use millimeters and must be interpreted accordingly when imported.

The shaft axis is Z. CAD and BEM share the nominal radial distributions and chord normalization. CAD trims the blade tips to the requested diameter; BEM evaluates nominal chord before this trim. The result records that mismatch instead of treating the calculation as surface-resolved CFD.

## Reproducibility and failure behavior

The original full workflow creates a fresh run directory, records input and source snapshots, logs each application invocation and hashes artifacts. It checks numerical and geometric result fields in addition to exit status. A solver failure leaves the failed run available for diagnosis.

The controller publisher does not replace a locked workbook or a workbook changed since its input snapshot. A deferred panel update does not invalidate already calculated outputs. COM operations own their new Excel instance; they do not close a user's existing Excel session or change global Office security.

These behaviors were exercised in the original local installation. The public wrapper and its tests are separately documented in [VERIFICATION.md](VERIFICATION.md); changing runtimes, versions or workbook authoring backends requires new relevant checks.

## Security and privacy boundary

Paths to installed executables belong in a local configuration file, not in committed source. Inputs and output files stay local in the engineering workflow. Commercial applications can independently contact their license services; a local computation workflow is not proof that every vendor application operates offline.

This distribution contains no vendor application binaries, installers, API keys, account configuration or unrelated project documents. Keep generated runs, personal tool-path files, license files and private datasets out of version control.
