# Publication license audit

Audit date: 12 October 2026. Scope: this separate public distribution folder. The original local engineering laboratory is preserved independently.

## Release decision and license scope

MIT is appropriate for the project's original implementation, documentation and author-provided demonstration material, subject to the third-party boundaries described in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). The top-level license grants only rights held by the project contributors. It does not assert ownership of engineering applications, scientific publications, supplier data, trademarks or fonts.

The inspected source consists of original orchestration, parametric geometry, numerical model implementations, verification scripts, report/workbook generation and local application adapters. Manual review found no vendored third-party library, copied solver implementation or vendor example model in the selected source. AI assisted implementation; provenance review and numerical checks are recorded separately. This review does not certify every possible intellectual-property claim or create rights the publisher does not hold.

Gmsh and CalculiX are separate processes exchanging ordinary geometry and solver input/output files. Octave and Scilab execute original script files. FreeCAD exposes its installed LGPL Python environment. These integration boundaries support publishing the original source without distributing or relicensing the applications. A future embedded interpreter, copied binding, solver DLL, plugin, container or standalone binary would change this review and must not be inferred to be covered by it.

## Allowed and excluded material

| Material | Decision | Conditions |
|---|---|---|
| Original `.py`, `.m`, `.sce`, `.ps1` and launcher sources | Include | Preserve attribution; no installation-specific personal path or private credential. |
| Original config, synthetic example inputs and selected calculated tables | Include | Keep units, numerical provenance, source citations and preliminary classification. |
| Project-generated CAD images, plotted results and publication report | Include | Review visible content and metadata; report must not carry private paths or font files. |
| Generated STEP/FCStd/STL and selected solver/model examples | Include only if selected and inspected | User-generated engineering output, no third-party proprietary model/template; strip file creator, path and application metadata that expose personal information. |
| Supplier datasheets, journal PDFs, reference illustrations and vendor manuals | Exclude | Link to originals; no redistribution authorization assumed. |
| MATLAB/Simulink/Excel/Inventor installers, binaries, runtimes or vendor source/examples | Exclude | Recipients install under their own licenses. |
| FreeCAD/Gmsh/CalculiX/Octave/Scilab/Poppler binaries and source distributions | Exclude | Obtain upstream; future redistribution requires full component notices and applicable source obligations. |
| Python packages, wheels, native libraries, virtual environments and `node_modules` | Exclude | Requirements identify externally installed dependencies, not bundled copies. |
| `@oai/artifact-tool`, Codex runtime bundles, skill source and authoring markers | Exclude | No rights assumed for redistribution; not needed by the public builder. |
| Arial/other Windows font files | Exclude | Public PDF uses standard unembedded PDF fonts. |
| Historical `pypdf==6.10.0` runtime requirement | Exclude | Applicable 2026 resource-exhaustion advisories discovered; dependency must be absent before publication. |
| Original raw run folders, native logs, preferences, caches, usernames, private source snapshots and other projects | Exclude | Publish selected sanitized evidence only. |

## License evidence

The component matrix and primary-source links are in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Official FreeCAD, Gmsh, CalculiX, Octave and Scilab license information was checked. NumPy, Pillow, openpyxl and ReportLab licensing was checked against official maintainer sources; ReportLab's installed 4.4.9 license was also read. MathWorks User Files distribution conditions were checked in the installed R2026a agreement and [official Program Offering Guide](https://www.mathworks.com/help/pdf_doc/offering/offering.pdf). MATLAB/Simulink and Excel remain licensed user prerequisites rather than supplied products.

Source equations and a few attributed factual material properties are represented as project implementations/reference inputs. No reference publication or material database is copied. No naval classification, vendor endorsement, commercial-use entitlement or certification is implied.

## Publication gates

The license review permits publication only after the release audit confirms all of the following:

1. The staging set contains only the selected source, documentation and sanitized project outputs.
2. No vendor/library/runtime/font binary, external proprietary model or reference PDF is tracked.
3. Public code and dependency files contain no import or requirement for the removed vulnerable `pypdf` component.
4. The public report contains no embedded Windows font program and no private path; its provenance and real numerical results remain accurate.
5. Secrets/private-path scans, file review and applicable executable verification pass. Security findings must be resolved before push.
6. Future changes to copied code, bundled dependencies, hosting or commercial packaging trigger a new license review.

The review covers this source distribution. It does not approve a future commercial packaged product, cloud service, installer or proprietary solver redistribution.
