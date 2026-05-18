#!/usr/bin/env python3
"""XSD validation in Python via lxml.

Standalone & cross-platform — no bash, no prior tool step (works on Windows).
After `pip install -e .` (see pyproject.toml):

  python XSD_Validation/python/validate.py <schema> <xml-file>
Exit:   0 = valid, 1 = invalid, 2 = usage/setup error

`<schema>` is a path to an XSD file OR a remote URL — e.g. the official
release: https://github.com/fundsxml/schema/releases/download/4.2.9/FundsXML.xsd
You give the validator exactly two things: the schema and the instance. No
version, no env var, no cache, no resolver — whatever you point at is used
as-is. For FundsXML 4.2.9+ the schema imports xmldsig-core-schema.xsd via a
relative path, so that sibling must be reachable next to `<schema>` (it is, in
the official release directory and in any complete local copy).

A URL schema (and, when it imports it, the xmldsig sibling) is fetched into a
temp dir with urllib first — libxml2 as built into lxml has no HTTP loader, so
`etree.parse` cannot read a URL itself; doing the fetch here also keeps the
official-release 302 handled. Validation then runs against that local copy.

Security: the *instance* parser is hardened against XXE / entity-expansion
(no_network=True, resolve_entities=False, no DTD load); FundsXML needs none of
those. Only the trusted, user-supplied schema is fetched over the network.
"""
import sys
import tempfile
import urllib.request
from pathlib import Path

from lxml import etree


def _fetch(url: str, dest: Path) -> None:
    print(f"schema: fetch {url}", file=sys.stderr)
    with urllib.request.urlopen(url, timeout=60) as r:  # follows the 302
        dest.write_bytes(r.read())


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: validate.py <schema> <xml-file>", file=sys.stderr)
        return 2
    schema_arg, xml_path = sys.argv[1], sys.argv[2]

    tmp: tempfile.TemporaryDirectory | None = None
    schema_path = schema_arg
    if schema_arg.startswith(("http://", "https://")):
        tmp = tempfile.TemporaryDirectory()
        local = Path(tmp.name) / "FundsXML.xsd"
        _fetch(schema_arg, local)
        # FundsXML 4.2.9+ imports xmldsig-core-schema.xsd via a relative path;
        # fetch that sibling from the same URL dir only when referenced.
        if "xmldsig-core-schema.xsd" in local.read_text(encoding="utf-8"):
            sib = schema_arg.rsplit("/", 1)[0] + "/xmldsig-core-schema.xsd"
            _fetch(sib, Path(tmp.name) / "xmldsig-core-schema.xsd")
        schema_path = str(local)

    try:
        # Hardened parser for the instance: no network, no entity resolution,
        # no DTD load, no huge-tree blowups.
        safe = etree.XMLParser(no_network=True, resolve_entities=False,
                               load_dtd=False, huge_tree=False)

        schema = etree.XMLSchema(etree.parse(schema_path))
        doc = etree.parse(xml_path, parser=safe)
        if schema.validate(doc):
            print(f"VALID: {xml_path} (schema {schema_arg})")
            return 0

        print(f"INVALID: {xml_path} (schema {schema_arg})", file=sys.stderr)
        for err in schema.error_log:
            print(f"  line {err.line}: {err.message}", file=sys.stderr)
        return 1
    finally:
        if tmp is not None:
            tmp.cleanup()


if __name__ == "__main__":
    sys.exit(main())
