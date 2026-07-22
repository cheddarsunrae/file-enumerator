#!/usr/bin/env python3
from pathlib import Path


def read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    Path(path).write_text(text, encoding="utf-8")


def replace_once(path: str, old: str, new: str) -> None:
    text = read(path)
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected one occurrence, found {count}: {old[:80]!r}")
    write(path, text.replace(old, new, 1))


def insert_before(path: str, marker: str, addition: str) -> None:
    text = read(path)
    count = text.count(marker)
    if count != 1:
        raise RuntimeError(f"{path}: expected one marker, found {count}: {marker!r}")
    write(path, text.replace(marker, addition + marker, 1))


# Version metadata.
replace_once("VERSION", "1.2.0\n", "1.2.1\n")
replace_once("src/file-enumerator", 'VERSION = "1.2.0"', 'VERSION = "1.2.1"')
replace_once(
    "tests/test_file_enumerator.py",
    'self.assertEqual(result.stdout.strip(), "file-enumerator 1.2.0")',
    'self.assertEqual(result.stdout.strip(), "file-enumerator 1.2.1")',
)

# Simple output path and archive-exclusion alias.
replace_once(
    "src/file-enumerator",
    '    parser.add_argument("root", help="Root folder to enumerate")\n',
    '    parser.add_argument("root", help="Root folder to enumerate")\n'
    '    parser.add_argument(\n'
    '        "-o",\n'
    '        "--output",\n'
    '        metavar="FILE",\n'
    '        help="Write one report to this exact .txt or .csv path",\n'
    '    )\n',
)
replace_once(
    "src/file-enumerator",
    '    parser.add_argument(\n'
    '        "--format", choices=("txt", "csv", "both"), default="both"\n'
    '    )\n'
    '    parser.add_argument(\n'
    '        "--output-dir", default=".", help="Directory for generated output"\n'
    '    )\n',
    '    parser.add_argument(\n'
    '        "--format",\n'
    '        choices=("txt", "csv", "both"),\n'
    '        default=None,\n'
    '        help="Advanced mode output format; defaults to both",\n'
    '    )\n'
    '    parser.add_argument(\n'
    '        "--output-dir",\n'
    '        default=None,\n'
    '        help="Advanced mode directory for generated output",\n'
    '    )\n',
)
replace_once(
    "src/file-enumerator",
    '    parser.add_argument(\n'
    '        "--no-archives",\n'
    '        action="store_true",\n'
    '        help="Do not inspect supported archives for member filenames",\n'
    '    )\n',
    '    parser.add_argument(\n'
    '        "--exclude-archives",\n'
    '        "--no-archives",\n'
    '        dest="exclude_archives",\n'
    '        action="store_true",\n'
    '        help="Do not inspect archives for member filenames",\n'
    '    )\n',
)
replace_once(
    "src/file-enumerator",
    "            if not args.no_archives:\n",
    "            if not args.exclude_archives:\n",
)
replace_once(
    "src/file-enumerator",
    "    output_dir = Path.cwd()\n",
    "    output_dir = Path.cwd()\n    output_path: Optional[Path] = None\n",
)
replace_once(
    "src/file-enumerator",
    '''        args = parser.parse_args()
        if args.zip_only:
            args.zip = True

        root = Path(args.root).expanduser().resolve()
        output_dir = Path(args.output_dir).expanduser().resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        basename = args.basename or f"file_inventory_{timestamp}"
        if Path(basename).name != basename:
            raise CLIUsageError("--basename must be a file name, not a path")

        error_log_path = output_dir / f"file_enum_{error_timestamp}_errors.txt"
        prospective_outputs = {
            output_dir / f"{basename}.txt",
            output_dir / f"{basename}.csv",
            output_dir / f"{basename}.zip",
            error_log_path,
        }
''',
    '''        args = parser.parse_args()
        root = Path(args.root).expanduser().resolve()

        if args.output:
            conflicts: list[str] = []
            if args.format is not None:
                conflicts.append("--format")
            if args.output_dir is not None:
                conflicts.append("--output-dir")
            if args.basename is not None:
                conflicts.append("--basename")
            if args.zip:
                conflicts.append("--zip")
            if args.zip_only:
                conflicts.append("--zip-only")
            if conflicts:
                raise CLIUsageError(
                    "-o/--output cannot be combined with " + ", ".join(conflicts)
                )

            output_path = Path(args.output).expanduser()
            if not output_path.is_absolute():
                output_path = Path.cwd() / output_path
            output_path = output_path.resolve()
            output_suffix = output_path.suffix.casefold()
            if output_suffix not in {".txt", ".csv"}:
                raise CLIUsageError("-o/--output must end in .txt or .csv")
            if output_path.exists() and output_path.is_dir():
                raise CLIUsageError("-o/--output must name a file, not a directory")

            output_dir = output_path.parent
            output_dir.mkdir(parents=True, exist_ok=True)
            output_format = output_suffix[1:]
            basename = output_path.stem
        else:
            if args.zip_only:
                args.zip = True
            output_dir = Path(args.output_dir or ".").expanduser().resolve()
            output_dir.mkdir(parents=True, exist_ok=True)
            output_format = args.format or "both"
            basename = args.basename or f"file_inventory_{timestamp}"
            if Path(basename).name != basename:
                raise CLIUsageError("--basename must be a file name, not a path")

        error_log_path = output_dir / f"file_enum_{error_timestamp}_errors.txt"
        prospective_outputs = {error_log_path}
        if output_path is not None:
            prospective_outputs.add(output_path)
        else:
            prospective_outputs.update(
                {
                    output_dir / f"{basename}.txt",
                    output_dir / f"{basename}.csv",
                    output_dir / f"{basename}.zip",
                }
            )
''',
)
replace_once(
    "src/file-enumerator",
    '''        if args.format in {"txt", "both"}:
            txt_path = output_dir / f"{basename}.txt"
            write_txt(txt_path, records, root, args.txt_path_mode, generated_utc)
            generated_files.append(txt_path)

        if args.format in {"csv", "both"}:
            csv_path = output_dir / f"{basename}.csv"
            write_csv(csv_path, records)
            generated_files.append(csv_path)
''',
    '''        if output_format in {"txt", "both"}:
            txt_path = (
                output_path
                if output_path is not None and output_format == "txt"
                else output_dir / f"{basename}.txt"
            )
            write_txt(txt_path, records, root, args.txt_path_mode, generated_utc)
            generated_files.append(txt_path)

        if output_format in {"csv", "both"}:
            csv_path = (
                output_path
                if output_path is not None and output_format == "csv"
                else output_dir / f"{basename}.csv"
            )
            write_csv(csv_path, records)
            generated_files.append(csv_path)
''',
)

# Regression tests for the simple path, default archive traversal, and alias.
tests = '''
    def test_simple_output_path_includes_archives_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = self.make_fixture(base)
            self.add_archive_fixtures(root)
            output = base / "files.txt"
            result = self.run_program(
                str(root),
                "-o",
                str(output),
                "--txt-path-mode",
                "relative",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(output.is_file())
            self.assertFalse((base / "files.csv").exists())
            text = output.read_text(encoding="utf-8")
            self.assertIn("[ARCHIVED] archives/sample.zip::docs/inside.PDF", text)
            self.assertIn("[ARCHIVED] archives/sample.tar.gz::nested/report.txt", text)

    def test_exclude_archives_alias_omits_archive_members(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = self.make_fixture(base)
            self.add_archive_fixtures(root)
            output = base / "files.txt"
            result = self.run_program(
                str(root),
                "-o",
                str(output),
                "--exclude-archives",
                "--txt-path-mode",
                "relative",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            text = output.read_text(encoding="utf-8")
            self.assertNotIn("[ARCHIVED]", text)
            self.assertIn("archives/sample.zip", text)
            self.assertIn("archives/sample.tar.gz", text)

    def test_simple_output_rejects_advanced_output_options(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = self.make_fixture(base)
            output = base / "files.txt"
            result = self.run_program(
                str(root),
                "-o",
                str(output),
                "--format",
                "txt",
                cwd=base,
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("-o/--output cannot be combined with --format", result.stderr)
            self.assertFalse(output.exists())

'''
insert_before("tests/test_file_enumerator.py", '\n\nif __name__ == "__main__":', tests)

# Bash completion.
replace_once(
    "completions/file-enumerator.bash",
    '        --output-dir)\n            COMPREPLY=( $(compgen -d -- "$cur") )\n            return 0\n            ;;\n',
    '        -o|--output)\n            COMPREPLY=( $(compgen -f -- "$cur") )\n            return 0\n            ;;\n'
    '        --output-dir)\n            COMPREPLY=( $(compgen -d -- "$cur") )\n            return 0\n            ;;\n',
)
replace_once(
    "completions/file-enumerator.bash",
    '            --format --output-dir --basename --txt-path-mode\n'
    '            --zip --zip-only --no-archives --follow-links --case-sensitive --quiet\n',
    '            -o --output --format --output-dir --basename --txt-path-mode\n'
    '            --zip --zip-only --exclude-archives --no-archives\n'
    '            --follow-links --case-sensitive --quiet\n',
)

# README: make the simple interface primary while keeping advanced compatibility.
replace_once(
    "README.md",
    "- TXT, CSV, or combined output.\n",
    "- Simple exact-file output with `-o/--output`, plus advanced TXT/CSV/ZIP modes.\n",
)
replace_once(
    "README.md",
    "Use `--no-archives` when only filesystem entries are wanted.\n",
    "Use `--exclude-archives` when only filesystem entries are wanted. The older\n"
    "`--no-archives` spelling remains available as a compatibility alias.\n",
)
replace_once(
    "README.md",
    '''Basic TXT and CSV inventory, including supported archive members:

```bash
file-enumerator /backup/Downloads
```
''',
    '''Write every filesystem file and supported archive member beneath `/master`
to one text file:

```bash
file-enumerator /master -o files.txt
```

Exclude archive contents while still listing the archive container files:

```bash
file-enumerator /master -o files.txt --exclude-archives
```

The older advanced mode still creates timestamped TXT and CSV reports when no
`-o/--output` path is supplied:

```bash
file-enumerator /backup/Downloads
```
''',
)
replace_once(
    "README.md",
    "  evaluated; use `--no-archives` to disable member traversal entirely.\n",
    "  evaluated; use `--exclude-archives` to disable member traversal entirely.\n",
)
replace_once(
    "README.md",
    "The error log is written to `--output-dir`. If that location cannot be used, the\n"
    "program attempts to write it in the current directory. `--quiet` never suppresses\n",
    "With `-o/--output`, the error log is written beside the requested output file.\n"
    "In advanced mode it is written to `--output-dir`. If that location cannot be used,\n"
    "the program attempts to write it in the current directory. `--quiet` never suppresses\n",
)

# Man page.
replace_once(
    "man/file-enumerator.1",
    'file-enumerator 1.2.0',
    'file-enumerator 1.2.1',
)
replace_once(
    "man/file-enumerator.1",
    '.B file-enumerator\n.RI [ options ]\n.I ROOT\n',
    '.B file-enumerator\n.I ROOT\n.BI "-o " FILE\n.br\n.B file-enumerator\n.RI [ advanced-options ]\n.I ROOT\n',
)
replace_once(
    "man/file-enumerator.1",
    '.TP\n.BR --format " " { txt , csv , both }\n',
    '.TP\n.BR -o " FILE"\n.TQ\n.BR --output " FILE"\nWrite exactly one report to the requested path. A\n.B .txt\nfilename selects text output and a\n.B .csv\nfilename selects CSV output. Relative paths are resolved from the current\ndirectory. This simple mode cannot be combined with\n.BR --format ,\n.BR --output-dir ,\n.BR --basename ,\n.BR --zip ,\nor\n.BR --zip-only .\n.TP\n.BR --format " " { txt , csv , both }\n',
)
replace_once(
    "man/file-enumerator.1",
    '.B --no-archives\nDo not inspect supported archives for member filenames. Archive container files\ncan still appear as normal filesystem results.\n',
    '.BR --exclude-archives\n.TQ\n.B --no-archives\nDo not inspect archives for member filenames. Archive container files can still\nappear as normal filesystem results. The older\n.B --no-archives\nname is retained as a compatibility alias.\n',
)
replace_once(
    "man/file-enumerator.1",
    'Inventory a directory and supported archive contents as TXT and CSV:\n.PP\n.nf\nfile-enumerator /backup/Downloads\n.fi\n',
    'Write all files and supported archive members beneath /master to one text file:\n.PP\n.nf\nfile-enumerator /master -o files.txt\n.fi\n.PP\nExclude archive contents while retaining archive container files:\n.PP\n.nf\nfile-enumerator /master -o files.txt --exclude-archives\n.fi\n.PP\nCreate the advanced default TXT and CSV inventory:\n.PP\n.nf\nfile-enumerator /backup/Downloads\n.fi\n',
)
replace_once(
    "man/file-enumerator.1",
    'file-enumerator /backup/Downloads --no-archives\n',
    'file-enumerator /backup/Downloads --exclude-archives\n',
)
replace_once(
    "man/file-enumerator.1",
    'The error log is written under\n.BR --output-dir .\nIf that location cannot be used, the current directory is attempted. The error\n',
    'With\n.BR -o / --output ,\nthe error log is written beside the requested report. In advanced mode it is\nwritten under\n.BR --output-dir .\nIf that location cannot be used, the current directory is attempted. The error\n',
)

# Changelog, RPM metadata, and install docs.
insert_before(
    "CHANGELOG.md",
    "## 1.2.0 — 2026-07-21\n",
    "## 1.2.1 — 2026-07-22\n\n"
    "- Added `-o/--output` for an exact `.txt` or `.csv` report path.\n"
    "- Added `--exclude-archives` as the preferred archive-disable option.\n"
    "- Retained `--no-archives` and the advanced output flags for compatibility.\n"
    "- Added regression coverage and updated help, completion, and documentation.\n\n",
)
replace_once(
    "packaging/rpm/file-enumerator.spec",
    "Version:        1.2.0",
    "Version:        1.2.1",
)
replace_once(
    "packaging/rpm/file-enumerator.spec",
    "%changelog\n",
    "%changelog\n"
    "* Wed Jul 22 2026 Cheddar SunRae Logistics Inc. <shane@cheddar.team> - 1.2.1-1\n"
    "- Add simple exact-file output and exclude-archives alias\n\n",
)
replace_once(
    "docs/INSTALL.md",
    "cp dist/file-enumerator-1.2.0.tar.gz ~/rpmbuild/SOURCES/",
    "cp dist/file-enumerator-1.2.1.tar.gz ~/rpmbuild/SOURCES/",
)

print("Applied simple CLI migration to 1.2.1")
