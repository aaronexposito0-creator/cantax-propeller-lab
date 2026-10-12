# Security scope and publication review

This is a local engineering research tool, not an upload service or a sandbox for hostile documents. Run repository-authored scripts and trusted local inputs as an ordinary user. The engineering models are preliminary; numerical correctness and software security do not establish safe marine service.

## Trust boundaries

- Executable paths and configuration are supplied by the local user. Treat a change to those paths as a change to executable code. Do not point the launcher at an untrusted binary.
- The native pipeline opens the project's macro-free `.xlsx` template or a trusted edited copy. It does not promise safe handling of arbitrary downloaded workbooks, STEP files, images or PDFs.
- The pipeline uses command argument lists rather than shell evaluation. It does not run input text through Python `eval`, `exec`, PowerShell `Invoke-Expression` or a remote execution endpoint.
- Excel preflight rejects VBA/XLM, external links, query tables/connections and identified remote-fetch/DDE worksheet formulas. A newly owned COM instance disables macros, events and link updates before opening. These controls supplement Excel's own security; they are not a complete hostile-file parser audit.
- Numerical parameters and units are checked. Output directories remain inside the laboratory; existing run records are preserved. Completed results are retained if the controller is locked or concurrently edited.
- Only a process created by the pipeline is subject to timeout termination. Excel cleanup targets its newly owned instance; it does not quit a pre-existing user instance.
- Project code does not upload geometry, calculations or private files. Separately installed applications can have licensing, update or telemetry behavior governed by their own settings and agreements.

## Dependency finding and remediation

The historical private workflow used `pypdf==6.10.0`. Review on 12 October 2026 found that this version falls in the affected ranges of the upstream [font-data memory-use advisory](https://github.com/py-pdf/pypdf/security/advisories/GHSA-g9cg-prrw-2r8q) and [malformed FlateDecode runtime advisory](https://github.com/py-pdf/pypdf/security/advisories/GHSA-jw7q-gvrg-4vj3), both patched from 6.18.1. The publication gate was stopped when this was identified.

The distribution removes this dependency rather than installing or bundling another PDF parser. Public report creation uses ReportLab; PDF QA uses separately installed Poppler tools on trusted generated reports with bounded subprocess execution. The release audit must confirm that no public runtime import, dependency requirement or executable test requires `pypdf`. Historical original files and installed software remain unchanged.

Static remediation review confirmed that the public `scripts/`, `tests/` and `requirements.txt` contain no `pypdf` requirement/import or `PdfReader` reference. `report.py` tracks pages through the ReportLab callback and runs optional configured Poppler with an argument list and a 180-second timeout. This closes the identified distribution dependency finding at source level; generated report execution, rendered-page review and final publication-content scanning remain separate release checks.

Pillow 12.3.0 is beyond the affected ranges of the identified July 2026 Pillow advisories; see the [upstream release notes](https://pillow.readthedocs.io/en/stable/releasenotes/12.3.0.html). ReportLab 4.4.9 is beyond the affected ranges of the older [XML injection](https://github.com/advisories/GHSA-qpg2-vx7j-3869) and [code execution](https://github.com/advisories/GHSA-9q9m-c65c-37pq) advisories checked. This targeted review is not an exhaustive vulnerability assessment of every installed native application, transitive binary or future dependency version.

## Release controls

The public staging folder is separate from the original laboratory. Personal paths, credentials, tokens, native logs, caches, preferences, local tool settings and unrelated project material are excluded. Selected outputs are checked for textual content and archive/document metadata. No software installation, administrator privilege or runtime redistribution is part of publication. Git publication is limited to the explicitly named destination and does not use force-push.

Use the dependency versions recorded by the release and monitor upstream security advisories when updating. Do not disable Pillow's image-size protections or enable pickle-based loading for untrusted NumPy files. For any future public upload service, native file processing needs resource limits and isolated workers; this local release has not implemented that service.

## Reporting

Report reproducible defects through the repository issue tracker using a minimal synthetic example. Do not attach credentials, customer geometry or private logs. For a sensitive exploitable issue, use the repository's private vulnerability reporting feature if enabled; do not post exploit details or private data in a public issue. A private reporting channel is not asserted to be enabled until configured by the maintainer.
