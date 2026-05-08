# re-export shim — see tools/skill_domain/validator_cross_references.py
from skill_domain.validator_cross_references import *  # noqa: F403
from skill_domain.validator_cross_references import _check_cross_references

__all__ = ("_check_cross_references",)
