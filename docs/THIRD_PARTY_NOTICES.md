# Third-party notices and distribution boundaries

Reviewed on 12 October 2026. The repository distributes CantaX source, documentation and selected demonstration outputs. It does **not** distribute engineering applications, their runtimes, Python packages, operating-system components, vendor examples or font files. The project MIT license does not relicense these external products.

## Engineering applications

| Component | Demonstrated version | License / primary source | Relationship to this repository |
|---|---|---|---|
| FreeCAD | 1.1.4 | [FreeCAD LGPL license text](https://github.com/FreeCAD/FreeCAD/blob/main/LICENSE) and [component licensing explanation](https://github.com/FreeCAD/FreeCAD-documentation/blob/main/wiki/License.md) | Original Python script runs inside a separately installed FreeCAD. No FreeCAD/OCC source or libraries are copied. Generated CAD is project output. |
| Gmsh | 4.15.0 | [GPL 2 or later, with specific linking exceptions](https://gmsh.info/doc/texinfo/#License) | A standalone executable receives a generated `.geo` file and STEP geometry. No Gmsh Python binding, DLL or executable is distributed. |
| CalculiX CrunchiX | 2.22 | [GPL 2 or later](https://www.calculix.de/) | A standalone executable reads original finite-element input decks. No solver source or binary is distributed. |
| GNU Octave | 11.3.0 | [GPL 3 or later](https://octave.org/copyright/) | Separately installed interpreter executes the project's original verification script. No `.oct` extension or embedded interpreter is supplied. |
| Scilab | 2026.1.0 | [GPL 2.0](https://www.scilab.org/about/scilab-open-source-software) | Separately installed interpreter executes an original verification script. No Scilab code, module or runtime is supplied. |
| MATLAB and Simulink | R2026a Update 2 | [MathWorks Program Offering Guide](https://www.mathworks.com/help/pdf_doc/offering/offering.pdf) | Licensed local applications execute original `.m` scripts and programmatically construct the shaft-control model. No MATLAB toolbox code, example model, installer, runtime or compiled application is supplied. |
| Microsoft Excel | Local desktop installation | [Microsoft licensing documents](https://www.microsoft.com/licensing/docs/view/Licensing-Use-Terms) | COM automates a separately licensed local Excel instance. The project workbook is original user content. No Office component is supplied. |

MATLAB's User Files provision permits distribution of qualifying original code and models, subject to the license offering and general agreement. It does not grant rights to redistribute MATLAB source or its libraries. The installed R2026a agreement was inspected at its Deployment Rights for User Files section. Recipients need their own eligible MATLAB/Simulink and Excel licenses. Publication is a source demonstration, not a sublicensed commercial application or a guarantee that every academic/home license permits every future use.

The Gmsh copyright holders are Christophe Geuzaine and Jean-François Remacle. For engineering use, cite C. Geuzaine and J.-F. Remacle, *Gmsh: a three-dimensional finite element mesh generator with built-in pre- and post-processing facilities*, International Journal for Numerical Methods in Engineering 79(11), 1309–1331 (2009), as requested by the [Gmsh manual](https://gmsh.info/doc/texinfo/#Obtaining-Gmsh).

## Python and rendering dependencies

These are requirements obtained independently by the recipient, not vendored copies. Consult the exact installed distribution for its complete notices and bundled-library licenses before creating a future packaged executable.

| Component | Version used | Upstream license | Source |
|---|---|---|---|
| Python | See installation guide | PSF License 2 and incorporated-component notices | [Python license](https://docs.python.org/3/license.html) |
| NumPy | 2.3.5 | BSD 3-Clause | [NumPy license](https://numpy.org/doc/stable/license.html) |
| Pillow | 12.3.0 | MIT-CMU; wheel components have their own notices | [Pillow license](https://pillow.readthedocs.io/en/stable/about.html#license) |
| openpyxl | 3.1.5 | MIT | [Maintainer-published package metadata](https://pypi.org/project/openpyxl/3.1.5/) |
| ReportLab open-source toolkit | 4.4.9 | BSD; the installed license contains three conditions | [ReportLab licensing FAQ](https://docs.reportlab.com/developerfaqs/#13-licensing) |
| et-xmlfile | Installed dependency of openpyxl | MIT | [Maintainer-published package](https://pypi.org/project/et-xmlfile/) |
| charset-normalizer | Installed dependency of ReportLab | MIT | [Upstream license](https://github.com/jawah/charset_normalizer/blob/master/LICENSE) |
| PowerShell 7 | See installation guide | MIT; external .NET/native components retain their licenses | [PowerShell license](https://github.com/PowerShell/PowerShell/blob/master/LICENSE.txt) |
| Poppler utilities | Optional local PDF QA tool | GPL; check the exact build's component notices | [Official project](https://poppler.freedesktop.org/) and its [maintainer-linked source mirror license](https://github.com/tsdgeos/poppler_mirror/blob/master/COPYING) |

Poppler is executed as a separate local utility. There is no Python Poppler binding or bundled Poppler binary. ReportLab PLUS, `rlextra` and `pyRXP` are not requirements of this project.

`pypdf` was used in the historical private workflow, but is excluded from the public runtime after the security review identified applicable dependency advisories. The historical `@oai/artifact-tool` workbook authoring module, its Node runtime/cache, skill scripts and all Codex runtime bundles are excluded. The public workbook builder is separate original Python code using openpyxl.

## Scientific references and material data

The project independently implements numerical formulas; citations do not convey a license to copy reference software or documentation. No BladeAD, NREL, NASA, ITTC, PDAS, MathWorks example or third-party solver source is included. Refer to the model bibliography for the underlying BEM, thin-foil lift, friction line and loss-factor references. The custom closed trailing edge is identified as a geometry adaptation, not an unchanged reference airfoil.

Material configuration stores a small number of attributed factual reference values and SI conversions. It does not include supplier PDFs, tables, artwork or material certificates. Sources remain [Copper Development Association C95800](https://alloys.copper.org/alloy/C95800), [Outokumpu product references](https://www.outokumpu.com/en/products) and [Hydro alloy references](https://www.hydro.com/en/products-and-services/extruded-profiles/). Typical properties are not service allowables. Third-party reference documents and databases retain their original rights.

## Images, documents and trademarks

The displayed propellers and performance plots originate from this project's CAD tessellations and computed data. They are not vendor promotional artwork. No application logo is copied. Product names identify dependencies and do not imply endorsement by their developers.

Selected FCStd and STEP models contain this project's own geometry. FreeCAD's [Files licensing explanation](https://github.com/FreeCAD/FreeCAD-documentation/blob/main/wiki/License.md#files) explicitly separates generated models from the application license. The [GNU GPL output explanation](https://www.gnu.org/licenses/gpl-faq.en.html#WhatCaseIsOutputGPL) likewise distinguishes data-derived output from copied program content. Public native CAD metadata must declare the chosen project license consistently; default “All rights reserved” document metadata is not silently treated as an MIT declaration. The generated FCStd is an editable solid; the regeneration recipe and inputs define its parameters.

The public report uses standard PDF font names and does not package Windows Arial font software. Raster images may contain rendered text. Microsoft distinguishes rendered content and permitted document embedding from font-file redistribution in its [font redistribution FAQ](https://learn.microsoft.com/en-us/typography/fonts/font-faq). The repository grants no rights to third-party typefaces.

Inventor, ParaView and DWSIM are documented as unverified or pending integrations. They contribute no distributed code, binary or result to this release. Adding them or any new bundled component requires another rights and security review.
