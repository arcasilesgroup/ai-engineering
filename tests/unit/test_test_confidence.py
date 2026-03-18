"""Tests for test_confidence_metrics fallback chain."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit


class TestTestConfidenceMetrics:
    """Tests for test_confidence_metrics in signals.py."""

    def setup_method(self):
        from ai_engineering.lib.signals import _reset_sonar_cache

        _reset_sonar_cache()

    def test_sonarcloud_source_preferred(self, tmp_path: Path):
        """SonarCloud coverage is used when available."""
        from ai_engineering.lib.signals import _reset_sonar_cache, test_confidence_metrics

        _reset_sonar_cache()
        sonar_data = {"available": True, "coverage_pct": 87.5, "source": "sonarcloud"}
        with patch(
            "ai_engineering.lib.signals.sonar_detailed_metrics",
            return_value=sonar_data,
        ):
            result = test_confidence_metrics(tmp_path)
        assert result["source"] == "sonarcloud"
        assert result["coverage_pct"] == 87.5
        assert result["meets_threshold"] is True

    def test_sonarcloud_below_threshold(self, tmp_path: Path):
        """SonarCloud coverage below 80% -> meets_threshold False."""
        from ai_engineering.lib.signals import _reset_sonar_cache, test_confidence_metrics

        _reset_sonar_cache()
        sonar_data = {"available": True, "coverage_pct": 65.0, "source": "sonarcloud"}
        with patch(
            "ai_engineering.lib.signals.sonar_detailed_metrics",
            return_value=sonar_data,
        ):
            result = test_confidence_metrics(tmp_path)
        assert result["meets_threshold"] is False

    def test_coverage_json_fallback(self, tmp_path: Path):
        """Falls back to coverage.json when SonarCloud unavailable."""
        from ai_engineering.lib.signals import _reset_sonar_cache, test_confidence_metrics

        _reset_sonar_cache()
        coverage_data = {
            "totals": {"percent_covered": 82.3},
            "files": {
                "src/foo.py": {"summary": {"percent_covered": 90}},
                "src/bar.py": {"summary": {"percent_covered": 0}},
                "src/baz.py": {"summary": {"percent_covered": 75}},
            },
        }
        (tmp_path / "coverage.json").write_text(json.dumps(coverage_data))
        with patch(
            "ai_engineering.lib.signals.sonar_detailed_metrics",
            return_value={"available": False},
        ):
            result = test_confidence_metrics(tmp_path)
        assert result["source"] == "coverage.json"
        assert result["coverage_pct"] == 82.3
        assert result["files_total"] == 3
        assert result["files_covered"] == 2
        assert "src/bar.py" in result["untested_critical"]

    def test_test_scope_fallback(self, tmp_path: Path):
        """Falls back to test_scope mapping when no coverage data."""
        from ai_engineering.lib.signals import _reset_sonar_cache, test_confidence_metrics

        _reset_sonar_cache()
        # Create src structure
        src = tmp_path / "src" / "mymod"
        src.mkdir(parents=True)
        (src / "__init__.py").touch()
        (src / "foo.py").touch()
        (src / "bar.py").touch()
        with patch(
            "ai_engineering.lib.signals.sonar_detailed_metrics",
            return_value={"available": False},
        ):
            result = test_confidence_metrics(tmp_path)
        assert result["source"] == "test_scope"

    def test_no_data_fallback(self, tmp_path: Path):
        """Returns defaults when no data source available."""
        import sys

        from ai_engineering.lib.signals import _reset_sonar_cache, test_confidence_metrics

        _reset_sonar_cache()
        with (
            patch(
                "ai_engineering.lib.signals.sonar_detailed_metrics",
                return_value={"available": False},
            ),
            patch.dict(
                sys.modules,
                {"ai_engineering.policy.test_scope": None},
            ),
        ):
            result = test_confidence_metrics(tmp_path)
        assert result["source"] == "none"
        assert result["coverage_pct"] == 0.0
        assert result["meets_threshold"] is False

    def test_corrupt_coverage_json_skipped(self, tmp_path: Path):
        """Corrupt coverage.json is skipped gracefully."""
        from ai_engineering.lib.signals import _reset_sonar_cache, test_confidence_metrics

        _reset_sonar_cache()
        (tmp_path / "coverage.json").write_text("not valid json")
        with patch(
            "ai_engineering.lib.signals.sonar_detailed_metrics",
            return_value={"available": False},
        ):
            result = test_confidence_metrics(tmp_path)
        assert result["source"] in ("test_scope", "none")

    def test_coverage_json_meets_threshold_true(self, tmp_path: Path):
        """coverage.json with >= 80% meets threshold."""
        from ai_engineering.lib.signals import _reset_sonar_cache, test_confidence_metrics

        _reset_sonar_cache()
        coverage_data = {
            "totals": {"percent_covered": 80.0},
            "files": {
                "src/a.py": {"summary": {"percent_covered": 80}},
            },
        }
        (tmp_path / "coverage.json").write_text(json.dumps(coverage_data))
        with patch(
            "ai_engineering.lib.signals.sonar_detailed_metrics",
            return_value={"available": False},
        ):
            result = test_confidence_metrics(tmp_path)
        assert result["source"] == "coverage.json"
        assert result["meets_threshold"] is True

    def test_coverage_json_meets_threshold_false(self, tmp_path: Path):
        """coverage.json with < 80% does not meet threshold."""
        from ai_engineering.lib.signals import _reset_sonar_cache, test_confidence_metrics

        _reset_sonar_cache()
        coverage_data = {
            "totals": {"percent_covered": 79.9},
            "files": {
                "src/a.py": {"summary": {"percent_covered": 79.9}},
            },
        }
        (tmp_path / "coverage.json").write_text(json.dumps(coverage_data))
        with patch(
            "ai_engineering.lib.signals.sonar_detailed_metrics",
            return_value={"available": False},
        ):
            result = test_confidence_metrics(tmp_path)
        assert result["source"] == "coverage.json"
        assert result["meets_threshold"] is False

    def test_coverage_json_untested_limited_to_five(self, tmp_path: Path):
        """Untested files list is limited to top 5."""
        from ai_engineering.lib.signals import _reset_sonar_cache, test_confidence_metrics

        _reset_sonar_cache()
        files = {}
        for i in range(10):
            files[f"src/mod{i}.py"] = {"summary": {"percent_covered": 0}}
        coverage_data = {
            "totals": {"percent_covered": 0.0},
            "files": files,
        }
        (tmp_path / "coverage.json").write_text(json.dumps(coverage_data))
        with patch(
            "ai_engineering.lib.signals.sonar_detailed_metrics",
            return_value={"available": False},
        ):
            result = test_confidence_metrics(tmp_path)
        assert result["source"] == "coverage.json"
        assert len(result["untested_critical"]) == 5

    def test_sonarcloud_zero_coverage_skipped(self, tmp_path: Path):
        """SonarCloud with 0% coverage falls through to next source."""
        from ai_engineering.lib.signals import _reset_sonar_cache, test_confidence_metrics

        _reset_sonar_cache()
        sonar_data = {"available": True, "coverage_pct": 0, "source": "sonarcloud"}
        # No coverage.json, so should fall through to test_scope
        with patch(
            "ai_engineering.lib.signals.sonar_detailed_metrics",
            return_value=sonar_data,
        ):
            result = test_confidence_metrics(tmp_path)
        assert result["source"] in ("test_scope", "none")

    def test_sonarcloud_not_available_skipped(self, tmp_path: Path):
        """SonarCloud not available falls through to next source."""
        from ai_engineering.lib.signals import _reset_sonar_cache, test_confidence_metrics

        _reset_sonar_cache()
        with patch(
            "ai_engineering.lib.signals.sonar_detailed_metrics",
            return_value={"available": False},
        ):
            result = test_confidence_metrics(tmp_path)
        assert result["source"] != "sonarcloud"

    def test_return_shape_consistent(self, tmp_path: Path):
        """All return paths have the same keys."""
        from ai_engineering.lib.signals import _reset_sonar_cache, test_confidence_metrics

        _reset_sonar_cache()
        expected_keys = {
            "source",
            "coverage_pct",
            "meets_threshold",
            "files_total",
            "files_covered",
            "untested_critical",
        }
        # Test with sonarcloud
        sonar_data = {"available": True, "coverage_pct": 90.0, "source": "sonarcloud"}
        with patch(
            "ai_engineering.lib.signals.sonar_detailed_metrics",
            return_value=sonar_data,
        ):
            result = test_confidence_metrics(tmp_path)
        assert set(result.keys()) == expected_keys

        # Test with no data
        _reset_sonar_cache()
        with patch(
            "ai_engineering.lib.signals.sonar_detailed_metrics",
            return_value={"available": False},
        ):
            result = test_confidence_metrics(tmp_path)
        assert set(result.keys()) == expected_keys
