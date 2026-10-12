# Installation and execution

The repository distributes source, selected historical results and documentation. It does not include engineering applications, application installers, a licensed runtime or a general-purpose installer. The public package runs independently of the author's personal directories and does not need a ChatGPT session or API key.

## 1. Inspect the saved results

You can read the README, JSON/CSV examples, images and [technical report](cantax-technical-report.pdf) without installing the calculation engines.

To execute the saved-results demonstration, use Python 3.11 or later and the Python dependencies listed in `requirements.txt`; Python 3.12.14 was used for publication checks. Their versions are the versions available for publication testing, not a claim of universal compatibility. In a virtual environment that you control:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python scripts/run_lab.py --demo
```

Installing these dependencies is a user action; the launcher does not silently install software. The demonstration reads `examples/verified_runs/`, checks algebraic consistency and writes a new `runs/demo_*` output directory. It can generate an example workbook using the public spreadsheet backend. **It does not invoke solvers or simulate new engineering results.**

The historical data remains unchanged. This mode is useful for reviewing the data contract and published parameter comparisons without commercial application licenses. It requires neither PowerShell nor native engineering applications. Workbook formulas are written but are **not evaluated by openpyxl**; native Excel recalculation is a separate full-workflow check.

## 2. Prepare a full Windows workflow

Full execution uses the following separately installed tools:

| Dependency | Original tested version | Purpose |
|---|---|---|
| Python | 3.12.14 | Orchestration, mesh/result processing, workbook and report generation |
| PowerShell | 7 | Full-workflow Excel COM operations |
| Excel desktop | 16.0.20430.20146 | Input readback, native recalculation and workbook checks |
| FreeCAD | 1.1.4 | Embedded Python CAD generation |
| MATLAB and Simulink | R2026a Update 2 | BEM, sensitivity and shaft dynamics |
| Gmsh | 4.15.0 | STEP meshing |
| CalculiX | 2.22 | Benchmark and preliminary elasticity |
| GNU Octave | 11.3.0 | Independent definitions and unit checks |
| Scilab | 2026.1.0 | Independent definitions and unit checks |
| Poppler | Optional local tool | PDF rendering for visual QA |

The Python requirements include NumPy, Pillow, openpyxl and ReportLab. Engineering executables are invoked separately; FreeCAD supplies its own embedded Python. No pip package substitutes for Excel, MATLAB, Simulink or the CAD/FEM applications.

Maintain your own licenses and check each application's terms. MATLAB may contact its license service even when engineering calculations and project files remain local. This project does not promise vendor license services work offline.

## 3. Configure local executable paths

Copy the path configuration template, then edit the new local file to match your installation:

```powershell
Copy-Item config/executables.example.json config/executables.local.json
notepad config/executables.local.json
python scripts/run_lab.py --check-tools
```

The template is the authoritative list of accepted tool keys: `powershell`, `freecad`, `matlab`, `octave`, `scilab`, `gmsh`, `calculix` and optional `poppler`. Paths may also be supplied using the matching `CANTAX_<APP>` environment variables, such as `CANTAX_FREECAD` or `CANTAX_POWERSHELL`. `CANTAX_EXECUTABLES` can select a local executable-configuration JSON file. `CANTAX_PYTHON` selects Python for the Windows launcher; otherwise it uses Python on PATH.

`--check-tools` reports executable availability. Availability alone is **not** a successful API, license or calculation test. Run the relevant workflow to establish those capabilities on your machine. The local configuration is ignored by Git because it can contain personal paths.

## 4. Create inputs and run

```powershell
python scripts/run_lab.py --create-input
```

Open the generated `CantaX_Propeller_Lab.xlsx`. Edit the documented input cells in the Control and Radial sheets, save and close Excel, then run:

```powershell
python scripts/run_lab.py --run
```

The controller workbook must be inside this repository's working directory. For a separate controller copy inside the repository:

```powershell
python scripts/run_lab.py --run --workbook examples/my-controller.xlsx
```

For the two parameter-change scenarios used in the historical verification:

```powershell
python scripts/run_lab.py --run --rpm 1000 --no-update-panel
python scripts/run_lab.py --run --rpm 900 --blades 5 --pitch-ratio 0.85 --no-update-panel
```

The commands perform real calculations when all required tools are available. They do not silently use saved results after a solver fails. They should start from the same baseline controller if you want to compare directly with the published examples.

To compare one BASE case plus 12 diameter/blade/pitch variants:

```powershell
python scripts/run_lab.py --run --diameter-sweep
```

The Windows entry point is `Start_CantaX.bat`; its menu uses Python, so the saved demonstration does not require PowerShell. Full calculations still require Windows, PowerShell 7 and the relevant native applications. Command-line use makes the selected operation explicit and is suitable for recording a demonstration.

## Outputs and controller handling

Each calculation gets a fresh folder in `runs/`. It preserves inputs and logs and produces structured results, generated models, solver files, figures, Excel results and a PDF when the required stages complete. Retain the entire run for reproducibility; publishing only an attractive image loses the underlying checks.

Save and close your controller before execution. If a result cannot replace the controller because it is open or changed, the update is deferred and the result draft is preserved. Do not close other users' Excel instances or bypass file sharing restrictions to force publication.

The PDF generator can produce a valid file without proving its visual layout. Inspect the rendered pages, labels, tables and scientific limitations before distributing a new report.

## Testing and compatibility

See [VERIFICATION.md](VERIFICATION.md) for the release tests and the distinction between historical full-workflow evidence and saved-data tests. Re-test relevant interfaces after changing application versions, licenses, paths or workbook/runtime implementations.

The original installation and the public distribution use different spreadsheet authoring backends. The release regression exercised the public openpyxl backend through actual Excel recalculation with zero formula errors. That establishes the tested workflow on the reviewed Windows installation; new machines or changed versions still require relevant checks. An engine being detected does not by itself establish a successful full calculation.

## Privacy when publishing new runs

The default `.gitignore` excludes generated runs, local tool paths, environments, temporary files and common credentials. It is a safeguard, not a confidentiality audit. Review inputs, metadata, embedded workbook links, figures and report text before adding your own data to Git.

Never commit proprietary application binaries or installers, vendor license files, personal logs or unrelated engineering work. A license for project-authored code does not grant redistribution rights to third-party dependencies or datasets.
