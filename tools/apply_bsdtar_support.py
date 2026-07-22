#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8", newline="\n")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


def replace_section(text: str, start: str, end: str, replacement: str, label: str) -> str:
    start_index = text.find(start)
    if start_index < 0:
        raise RuntimeError(f"{label}: start marker not found")
    end_index = text.find(end, start_index + len(start))
    if end_index < 0:
        raise RuntimeError(f"{label}: end marker not found")
    return text[:start_index] + replacement + text[end_index:]


# Core executable
path = "src/file-enumerator"
text = read(path)
text = replace_once(
    text,
    "The primary target is Fedora/Linux, but the program uses only the Python 3\nstandard library and remains portable to other Python 3 platforms.\n",
    "The primary target is Fedora/Linux. ZIP and TAR use the Python 3 standard\nlibrary; additional archive formats use the optional bsdtar command.\n",
    "source docstring",
)
text = replace_once(
    text,
    "import os\nimport stat\nimport sys\nimport tarfile\n",
    "import os\nimport shutil\nimport stat\nimport subprocess\nimport sys\nimport tarfile\n",
    "source imports",
)
text = replace_once(text, 'VERSION = "1.1.1"', 'VERSION = "1.2.0"', "source version")
text = replace_once(
    text,
    '''UNSUPPORTED_ARCHIVE_SUFFIXES = (\n    ".7z",\n    ".rar",\n    ".cab",\n    ".cpio",\n    ".iso",\n    ".lha",\n    ".lzh",\n    ".ace",\n    ".tar.zst",\n    ".tzst",\n)\n''',
    '''BSDTAR_ARCHIVE_SUFFIXES = (\n    ".7z",\n    ".rar",\n    ".cab",\n    ".cpio",\n    ".iso",\n    ".lha",\n    ".lzh",\n    ".ar",\n    ".xar",\n    ".rpm",\n    ".deb",\n    ".tar.zst",\n    ".tzst",\n)\nUNSUPPORTED_ARCHIVE_SUFFIXES = (\n    ".ace",\n)\n''',
    "archive suffix constants",
)
text = replace_once(
    text,
    '''class CLIUsageError(ValueError):\n    """Raised instead of allowing argparse to terminate without error logging."""\n\n\nclass LoggingArgumentParser(argparse.ArgumentParser):\n''',
    '''class CLIUsageError(ValueError):\n    """Raised instead of allowing argparse to terminate without error logging."""\n\n\nclass ArchiveBackendMissing(RuntimeError):\n    """Raised when an optional archive helper is required but unavailable."""\n\n\nclass LoggingArgumentParser(argparse.ArgumentParser):\n''',
    "backend exception",
)
text = replace_once(
    text,
    '''def archive_kind(path: Path) -> Optional[str]:\n    lower_name = path.name.casefold()\n    if lower_name.endswith(ZIP_ARCHIVE_SUFFIXES):\n        return "zip"\n    if lower_name.endswith(TAR_ARCHIVE_SUFFIXES):\n        return "tar"\n    if lower_name.endswith(UNSUPPORTED_ARCHIVE_SUFFIXES):\n        return "unsupported"\n    return None\n''',
    '''def bsdtar_archive_format(path: Path) -> str:\n    lower_name = path.name.casefold()\n    for suffix in sorted(BSDTAR_ARCHIVE_SUFFIXES, key=len, reverse=True):\n        if lower_name.endswith(suffix):\n            return suffix.lstrip(".")\n    return "libarchive"\n\n\ndef archive_kind(path: Path) -> Optional[str]:\n    lower_name = path.name.casefold()\n    if lower_name.endswith(ZIP_ARCHIVE_SUFFIXES):\n        return "zip"\n    if lower_name.endswith(TAR_ARCHIVE_SUFFIXES):\n        return "tar"\n    if lower_name.endswith(BSDTAR_ARCHIVE_SUFFIXES):\n        return "bsdtar"\n    if lower_name.endswith(UNSUPPORTED_ARCHIVE_SUFFIXES):\n        return "unsupported"\n    return None\n''',
    "archive kind",
)
text = replace_once(
    text,
    '''    return records\n\n\ndef enumerate_archive_members(\n    path: Path,\n    root: Path,\n    filters: FilterConfig,\n) -> tuple[list[FileRecord], list[str]]:\n''',
    '''    return records\n\n\ndef enumerate_bsdtar_members(\n    path: Path,\n    root: Path,\n    filters: FilterConfig,\n) -> list[FileRecord]:\n    bsdtar = shutil.which("bsdtar")\n    if bsdtar is None:\n        raise ArchiveBackendMissing(\n            "bsdtar is required for this archive format; on Fedora run: "\n            "sudo dnf install bsdtar"\n        )\n\n    completed = subprocess.run(\n        [bsdtar, "-tf", str(path)],\n        text=True,\n        capture_output=True,\n        check=False,\n        encoding="utf-8",\n        errors="replace",\n    )\n    if completed.returncode != 0:\n        detail = completed.stderr.strip() or completed.stdout.strip()\n        if not detail:\n            detail = f"bsdtar exited with status {completed.returncode}"\n        raise RuntimeError(detail)\n\n    records: list[FileRecord] = []\n    archive_relative = PurePosixPath(path.relative_to(root).as_posix())\n    archive_format = bsdtar_archive_format(path)\n    for raw_name in completed.stdout.splitlines():\n        member_name = normalize_archive_member_name(raw_name)\n        if not member_name or raw_name.rstrip().endswith("/"):\n            continue\n        member_relative = PurePosixPath(member_name)\n        if not member_relative.name:\n            continue\n        folder_values = archive_folder_candidates(archive_relative, member_relative)\n        if not record_matches(\n            member_relative.name,\n            member_relative.suffix,\n            folder_values,\n            filters,\n        ):\n            continue\n        records.append(\n            archived_record(\n                archive_path=path,\n                root=root,\n                member_name=member_name,\n                size_bytes=0,\n                modified_utc="",\n                is_symlink=False,\n                archive_format=archive_format,\n            )\n        )\n    return records\n\n\ndef enumerate_archive_members(\n    path: Path,\n    root: Path,\n    filters: FilterConfig,\n) -> tuple[list[FileRecord], list[str]]:\n''',
    "bsdtar enumerator insertion",
)
text = replace_once(
    text,
    '''    if kind == "unsupported":\n        return [], [\n            f"UNSUPPORTED ARCHIVE: {path}: format is not supported by the "\n            "dependency-free archive reader"\n        ]\n\n    try:\n        if kind == "zip":\n            return enumerate_zip_members(path, root, filters), []\n        return enumerate_tar_members(path, root, filters), []\n    except (\n        OSError,\n        EOFError,\n        RuntimeError,\n        tarfile.TarError,\n        zipfile.BadZipFile,\n        ValueError,\n    ) as error:\n        return [], [f"ARCHIVE ERROR: {path}: {error}"]\n''',
    '''    if kind == "unsupported":\n        return [], [\n            f"UNSUPPORTED ARCHIVE: {path}: format is not supported by the "\n            "configured archive readers"\n        ]\n\n    try:\n        if kind == "zip":\n            return enumerate_zip_members(path, root, filters), []\n        if kind == "tar":\n            return enumerate_tar_members(path, root, filters), []\n        return enumerate_bsdtar_members(path, root, filters), []\n    except ArchiveBackendMissing as error:\n        return [], [f"ARCHIVE BACKEND MISSING: {path}: {error}"]\n    except (\n        OSError,\n        EOFError,\n        RuntimeError,\n        subprocess.SubprocessError,\n        tarfile.TarError,\n        zipfile.BadZipFile,\n        ValueError,\n    ) as error:\n        return [], [f"ARCHIVE ERROR: {path}: {error}"]\n''',
    "archive dispatch",
)
text = replace_once(
    text,
    '"Recursively enumerate filesystem files and supported archive members "\n            "with filetype, filename, and foldername include/exclude filters."',
    '"Recursively enumerate filesystem files and archive members, using native "\n            "ZIP/TAR readers and optional bsdtar support for broader formats, "\n            "with filetype, filename, and foldername include/exclude filters."',
    "parser description",
)
write(path, text)

# Tests
path = "tests/test_file_enumerator.py"
text = read(path)
text = replace_once(text, "import io\nimport subprocess\n", "import io\nimport os\nimport subprocess\n", "test imports")
text = replace_once(
    text,
    '''    def run_program(\n        self, *args: str, cwd: Path | None = None\n    ) -> subprocess.CompletedProcess[str]:\n        return subprocess.run(\n            [sys.executable, str(PROGRAM), *args],\n            text=True,\n            capture_output=True,\n            check=False,\n            cwd=cwd,\n        )\n''',
    '''    def run_program(\n        self,\n        *args: str,\n        cwd: Path | None = None,\n        env: dict[str, str] | None = None,\n    ) -> subprocess.CompletedProcess[str]:\n        return subprocess.run(\n            [sys.executable, str(PROGRAM), *args],\n            text=True,\n            capture_output=True,\n            check=False,\n            cwd=cwd,\n            env=env,\n        )\n''',
    "run_program environment",
)
text = replace_once(
    text,
    '''    def read_csv(self, path: Path) -> list[dict[str, str]]:\n''',
    '''    def make_fake_bsdtar(self, base: Path) -> Path:\n        bin_dir = base / "fake-bin"\n        bin_dir.mkdir()\n        script = bin_dir / "bsdtar"\n        script.write_text(\n            f"#!{sys.executable}\\n"\n            "from pathlib import Path\\n"\n            "import sys\\n"\n            "name = Path(sys.argv[-1]).name.casefold()\\n"\n            "if name.endswith('.rar'):\\n"\n            "    print('docs/inside-rar.PDF')\\n"\n            "    print('empty/')\\n"\n            "elif name.endswith('.iso'):\\n"\n            "    print('ISO_ROOT/manual.txt')\\n"\n            "else:\\n"\n            "    print('unsupported fake archive', file=sys.stderr)\\n"\n            "    raise SystemExit(3)\\n",\n            encoding="utf-8",\n        )\n        script.chmod(0o755)\n        return bin_dir\n\n    def read_csv(self, path: Path) -> list[dict[str, str]]:\n''',
    "fake bsdtar helper",
)
text = replace_once(text, '"file-enumerator 1.1.1"', '"file-enumerator 1.2.0"', "test version")
text = replace_once(
    text,
    '''    def test_unsupported_archive_is_reported(self) -> None:\n        with tempfile.TemporaryDirectory() as temporary:\n            base = Path(temporary)\n            root = self.make_fixture(base)\n            (root / "unsupported.7z").write_bytes(b"7z placeholder")\n            output = base / "output"\n            result = self.run_program(\n                str(root),\n                "--output-dir",\n                str(output),\n                "--basename",\n                "unsupported",\n                "--format",\n                "csv",\n            )\n            self.assertEqual(result.returncode, 2)\n            self.assertIn("UNSUPPORTED ARCHIVE:", result.stderr)\n            logs = list(output.glob("file_enum_*_errors.txt"))\n            self.assertEqual(len(logs), 1)\n            self.assertIn(\n                "UNSUPPORTED ARCHIVE:", logs[0].read_text(encoding="utf-8")\n            )\n''',
    '''    def test_bsdtar_backend_lists_rar_and_iso(self) -> None:\n        with tempfile.TemporaryDirectory() as temporary:\n            base = Path(temporary)\n            root = self.make_fixture(base)\n            archive_dir = root / "archives"\n            archive_dir.mkdir()\n            (archive_dir / "sample.rar").write_bytes(b"rar fixture")\n            (archive_dir / "disc.iso").write_bytes(b"iso fixture")\n            fake_bin = self.make_fake_bsdtar(base)\n            env = os.environ.copy()\n            env["PATH"] = f"{fake_bin}{os.pathsep}{env.get('PATH', '')}"\n            output = base / "output"\n            result = self.run_program(\n                str(root),\n                "--output-dir",\n                str(output),\n                "--basename",\n                "external_archives",\n                "--format",\n                "csv",\n                env=env,\n            )\n            self.assertEqual(result.returncode, 0, result.stderr)\n            rows = self.read_csv(output / "external_archives.csv")\n            by_path = {row["relative_path"]: row for row in rows}\n            rar_member = "archives/sample.rar::docs/inside-rar.PDF"\n            iso_member = "archives/disc.iso::ISO_ROOT/manual.txt"\n            self.assertEqual(by_path[rar_member]["archive_format"], "rar")\n            self.assertEqual(by_path[iso_member]["archive_format"], "iso")\n            self.assertEqual(by_path[rar_member]["is_archived"], "True")\n            self.assertEqual(by_path[iso_member]["is_archived"], "True")\n\n    def test_missing_bsdtar_backend_is_logged(self) -> None:\n        with tempfile.TemporaryDirectory() as temporary:\n            base = Path(temporary)\n            root = self.make_fixture(base)\n            (root / "sample.rar").write_bytes(b"rar fixture")\n            empty_bin = base / "empty-bin"\n            empty_bin.mkdir()\n            env = os.environ.copy()\n            env["PATH"] = str(empty_bin)\n            output = base / "output"\n            result = self.run_program(\n                str(root),\n                "--output-dir",\n                str(output),\n                "--basename",\n                "missing_backend",\n                "--format",\n                "csv",\n                env=env,\n            )\n            self.assertEqual(result.returncode, 2)\n            self.assertIn("ARCHIVE BACKEND MISSING:", result.stderr)\n            self.assertIn("sudo dnf install bsdtar", result.stderr)\n            logs = list(output.glob("file_enum_*_errors.txt"))\n            self.assertEqual(len(logs), 1)\n            log_text = logs[0].read_text(encoding="utf-8")\n            self.assertIn("ARCHIVE BACKEND MISSING:", log_text)\n            self.assertIn("sudo dnf install bsdtar", log_text)\n\n    def test_unsupported_archive_is_reported(self) -> None:\n        with tempfile.TemporaryDirectory() as temporary:\n            base = Path(temporary)\n            root = self.make_fixture(base)\n            (root / "unsupported.ace").write_bytes(b"ACE placeholder")\n            output = base / "output"\n            result = self.run_program(\n                str(root),\n                "--output-dir",\n                str(output),\n                "--basename",\n                "unsupported",\n                "--format",\n                "csv",\n            )\n            self.assertEqual(result.returncode, 2)\n            self.assertIn("UNSUPPORTED ARCHIVE:", result.stderr)\n            logs = list(output.glob("file_enum_*_errors.txt"))\n            self.assertEqual(len(logs), 1)\n            self.assertIn(\n                "UNSUPPORTED ARCHIVE:", logs[0].read_text(encoding="utf-8")\n            )\n''',
    "archive backend tests",
)
write(path, text)

# Version
write("VERSION", "1.2.0\n")

# README
path = "README.md"
text = read(path)
text = replace_once(
    text,
    "- Standard-library-only Python implementation.\n",
    "- Python standard-library core with optional `bsdtar` support for broader formats.\n",
    "README feature",
)
new_archive_section = '''## Archive support\n\nArchive traversal is enabled by default and does not extract files.\n\nThe Python standard library handles these formats directly:\n\n- ZIP and common ZIP containers: `.zip`, `.jar`, `.war`, `.ear`, `.whl`,\n  `.apk`, `.xpi`, and `.epub`\n- TAR and compressed TAR: `.tar`, `.tar.gz`, `.tgz`, `.tar.bz2`, `.tbz`,\n  `.tbz2`, `.tar.xz`, and `.txz`\n\nWhen `bsdtar` is installed, File Enumerator also lists members from `.rar`,\n`.iso`, `.7z`, `.cab`, `.cpio`, `.lha`, `.lzh`, `.ar`, `.xar`, `.rpm`, `.deb`,\n`.tar.zst`, and `.tzst` files. Fedora provides `bsdtar` as a standalone package.\nEncrypted RAR headers, malformed archives, and formats rejected by libarchive are\nreported as failures and written to the timestamped error log.\n\nIf a broad-format archive is encountered without `bsdtar`, the scan continues,\nreturns exit status 2, prints the missing-backend failure, and writes it to the\nerror log. `.ace` remains explicitly unsupported. Nested archive files are listed\nas members but are not recursively opened.\n\nUse `--no-archives` when only filesystem entries are wanted.\n\nThe archive functionality described here applies to the primary Linux/Python\ncommand. The retained PowerShell script has not yet been brought to archive\nfeature parity.\n\n'''
text = replace_section(text, "## Archive support\n", "## Fedora installation\n", new_archive_section, "README archive section")
text = replace_once(
    text,
    "sudo dnf install python3 make man-db bash-completion\n",
    "sudo dnf install python3 make man-db bash-completion bsdtar\n",
    "README Fedora install",
)
text = replace_once(
    text,
    "ZIP member timestamps are left blank because the ZIP format does not reliably\nstore a timezone. TAR member timestamps are emitted in UTC when available.\n",
    "ZIP member timestamps are left blank because the ZIP format does not reliably\nstore a timezone. TAR member timestamps are emitted in UTC when available. The\nplain `bsdtar -t` listing used for broad formats does not expose portable size,\ntimestamp, or symlink metadata, so those fields are emitted as zero/blank/false.\n",
    "README metadata note",
)
write(path, text)

# Man page
path = "man/file-enumerator.1"
text = read(path)
text = replace_once(
    text,
    '.TH FILE-ENUMERATOR 1 "July 2026" "file-enumerator 1.1.1" "User Commands"',
    '.TH FILE-ENUMERATOR 1 "July 2026" "file-enumerator 1.2.0" "User Commands"',
    "man version",
)
text = replace_once(
    text,
    '''Supported ZIP and TAR-family archives are inspected by default without\nextracting their contents. Archive members are evaluated by the same filters as\nfilesystem files and are clearly marked in generated reports.\n''',
    '''ZIP and TAR-family archives are inspected natively by default without\nextracting their contents. When\n.B bsdtar\nis installed, additional formats including RAR and ISO images are also listed.\nArchive members are evaluated by the same filters as filesystem files and are\nclearly marked in generated reports.\n''',
    "man description",
)
new_man_archive = '''.SH ARCHIVE SUPPORT\nArchive traversal is enabled by default and does not extract files.\n.PP\nThe Python standard library reads ZIP containers:\n.BR .zip ,\n.BR .jar ,\n.BR .war ,\n.BR .ear ,\n.BR .whl ,\n.BR .apk ,\n.BR .xpi ,\nand\n.BR .epub ;\nand TAR variants:\n.BR .tar ,\n.BR .tar.gz ,\n.BR .tgz ,\n.BR .tar.bz2 ,\n.BR .tbz ,\n.BR .tbz2 ,\n.BR .tar.xz ,\nand\n.BR .txz .\n.PP\nWhen\n.B bsdtar\nis available, the program also reads\n.BR .rar ,\n.BR .iso ,\n.BR .7z ,\n.BR .cab ,\n.BR .cpio ,\n.BR .lha ,\n.BR .lzh ,\n.BR .ar ,\n.BR .xar ,\n.BR .rpm ,\n.BR .deb ,\n.BR .tar.zst ,\nand\n.BR .tzst .\nOn Fedora, install the helper with:\n.PP\n.nf\nsudo dnf install bsdtar\n.fi\n.PP\nIf the helper is absent, the scan continues and records an\n.B ARCHIVE BACKEND MISSING\nfailure. Encrypted RAR headers, malformed archives, and formats rejected by\nlibarchive are recorded as\n.B ARCHIVE ERROR\nfailures.\n.B .ace\nremains explicitly unsupported.\n.PP\nNested archive files are listed as archive members but are not recursively\nopened. Filtering an archive container out of normal output does not prevent\nits members from being evaluated; use\n.B --no-archives\nto disable member traversal entirely.\n'''
text = replace_section(text, ".SH ARCHIVE SUPPORT\n", ".SH OUTPUT\n", new_man_archive, "man archive section")
text = replace_once(
    text,
    '''ZIP member timestamps are left blank because ZIP timestamps do not reliably\ncarry timezone information. TAR member timestamps are written in UTC when\navailable.\n''',
    '''ZIP member timestamps are left blank because ZIP timestamps do not reliably\ncarry timezone information. TAR member timestamps are written in UTC when\navailable. Broad-format listings from\n.B bsdtar\ndo not expose portable member size, timestamp, or symlink metadata; those fields\nare written as zero, blank, and false respectively.\n''',
    "man metadata note",
)
text = replace_once(
    text,
    ".BR find (1),\n.BR tar (1),\n",
    ".BR bsdtar (1),\n.BR find (1),\n.BR tar (1),\n",
    "man see also",
)
write(path, text)

# Fedora packaging
path = "packaging/rpm/file-enumerator.spec"
text = read(path)
text = replace_once(text, "Version:        1.1.1", "Version:        1.2.0", "spec version")
text = replace_once(
    text,
    "Requires:       bash-completion\n",
    "Requires:       bash-completion\nRequires:       bsdtar\n",
    "spec bsdtar dependency",
)
text = replace_once(
    text,
    '''file-enumerator recursively inventories files beneath a root directory and\nmember filenames inside supported ZIP and TAR-family archives. It can include\nor exclude file extensions, filename globs, and folder globs, and can write TXT,\nCSV, and ZIP output. It uses only the Python standard library.\n''',
    '''file-enumerator recursively inventories files beneath a root directory and\nmember filenames inside ZIP, TAR, RAR, ISO, 7-Zip, and other supported archives.\nIt can include or exclude file extensions, filename globs, and folder globs, and\ncan write TXT, CSV, and ZIP output. ZIP and TAR use Python's standard library;\nbroader formats are listed through bsdtar without extraction.\n''',
    "spec description",
)
text = replace_once(
    text,
    "%changelog\n",
    "%changelog\n* Tue Jul 21 2026 Cheddar SunRae Logistics Inc. <shane@cheddar.team> - 1.2.0-1\n- Add bsdtar-backed RAR, ISO, 7-Zip, CAB, and broad archive listing\n\n",
    "spec changelog",
)
write(path, text)

# Installation documentation
path = "docs/INSTALL.md"
text = read(path)
text = replace_once(
    text,
    "- `bash-completion` for Bash completion\n",
    "- `bash-completion` for Bash completion\n- `bsdtar` for RAR, ISO, 7-Zip, CAB, and other broad archive formats\n",
    "install requirements",
)
text = replace_once(
    text,
    "sudo dnf install python3 make man-db bash-completion\n",
    "sudo dnf install python3 make man-db bash-completion bsdtar\n",
    "install Fedora command",
)
text = replace_once(
    text,
    "sudo dnf install rpm-build rpmdevtools python3 make bash-completion\n",
    "sudo dnf install rpm-build rpmdevtools python3 make bash-completion bsdtar\n",
    "RPM build dependencies",
)
text = replace_once(
    text,
    "cp dist/file-enumerator-1.1.1.tar.gz ~/rpmbuild/SOURCES/\n",
    "cp dist/file-enumerator-1.2.0.tar.gz ~/rpmbuild/SOURCES/\n",
    "RPM source version",
)
write(path, text)

# Changelog
path = "CHANGELOG.md"
text = read(path)
text = replace_once(
    text,
    "# Changelog\n\n",
    "# Changelog\n\n## 1.2.0 — 2026-07-21\n\n- Added optional `bsdtar` archive listing for RAR, ISO, 7-Zip, CAB, CPIO,\n  LHA/LZH, AR/XAR, RPM/DEB, and Zstandard-compressed TAR files.\n- Added explicit missing-backend errors with the Fedora installation command.\n- Preserved native dependency-free ZIP and TAR handling.\n- Added regression coverage for RAR/ISO listing and missing helper logging.\n- Updated the man page, Fedora packaging, and installation documentation.\n\n",
    "project changelog",
)
write(path, text)

print("Applied bsdtar archive support patch")
