"""Typed configuration models for .ai-engineering/manifest.yml."""

from ai_engineering.config.loader import load_manifest_config
from ai_engineering.config.manifest import ManifestConfig

__all__ = ["ManifestConfig", "load_manifest_config"]
