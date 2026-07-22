# File Enumerator

A dependency-free command-line utility for recursively inventorying filesystem
files and supported archive members with include and exclude filters. The
primary Linux/Fedora command is `file-enumerator`; the original PowerShell
implementation is retained under `contrib/windows/`.

## Features

- Recursive enumeration beneath a requested root directory.
- Automatic member listing for supported ZIP and TAR-family archives.
- Archived entries are clearly marked in TXT and CSV output.
- Include or exclude file extensions, filename globs, and folder globs.
- Filters apply to both normal files and files stored inside archives.
- TXT, CSV, or combined output.
- Optional ZIP or ZIP-only output.
- Case-insensitive matching by default, with an explicit case-sensitive mode.
- Directory symlinks are not followed by default.
- Output files are excluded from their own scan.
- Every failure is printed to stderr and written to a timestamped error log.
- Exit status distinguishes complete success, fatal errors, and partial reads.
- Proper man page and Bash completion.
- Source install and uninstall targets.
- Fedora RPM spec.
- Standard-library-only Python implementation.

## Archive support

Archive traversal is enabled by default and does not extract files.

Supported formats:

- ZIP and common ZIP containers: `.zip`, `.jar`, `.war`, `.ear`, `.whl`,
  `.apk`, `.xpi`, and `.epub`
- TAR and compressed TAR: `.tar`, `.tar.gz`, `.tgz`, `.tar.bz2`, `.tbz`,
  `.tbz2`, `.tar.xz`, and `.txz`

Known archive formats that cannot be read by the dependency-free backend, such
as `.7z`, `.rar`, `.cab`, `.iso`, and `.tar.zst`, are reported as failures
rather than silently skipped. Nested archive files are listed as archive
members but are not recursively opened.

Use `--no-archives` when only filesystem entries are wanted.

The archive functionality described here applies to the primary Linux/Python
command. The retained PowerShell script has not yet been brought to archive
feature parity.

## Fedora installation

```bash
sudo dnf install python3 make man-db bash-completion
./scripts/install.sh
hash -r
file-enumerator --version
man file-enumerator
```

See [docs/INSTALL.md](docs/INSTALL.md) for per-user installation, staged
validation, RPM building, and uninstall instructions.

To publish or update the public GitHub repository from an authenticated
workstation, run `scripts/publish-github.sh`. The script refuses dirty working
trees, unexpected branches, mismatched remotes, and non-public repositories.

## Examples

Basic TXT and CSV inventory, including supported archive members:

```bash
file-enumerator /backup/Downloads
```

Only PDF and DOCX files, including matching files inside archives, while
excluding temporary files and common dependency folders:

```bash
file-enumerator /backup/Downloads \
  --include-filetype pdf,docx \
  --exclude-filename '~$*' \
  --exclude-filename '*.tmp' \
  --exclude-foldername '.git,node_modules,__pycache__' \
  --format both
```

Create only a ZIP archive of the generated inventory reports:

```bash
file-enumerator /backup/Downloads \
  --output-dir /backup/inventory-output \
  --basename downloads_inventory \
  --txt-path-mode relative \
  --zip-only
```

Disable archive traversal:

```bash
file-enumerator /backup/Downloads --no-archives
```

Use `file-enumerator --help` for command help and `man file-enumerator` for the
complete manual.

## Filter behaviour

- Exclusions always win.
- Values within one category are OR.
- Different include categories are AND.
- Filename and folder patterns accept `*`, `?`, and character ranges.
- Folder patterns match either one component or the relative folder path.
- Archives act as virtual folders, so folder filters can match paths inside them.
- Use `<none>` as a filetype to match files without an extension.
- Excluded filesystem folders are pruned and never scanned.
- Filtering an archive container does not prevent its members from being
  evaluated; use `--no-archives` to disable member traversal entirely.

## Output

TXT output contains a metadata header followed by one full or relative path per
line. Archive members are prefixed with `[ARCHIVED]` and use this virtual path
form:

```text
[ARCHIVED] archives/sample.zip::docs/report.pdf
```

CSV columns:

- `relative_path`
- `full_path`
- `name`
- `extension`
- `parent_relative`
- `size_bytes`
- `modified_utc`
- `is_symlink`
- `is_archived`
- `archive_path`
- `archive_member_path`
- `archive_format`

ZIP member timestamps are left blank because the ZIP format does not reliably
store a timezone. TAR member timestamps are emitted in UTC when available.

## Failure logging

Every filesystem, archive, argument, or fatal runtime failure is printed to
stderr. When one or more failures occur, the program also writes:

```text
file_enum_YYYYMMDD_HHMMSS_microseconds_errors.txt
```

The error log is written to `--output-dir`. If that location cannot be used, the
program attempts to write it in the current directory. `--quiet` never suppresses
errors. With `--zip-only`, the error log is included in the ZIP and also retained
as a loose file.

Exit codes:

- `0`: success
- `1`: fatal setup, argument, or output error
- `2`: inventory output created, but one or more paths or archives failed

## Development

```bash
make test
make verify
make dist
```

`make verify` syntax-checks the program, runs the test suite, renders the man
page when `groff` is available, builds release archives, and verifies their
checksums.

## Repository layout

```text
src/file-enumerator                 Linux/Python executable
man/file-enumerator.1               manual page
completions/file-enumerator.bash    Bash completion
packaging/rpm/file-enumerator.spec  Fedora RPM metadata
scripts/                            install and uninstall helpers
tests/                              standard-library unittest suite
contrib/windows/                    PowerShell implementation
docs/INSTALL.md                     installation and rollback guide
```

## Support

File Enumerator is free and open source. To support continued development, use
[Buy Me a Coffee](https://buy.stripe.com/test_fZu5kE3kTeBqeBzglQao800).

## License

Released under the [MIT License](LICENSE).
