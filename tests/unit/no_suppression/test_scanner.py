"""Scanner pattern coverage tests."""

from __future__ import annotations

from pathlib import Path

from no_suppression.scanner import scan_paths, scan_text


class TestScanText:
    """Verify every forbidden marker is detected with the right rule_id."""

    def test_detects_nosonar_marker(self) -> None:
        text = "do_thing()  # NOSONAR\n"
        findings = scan_text(Path("a.py"), text)
        assert len(findings) == 1
        assert findings[0].rule_id == "nosonar"

    def test_detects_nosonar_with_target_capture(self) -> None:
        text = "do_thing()  # NOSONAR(pythonsecurity:S2083)\n"
        findings = scan_text(Path("a.py"), text)
        assert findings and findings[0].rule_target == "pythonsecurity:S2083"

    def test_detects_noqa_with_target_capture(self) -> None:
        text = "x = 1  # noqa: E501\n"
        findings = scan_text(Path("a.py"), text)
        assert findings and findings[0].rule_id == "noqa"
        assert findings[0].rule_target == "E501"

    def test_detects_pragma_no_cover(self) -> None:
        text = "if False:  # pragma: no cover\n    pass\n"
        findings = scan_text(Path("a.py"), text)
        assert findings and findings[0].rule_id == "pragma_no_cover"

    def test_detects_type_ignore(self) -> None:
        text = "result = stuff()  # type: ignore[attr-defined]\n"
        findings = scan_text(Path("a.py"), text)
        assert findings and findings[0].rule_id == "type_ignore"
        assert findings[0].rule_target == "attr-defined"

    def test_detects_nosec(self) -> None:
        text = "subprocess.run(cmd, shell=True)  # nosec B602\n"
        findings = scan_text(Path("a.py"), text)
        assert findings and findings[0].rule_id == "nosec"

    def test_detects_sonar_multicriteria_root_line(self) -> None:
        text = "sonar.issue.ignore.multicriteria=e1,e2\n"
        findings = scan_text(Path("sonar-project.properties"), text)
        assert findings and findings[0].rule_id == "sonar_multicriteria"

    def test_detects_sonar_multicriteria_rule_key_line(self) -> None:
        text = "sonar.issue.ignore.multicriteria.e1.ruleKey=python:S5852\n"
        findings = scan_text(Path("sonar-project.properties"), text)
        assert findings and findings[0].rule_id == "sonar_multicriteria"

    def test_detects_ts_ignore(self) -> None:
        text = "// @ts-ignore: legacy interop\nconst x: any = 1;\n"
        findings = scan_text(Path("a.ts"), text)
        assert findings and findings[0].rule_id == "ts_ignore"

    def test_detects_eslint_disable_slash(self) -> None:
        text = "// eslint-disable-next-line @typescript-eslint/no-explicit-any\n"
        findings = scan_text(Path("a.ts"), text)
        assert findings and findings[0].rule_id == "eslint_disable_slash"

    def test_clean_file_has_no_findings(self) -> None:
        text = "def f():\n    return 1\n# this is a regular comment\n"
        assert scan_text(Path("a.py"), text) == []

    def test_records_line_and_column(self) -> None:
        text = "x = 1\ny = 2  # noqa: F401\nz = 3\n"
        findings = scan_text(Path("a.py"), text)
        assert len(findings) == 1
        assert findings[0].line == 2
        assert findings[0].column > 1


class TestScanPaths:
    """Filesystem scan with include/exclude globs."""

    def test_scans_matching_python_files(self, tmp_path: Path) -> None:
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        good = src_dir / "good.py"
        good.write_text("x = 1\n", encoding="utf-8")
        bad = src_dir / "bad.py"
        bad.write_text("x = 1  # noqa: E501\n", encoding="utf-8")

        findings = scan_paths(tmp_path, include_globs=["src/**/*.py"], exclude_globs=())
        assert len(findings) == 1
        assert findings[0].path == Path("src/bad.py")

    def test_excludes_paths_matching_exclude_globs(self, tmp_path: Path) -> None:
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        bad = src_dir / "bad.py"
        bad.write_text("x = 1  # noqa: E501\n", encoding="utf-8")
        tests_dir = tmp_path / "src" / "no_suppression"
        tests_dir.mkdir()
        defines = tests_dir / "scanner.py"
        defines.write_text("# noqa: defines the patterns\n", encoding="utf-8")

        findings = scan_paths(
            tmp_path,
            include_globs=["src/**/*.py"],
            exclude_globs=["src/no_suppression/**"],
        )
        relative_paths = {f.path.as_posix() for f in findings}
        assert "src/bad.py" in relative_paths
        assert "src/no_suppression/scanner.py" not in relative_paths

    def test_findings_sorted_deterministically(self, tmp_path: Path) -> None:
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "b.py").write_text("x = 1  # noqa: F401\n", encoding="utf-8")
        (src_dir / "a.py").write_text("x = 1  # noqa: F401\n", encoding="utf-8")
        findings = scan_paths(tmp_path, include_globs=["src/**/*.py"], exclude_globs=())
        assert [f.path.as_posix() for f in findings] == ["src/a.py", "src/b.py"]
