# re-export shim — see tools/skill_domain/validator_skill_frontmatter.py
from tools.skill_domain.validator_skill_frontmatter import *  # noqa: F403
from tools.skill_domain.validator_skill_frontmatter import _check_skill_frontmatter

__all__ = ("_check_skill_frontmatter",)
