from __future__ import annotations

import csv
import io
import os
import subprocess
import sys
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROGRAM = PROJECT_ROOT / "src" / "file-enumerator"


class FileEnumeratorTests(unittest.TestCase):
    def run_program(
        self,
        *args: str,
        cwd: Path | None = None,
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(PROGRAM), *args],
            text=True,
            capture_output=True,
            check=False,
            cwd=cwd,
            env=env,
        )

    def make_fixture(self, base: Path) -> Path:
        root = base / "input"
        (root / "docs").mkdir(parents=True)
        (root / "node_modules" / "pkg").mkdir(parents=True)
        (root / "Evidence").mkdir(parents=True)
        (root / "docs" / "report.PDF").write_text("pdf", encoding="utf-8")
        (root / "docs" / "notes.txt").write_text("notes", encoding="utf-8")
        (root / "docs" / "draft.tmp").write_text("tmp", encoding="utf-8")
        (root / "node_modules" / "pkg" / "skip.js").write_text(
            "js", encoding="utf-8"
        )
        (root / "Evidence" / "case.docx").write_text("docx", encoding="utf-8")
        (root / "README").write_text("none", encoding="utf-8")
        return root

    def add_archive_fixtures(self, root: Path) -> None:
        archive_dir = root / "archives"
        archive_dir.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(
            archive_dir / "sample.zip", mode="w", compression=zipfile.ZIP_DEFLATED
        ) as archive:
            archive.writestr("docs/inside.PDF", "archived pdf")
            archive.writestr("node_modules/pkg/inside.js", "archived js")
            archive.writestr("README", "extensionless archive member")

        with tarfile.open(archive_dir / "sample.tar.gz", mode="w:gz") as archive:
            payload = b"archived text"
            member = tarfile.TarInfo("nested/report.txt")
            member.size = len(payload)
            member.mtime = 1_700_000_000
            archive.addfile(member, io.BytesIO(payload))

    def make_fake_bsdtar(self, base: Path) -> Path:
        bin_dir = base / "fake-bin"
        bin_dir.mkdir()
        script = bin_dir / "bsdtar"
        script.write_text(
            f"#!{sys.executable}\n"
            "from pathlib import Path\n"
            "import sys\n"
            "name = Path(sys.argv[-1]).name.casefold()\n"
            "if name.endswith('.rar'):\n"
            "    print('docs/inside-rar.PDF')\n"
            "    print('empty/')\n"
            "elif name.endswith('.iso'):\n"
            "    print('ISO_ROOT/manual.txt')\n"
            "else:\n"
            "    print('unsupported fake archive', file=sys.stderr)\n"
            "    raise SystemExit(3)\n",
            encoding="utf-8",
        )
        script.chmod(0o755)
        return bin_dir

    def read_csv(self, path: Path) -> list[dict[str, str]]:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))

    def test_version(self) -> None:
        result = self.run_program("--version")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "file-enumerator 1.2.0")

    def test_basic_txt_and_csv(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = self.make_fixture(base)
            output = base / "output"
            result = self.run_program(
                str(root),
                "--output-dir",
                str(output),
                "--basename",
                "inventory",
                "--format",
                "both",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            txt_path = output / "inventory.txt"
            csv_path = output / "inventory.csv"
            self.assertTrue(txt_path.is_file())
            self.assertTrue(csv_path.is_file())
            self.assertEqual(len(self.read_csv(csv_path)), 6)

    def test_include_and_exclude_filters(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = self.make_fixture(base)
            output = base / "output"
            result = self.run_program(
                str(root),
                "--include-filetype",
                "pdf,docx",
                "--exclude-foldername",
                "node_modules",
                "--output-dir",
                str(output),
                "--basename",
                "filtered",
                "--format",
                "csv",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            paths = {row["relative_path"] for row in self.read_csv(output / "filtered.csv")}
            self.assertEqual(paths, {"docs/report.PDF", "Evidence/case.docx"})

    def test_extensionless_filter(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = self.make_fixture(base)
            output = base / "output"
            result = self.run_program(
                str(root),
                "--include-filetype",
                "<none>",
                "--output-dir",
                str(output),
                "--basename",
                "none",
                "--format",
                "txt",
                "--txt-path-mode",
                "relative",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            lines = (output / "none.txt").read_text(encoding="utf-8").splitlines()
            self.assertEqual(lines[-1], "README")

    def test_zip_only(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = self.make_fixture(base)
            output = base / "output"
            result = self.run_program(
                str(root),
                "--output-dir",
                str(output),
                "--basename",
                "archive",
                "--format",
                "both",
                "--zip-only",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse((output / "archive.txt").exists())
            self.assertFalse((output / "archive.csv").exists())
            archive = output / "archive.zip"
            self.assertTrue(archive.is_file())
            with zipfile.ZipFile(archive) as handle:
                self.assertEqual(set(handle.namelist()), {"archive.txt", "archive.csv"})

    def test_outputs_are_not_enumerated(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = self.make_fixture(base)
            output = root / "generated"
            output.mkdir()
            (output / "inventory.txt").write_text("old", encoding="utf-8")
            result = self.run_program(
                str(root),
                "--output-dir",
                str(output),
                "--basename",
                "inventory",
                "--format",
                "csv",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            paths = {row["relative_path"] for row in self.read_csv(output / "inventory.csv")}
            self.assertNotIn("generated/inventory.txt", paths)
            self.assertNotIn("generated/inventory.csv", paths)

    def test_zip_and_tar_members_are_marked(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = self.make_fixture(base)
            self.add_archive_fixtures(root)
            output = base / "output"
            result = self.run_program(
                str(root),
                "--output-dir",
                str(output),
                "--basename",
                "with_archives",
                "--format",
                "both",
                "--txt-path-mode",
                "relative",
            )
            self.assertEqual(result.returncode, 0, result.stderr)

            rows = self.read_csv(output / "with_archives.csv")
            by_path = {row["relative_path"]: row for row in rows}
            zip_member = "archives/sample.zip::docs/inside.PDF"
            tar_member = "archives/sample.tar.gz::nested/report.txt"
            self.assertEqual(by_path[zip_member]["is_archived"], "True")
            self.assertEqual(by_path[zip_member]["archive_format"], "zip")
            self.assertEqual(by_path[zip_member]["archive_path"], "archives/sample.zip")
            self.assertEqual(by_path[zip_member]["archive_member_path"], "docs/inside.PDF")
            self.assertEqual(by_path[tar_member]["is_archived"], "True")
            self.assertEqual(by_path[tar_member]["archive_format"], "tar")

            txt = (output / "with_archives.txt").read_text(encoding="utf-8")
            self.assertIn(f"[ARCHIVED] {zip_member}", txt)
            self.assertIn(f"[ARCHIVED] {tar_member}", txt)

    def test_filters_apply_inside_archives(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = self.make_fixture(base)
            self.add_archive_fixtures(root)
            output = base / "output"
            result = self.run_program(
                str(root),
                "--include-filetype",
                "pdf",
                "--exclude-foldername",
                "node_modules",
                "--output-dir",
                str(output),
                "--basename",
                "archive_filter",
                "--format",
                "csv",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            paths = {
                row["relative_path"]
                for row in self.read_csv(output / "archive_filter.csv")
            }
            self.assertEqual(
                paths,
                {
                    "docs/report.PDF",
                    "archives/sample.zip::docs/inside.PDF",
                },
            )

    def test_no_archives_disables_member_scan(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = self.make_fixture(base)
            self.add_archive_fixtures(root)
            output = base / "output"
            result = self.run_program(
                str(root),
                "--no-archives",
                "--output-dir",
                str(output),
                "--basename",
                "without_archives",
                "--format",
                "csv",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            rows = self.read_csv(output / "without_archives.csv")
            self.assertTrue(all(row["is_archived"] == "False" for row in rows))

    def test_archive_failure_prints_and_writes_timestamped_log(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = self.make_fixture(base)
            (root / "broken.zip").write_bytes(b"not a zip archive")
            output = base / "output"
            result = self.run_program(
                str(root),
                "--output-dir",
                str(output),
                "--basename",
                "broken",
                "--format",
                "csv",
                "--quiet",
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("ARCHIVE ERROR:", result.stderr)
            self.assertIn("broken.zip", result.stderr)
            logs = list(output.glob("file_enum_*_errors.txt"))
            self.assertEqual(len(logs), 1)
            log_text = logs[0].read_text(encoding="utf-8")
            self.assertIn("ARCHIVE ERROR:", log_text)
            self.assertIn("broken.zip", log_text)
            self.assertIn(f"Error log: {logs[0]}", result.stderr)

    def test_fatal_failure_prints_and_writes_error_log(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            missing = base / "does-not-exist"
            result = self.run_program(str(missing), cwd=base)
            self.assertEqual(result.returncode, 1)
            self.assertIn("ERROR: Root path does not exist:", result.stderr)
            logs = list(base.glob("file_enum_*_errors.txt"))
            self.assertEqual(len(logs), 1)
            self.assertIn(
                "ERROR: Root path does not exist:",
                logs[0].read_text(encoding="utf-8"),
            )

    def test_bsdtar_backend_lists_rar_and_iso(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = self.make_fixture(base)
            archive_dir = root / "archives"
            archive_dir.mkdir()
            (archive_dir / "sample.rar").write_bytes(b"rar fixture")
            (archive_dir / "disc.iso").write_bytes(b"iso fixture")
            fake_bin = self.make_fake_bsdtar(base)
            env = os.environ.copy()
            env["PATH"] = f"{fake_bin}{os.pathsep}{env.get('PATH', '')}"
            output = base / "output"
            result = self.run_program(
                str(root),
                "--output-dir",
                str(output),
                "--basename",
                "external_archives",
                "--format",
                "csv",
                env=env,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            rows = self.read_csv(output / "external_archives.csv")
            by_path = {row["relative_path"]: row for row in rows}
            rar_member = "archives/sample.rar::docs/inside-rar.PDF"
            iso_member = "archives/disc.iso::ISO_ROOT/manual.txt"
            self.assertEqual(by_path[rar_member]["archive_format"], "rar")
            self.assertEqual(by_path[iso_member]["archive_format"], "iso")
            self.assertEqual(by_path[rar_member]["is_archived"], "True")
            self.assertEqual(by_path[iso_member]["is_archived"], "True")

    def test_missing_bsdtar_backend_is_logged(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = self.make_fixture(base)
            (root / "sample.rar").write_bytes(b"rar fixture")
            empty_bin = base / "empty-bin"
            empty_bin.mkdir()
            env = os.environ.copy()
            env["PATH"] = str(empty_bin)
            output = base / "output"
            result = self.run_program(
                str(root),
                "--output-dir",
                str(output),
                "--basename",
                "missing_backend",
                "--format",
                "csv",
                env=env,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("ARCHIVE BACKEND MISSING:", result.stderr)
            self.assertIn("sudo dnf install bsdtar", result.stderr)
            logs = list(output.glob("file_enum_*_errors.txt"))
            self.assertEqual(len(logs), 1)
            log_text = logs[0].read_text(encoding="utf-8")
            self.assertIn("ARCHIVE BACKEND MISSING:", log_text)
            self.assertIn("sudo dnf install bsdtar", log_text)

    def test_unsupported_archive_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = self.make_fixture(base)
            (root / "unsupported.ace").write_bytes(b"ACE placeholder")
            output = base / "output"
            result = self.run_program(
                str(root),
                "--output-dir",
                str(output),
                "--basename",
                "unsupported",
                "--format",
                "csv",
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("UNSUPPORTED ARCHIVE:", result.stderr)
            logs = list(output.glob("file_enum_*_errors.txt"))
            self.assertEqual(len(logs), 1)
            self.assertIn(
                "UNSUPPORTED ARCHIVE:", logs[0].read_text(encoding="utf-8")
            )

    def test_zip_only_keeps_error_log_loose(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = self.make_fixture(base)
            (root / "broken.zip").write_bytes(b"not a zip archive")
            output = base / "output"
            result = self.run_program(
                str(root),
                "--output-dir",
                str(output),
                "--basename",
                "broken_zip_only",
                "--format",
                "both",
                "--zip-only",
            )
            self.assertEqual(result.returncode, 2)
            self.assertFalse((output / "broken_zip_only.txt").exists())
            self.assertFalse((output / "broken_zip_only.csv").exists())
            logs = list(output.glob("file_enum_*_errors.txt"))
            self.assertEqual(len(logs), 1)
            with zipfile.ZipFile(output / "broken_zip_only.zip") as archive:
                self.assertIn(logs[0].name, archive.namelist())
                self.assertIn("broken_zip_only.txt", archive.namelist())
                self.assertIn("broken_zip_only.csv", archive.namelist())


if __name__ == "__main__":
    unittest.main()
