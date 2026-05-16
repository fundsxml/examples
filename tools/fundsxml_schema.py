"""Resolve the official FundsXML XSD for a given version — standalone &
cross-platform, no bash, no prior tool step.

This is the Python counterpart of the in-language resolver used by the Java
example (XSD_Validation/java/XsdValidate.java). Same 3-step convention in every
stack:

  1. ``$FUNDSXML_SCHEMA_DIR`` — a directory holding ``FundsXML.xsd`` (plus the
     ``xmldsig-core-schema.xsd`` sibling for 4.2.9+). Used as-is, NO network.
     The escape hatch for locked-down corporate networks / offline use.
  2. ``<repo>/.schema-cache/<version>/FundsXML.xsd`` — reused if present.
  3. download from the official GitHub release (following the 302), caching
     into ``.schema-cache/<version>/``; the relative ``xmldsig-core-schema.xsd``
     sibling is fetched only when ``FundsXML.xsd`` actually imports it (4.2.9+).

The source of truth stays the official release URL — no committed catalog.
``urllib`` follows the GitHub 302 to objects.githubusercontent.com on its own.

Installed as a top-level module via the repo's ``pyproject.toml`` (``pip
install -e .``), so every Python example can ``from fundsxml_schema import
resolve_schema``. Also runnable directly::

    python -m fundsxml_schema 4.2.9            # prints the resolved path
"""
from __future__ import annotations

import os
import sys
import tempfile
import urllib.request
from pathlib import Path

RELEASE_BASE = "https://github.com/fundsxml/schema/releases/download/"

# tools/fundsxml_schema.py -> repo root is one level up. An editable install
# keeps __file__ pointing at this source file, so this stays correct.
_DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[1]


def _download(url: str, out: Path) -> None:
    """GET *url* (urllib follows the GitHub 302) atomically into *out*."""
    print(f"schema: fetch {url}", file=sys.stderr)
    with urllib.request.urlopen(url, timeout=60) as resp:  # noqa: S310 (trusted host)
        if resp.status != 200:
            raise RuntimeError(f"download failed (HTTP {resp.status}): {url}")
        data = resp.read()
    out.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(out.parent), suffix=".part")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        os.replace(tmp, out)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def resolve_schema(version: str, repo_root: Path | None = None) -> Path:
    """Return a local path to ``FundsXML.xsd`` for *version* (see module doc)."""
    # 1. Offline / corporate-network escape hatch: a hand-placed copy.
    env_dir = os.environ.get("FUNDSXML_SCHEMA_DIR")
    if env_dir:
        xsd = Path(env_dir) / "FundsXML.xsd"
        if not xsd.is_file():
            raise FileNotFoundError(
                f"FUNDSXML_SCHEMA_DIR set but {xsd} not found")
        print(f"schema: using $FUNDSXML_SCHEMA_DIR -> {xsd}", file=sys.stderr)
        return xsd

    root = Path(repo_root) if repo_root else _DEFAULT_REPO_ROOT
    cache_dir = root / ".schema-cache" / version
    xsd = cache_dir / "FundsXML.xsd"

    # 2. Local cache (shared by every stack, gitignored).
    if xsd.is_file():
        print(f"schema: cached -> {xsd}", file=sys.stderr)
        return xsd

    # 3. Download from the official release (source of truth).
    _download(f"{RELEASE_BASE}{version}/FundsXML.xsd", xsd)
    # From 4.2.9 on, FundsXML.xsd imports xmldsig-core-schema.xsd via a
    # relative path — it must sit next to FundsXML.xsd or the schema does not
    # compile. Fetch the sibling only when it is actually referenced.
    if "xmldsig-core-schema.xsd" in xsd.read_text(encoding="utf-8"):
        _download(f"{RELEASE_BASE}{version}/xmldsig-core-schema.xsd",
                  cache_dir / "xmldsig-core-schema.xsd")
    return xsd


def _main(argv: list[str]) -> int:
    if not 1 <= len(argv) <= 2:
        print("usage: python -m fundsxml_schema <version> [repo-root]",
              file=sys.stderr)
        return 2
    version = argv[0]
    root = Path(argv[1]) if len(argv) == 2 else None
    print(resolve_schema(version, root))      # path on stdout (scriptable)
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
