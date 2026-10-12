# Maintaining this repository

1. Keep local executable paths in ignored `config/executables.local.json` or your environment. Never commit that file, credentials, local run directories or vendor software.
2. Before a change, fetch remote updates and use `git pull --ff-only`. Review unexpected remote work; do not overwrite it or force push.
3. Run `python -m unittest discover -s tests -v` and `python scripts/run_lab.py --demo`. New native adapter or workbook changes need a fresh local native regression with installed applications/licences. Changes to physics require appropriate scientific checks and report inspection.
4. Preserve local old runs. Publish only selected sanitized examples after numerical consistency, metadata, copyright and secret checks. Retain provenance without workstation paths or private logs.
5. Review dependency versions and upstream security advisories before updating requirements. The removed vulnerable pypdf dependency must not be reintroduced without a separate review. Reassess licenses before bundling an interpreter, binding, binary or container.
6. Rebuild reports from the reviewed data; verify actual rendering and hyperlinks. Do not replace rejected or unfavorable model outcomes with successful-looking figures.
7. Stage explicit release files, inspect `git diff --cached --stat` and the complete staged file list, then commit and use normal `git push origin main`. Verify the public README, linked images and report after pushing.

LinkedIn files remain drafts. Review the repository, numbers, claims and rights before posting them manually. No social-network publication is automated by this project.
