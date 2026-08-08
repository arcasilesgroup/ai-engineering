"""Both halves of the product on the path: the package, and the guards.

The guards are deliberately not importable as part of the package — they are standard
library Python executed by path, because on the hot path `import ai_engineering` costs
about 110 ms. Tests reach them the same way the dispatcher does.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for folder in ("src", "hooks"):
    sys.path.insert(0, str(ROOT / folder))
