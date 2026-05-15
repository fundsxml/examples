#!/usr/bin/env python3
"""XSD validation in Python via lxml.

Usage:  python XSD_Validation/python/validate.py <version> <xml-file>
Exit:   0 = valid, 1 = invalid, 2 = usage/setup error

Validates against the official released schema, materialized locally by
tools/fetch-schema.sh (handles the GitHub 302 redirect and the relative
xmldsig-core-schema.xsd import that FundsXML 4.2.9+ requires).

Security: the XML parser is hardened against XXE / entity-expansion
(no_network=True, resolve_entities=False, no DTD load). FundsXML needs none
of those features.
"""
import subprocess
import sys
from pathlib import Path

from lxml import etree

REPO_ROOT = Path(__file__).resolve().parents[2]


def ensure_schema(version: str) -> Path:
    schema = REPO_ROOT / ".schema-cache" / version / "FundsXML.xsd"
    if not schema.is_file():
        print(f"schema not cached; fetching official release {version}...",
              file=sys.stderr)
        subprocess.run([str(REPO_ROOT / "tools" / "fetch-schema.sh"), version],
                       check=True, stdout=subprocess.DEVNULL)
    return schema


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: validate.py <version> <xml-file>", file=sys.stderr)
        return 2
    version, xml_path = sys.argv[1], sys.argv[2]

    schema_path = ensure_schema(version)

    # Hardened parser: no network, no entity resolution, no huge-tree blowups.
    safe = etree.XMLParser(no_network=True, resolve_entities=False,
                           load_dtd=False, huge_tree=False)

    # The schema itself is parsed with network access so its relative
    # xmldsig-core-schema.xsd import (4.2.9+) resolves from the same dir.
    schema_doc = etree.parse(str(schema_path))
    schema = etree.XMLSchema(schema_doc)

    doc = etree.parse(xml_path, parser=safe)
    if schema.validate(doc):
        print(f"VALID: {xml_path} (FundsXML {version})")
        return 0

    print(f"INVALID: {xml_path} (FundsXML {version})", file=sys.stderr)
    for err in schema.error_log:
        print(f"  line {err.line}: {err.message}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
