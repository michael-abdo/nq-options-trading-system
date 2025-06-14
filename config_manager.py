"""Global configuration manager stub for IFD v3 system.

This is *not* the final implementation.  Its only purpose right now is to
expose a minimal `load_config` helper so that other modules can import it
without runtime errors while the full configuration sub-system is being
ported.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

DEFAULT_CONFIG_PATH = Path("config/profiles/ifd_v3_production.json")


def load_config(path: str | Path | None = None) -> Dict[str, Any]:
    """Load a JSON configuration file.

    Args:
        path: Path to a JSON config.  If *None*, `DEFAULT_CONFIG_PATH` is used.

    Returns
    -------
    dict
        Parsed configuration.  An empty dict is returned if the file cannot
        be found or parsed.
    """

    path = Path(path or DEFAULT_CONFIG_PATH)

    try:
        with path.open("r", encoding="utf-8") as fp:
            return json.load(fp)
    except FileNotFoundError:
        print(f"⚠️  Config file not found: {path} – returning empty config")
        return {}
    except json.JSONDecodeError as exc:
        print(f"⚠️  Invalid JSON in config {path}: {exc}. Returning empty config")
        return {}
