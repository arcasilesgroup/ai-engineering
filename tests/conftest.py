"""Shared pytest fixtures for all tests."""

import pytest
import os


@pytest.fixture
def temp_repo(tmp_path):
    """Create a temporary directory for testing."""
    repo_dir = tmp_path / "test_repo"
    repo_dir.mkdir()
    # Save original directory
    original_dir = os.getcwd()
    # Change to temp directory
    os.chdir(repo_dir)
    yield repo_dir
    # Restore original directory
    os.chdir(original_dir)


@pytest.fixture
def sample_manifest():
    """Sample manifest.yml for testing."""
    return {
        "version": "1.0",
        "metadata": {
            "name": "test-repo",
            "owner": "Test Team"
        },
        "standards": {
            "gates": {
                "pre_commit": {
                    "lint": "mandatory",
                    "secret_scan": "mandatory"
                }
            }
        }
    }
