from __future__ import annotations

import csv
import io
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
        self, *args: str, cwd: Path | None = None
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(PROGRAM), *args],
            text=True,
            capture_output=True,
            check=False,
            cwd=cwd,
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

    def read_csv(self, path: Path) -> list[dict[str, str]]:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))

    def test_version(self) -> None:
        result = self.run_program("--version")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "file-enumerator 1.1.1")

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

    def test_unsupported_archive_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = self.make_fixture(base)
            (root / "unsupported.7z").write_bytes(b"7z placeholder")
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
