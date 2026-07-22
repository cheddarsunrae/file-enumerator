# Changelog

## 1.1.1 — 2026-07-21

- Released the project publicly under the MIT License.
- Replaced the private-repository publisher with a guarded public-repository
  publisher.
- Updated Fedora packaging metadata and documentation for the public release.

## 1.1.0 — 2026-07-21

- Added default, non-extracting member enumeration for ZIP and TAR-family
  archives.
- Marked archive members with `[ARCHIVED]` in TXT output and added explicit
  archive metadata columns to CSV output.
- Applied filetype, filename, and folder filters inside archives.
- Added `--no-archives` to disable archive traversal.
- Added timestamped `file_enum_*_errors.txt` logs for partial and fatal failures.
- Made every failure print to stderr even when `--quiet` is used.
- Kept error logs loose under `--zip-only` while also including them in the ZIP.
- Added archive, filtering, fatal-error, and error-log regression coverage.

## 1.0.0 — 2026-07-21

- Added the installed `file-enumerator` Linux command.
- Added `--version` support.
- Added a complete section 1 man page.
- Added Bash completion.
- Added source install and uninstall workflows with `PREFIX` and `DESTDIR`.
- Added a Fedora noarch RPM spec.
- Added regression tests for filtering, extensionless files, CSV/TXT output,
  ZIP-only output, version reporting, and output self-exclusion.
- Retained the Windows PowerShell implementation under `contrib/windows/`.
