# Verification and evidence

Verification means that the implemented equations, file exchanges and tested integrations behaved consistently under declared checks. It is distinct from experimental validation, independent human approval, manufacturing readiness and certification.

## Historical full workflows

The original Windows installation executed the following four workflows. Curated data is stored under `examples/verified_runs/` without personal paths or private logs.

| Public example | Changed inputs | Verified response |
|---|---|---|
| `baseline` | D 0.300 m, B=4, P/D 0.80, 900 RPM | Reference geometry, BEM, dynamics, mesh, BASE elasticity, workbook and report |
| `rpm_1000` | 900 → 1,000 RPM | Changed loads and dynamics; identical geometry signature and volume |
| `five_blades` | B=4 → 5, P/D 0.80 → 0.85, 900 RPM | Different CAD/mesh/result hashes and 10.451% lower volume/mass |
| `diameter_study` | BASE plus 12 D/B/P-D alternatives | 13 designs, two perturbed diameters, three blade counts and two perturbed pitch ratios |

The RPM test was launched after removing AI-session-related environment variables. It required no ChatGPT conversation or API key. It still required the local installed applications and runtimes; that test is not a commercial portability or vendor-offline-licensing claim.

## Checks by subsystem

| Subsystem | Evidence and original acceptance scope |
|---|---|
| Excel input | Native COM read, save/reopen readback of changed cells, parameter bounds and radial table validation |
| CAD | One valid closed positive-volume solid per candidate, no blade overlap outside hub, diameter bound |
| Format exchange | FCStd and STEP reopen; volume relative discrepancy ≤`1e-4`, bounding-box tolerance checked |
| BEM solve | Both normalized annular residuals <`1e-5`; explicit accepted-domain guards |
| BEM discretization | 60 → 120 annuli; thrust/torque change <1% |
| Independent definitions | Octave and Scilab check J, KT, KQ, P and efficiency from common loads; relative tolerance `1e-8`, absolute `1e-10` |
| Mesh | Meter-scale import, volume discrepancy ≤5%, no inverted/degenerate tetrahedra or non-manifold faces |
| Solver benchmark | C3D8 cube analytical extension/stress/reaction; relative tolerance `1e-5` |
| Propeller elasticity | Recorded actual reaction force and moment; relative balance tolerance `1e-3` |
| Dynamics | Torque and energy balances, lookup coverage, SLX save/reopen/resimulation |
| Excel results | Four historical final workbooks natively recalculated; zero formula errors |
| Presentation | Original PDF pages and calculation figures rendered and visually inspected |

The original Excel controller also exercised input freshness after RPM/chord edits, file locks, deferred replacement and concurrent controller edits. These are integration behaviors, not hydrodynamic validation.

## Representative baseline evidence

The baseline produced `J = 0.4444444444`, `KT = 0.1875467144`, `KQ = 0.02418792420`, thrust 350.348984 N, torque 13.555366 N·m and power 1,277.563170 W. Its volume was `0.0003564570746956503 m³`, giving 2.723332 kg at the declared reference density.

The BEM residual was approximately `3.02e-10`. Radial refinement changed thrust by 0.02384% and torque by 0.02732%. Octave and Scilab recalculate definitions from MATLAB's common loads; their agreement is algebraic/unit verification, not an independent physical model of the propeller.

An ideal full actuator-disk check gives an optimistic minimum power of approximately 998.05 W for the baseline thrust and advance speed. The BEM estimate exceeds that bound. This elementary consistency check does not calibrate the model or establish physical accuracy.

The baseline Simulink run had approximately 0.1072% relative energy-balance error. Reopening and resimulating the embedded-workspace SLX produced zero recorded difference. The BASE elastic model gave approximately 35.42 µm maximum displacement and 16.93 MPa von Mises stress, with the limitations in [STRUCTURAL_ANALYSIS.md](STRUCTURAL_ANALYSIS.md).

## Keep scenario outcomes separate from integration success

At 1,000 RPM, the later speed/load step requires about 27.60 N·m against a 25 N·m motor cap. Final speed is about 1,057.54 RPM against a 1,100 RPM target. The numerical model passes its checks while reporting insufficient motor capacity.

For five blades/P-D 0.85, the requested final steady torque is about 25.18 N·m. It is also capacity-limited despite tracking close to the 990 RPM target. A successful executable run must not hide these unfavorable outcomes.

## Public-package tests

Use the repository tests and the saved-results demonstration to audit the public distribution:

```powershell
python -m unittest discover -s tests -v
python scripts/run_lab.py --demo
```

Saved-data tests detect malformed examples, coefficient inconsistencies and packaging errors. They do not repeat FreeCAD, MATLAB, Excel or FEM execution. A successful saved demo must never be reported as a new full engineering run.

The public wrapper's packaging check passed 12 unit tests and Python compilation. Its actual saved demo checked four historical cases, 260 algebraic identities and 52 historical geometry records. The resulting workbook contains formulas that require Excel to evaluate; creating it is not evidence of native recalculation or a new CAD solve.

## Fresh public-source execution

The public distribution completed a new baseline workflow using the installed Windows engineering applications. All ten orchestration stages exited successfully, with the structured checks confirming native Excel input readback, 13 FreeCAD solids and round trips, MATLAB BEM, a real Simulink SLX saved/reopened/resimulated with zero recorded difference, two Gmsh meshes, the CalculiX benchmark and BASE elasticity, Octave and Scilab checks, workbook generation, native Excel verification and PDF generation.

The public openpyxl result workbook was opened and recalculated by Excel: zero formula errors, 25 validated input cells and a current-results panel. This exercises the publication backend separately from the original authoring implementation.

The generated run PDF had 11 pages. Visual review found two presentation details: fragmented material-property labels and a reference to an original documentation filename. The report source was corrected and only the report was regenerated from saved calculation files. All 171 non-presentation files in the original run manifest were checked unchanged. Pages 1, 9 and 11 were visually rechecked; the other eight rendered PNG pages were byte-identical to the already inspected renders. Final run-report visual QA passed.

The separate eight-page English public report was also inspected page by page. Its [QA record](PUBLICATION_QA.json) identifies the PDF hash and rendered-page hashes. The [release execution record](../examples/PUBLIC_RELEASE_VERIFICATION.json) provides sanitized evidence of the fresh native workflow. Neither report review establishes independent human approval or physical validation.

The parameter-change A/B tests and diameter-study C remain preserved historical evidence; their unchanged calculations were not rerun solely for packaging. The fresh regression covers the baseline public-source pipeline and its new workbook backend. It used the existing reviewed Windows installation; compatibility on a clean installation or with other application versions has not been established.

## Human review and future results

The project was implemented with AI assistance. Recorded numerical checks and visual inspections are available, but no independent human validation of the physical models is claimed. Human review of source, evidence, rights and professional communication remains the author's responsibility.

New operating conditions require new acceptance checks and report inspection. A historic PASS applies to the recorded files and declared models; it does not automatically apply to modified inputs, later software versions or manufacturing decisions.
