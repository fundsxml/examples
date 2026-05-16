#!/usr/bin/env python3
"""XSD validation in Python via lxml.

Standalone & cross-platform — no bash, no prior tool step (works on Windows).
After `pip install -e .` (see pyproject.toml):

  python XSD_Validation/python/validate.py <version> <xml-file>
Exit:   0 = valid, 1 = invalid, 2 = usage/setup error

The official released schema is obtained by this program itself via the shared
`fundsxml_schema` resolver: $FUNDSXML_SCHEMA_DIR (offline/corporate escape
hatch) -> .schema-cache/ -> download from the official GitHub release
(following the 302; fetching the relative xmldsig-core-schema.xsd sibling that
FundsXML 4.2.9+ imports). The official release stays the source of truth.

Security: the XML parser is hardened against XXE / entity-expansion
(no_network=True, resolve_entities=False, no DTD load). FundsXML needs none
of those features.
"""
import sys

from lxml import etree

from fundsxml_schema import resolve_schema


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: validate.py <version> <xml-file>", file=sys.stderr)
        return 2
    version, xml_path = sys.argv[1], sys.argv[2]

    schema_path = resolve_schema(version)

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
