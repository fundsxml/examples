#!/usr/bin/env python3
"""Summarize an SVRL report and set an exit code.

SVRL (Schematron Validation Report Language) semantics used here:
  svrl:failed-assert  with role="error"   -> ERROR
  svrl:failed-assert  with role="warning" -> WARNING
  svrl:successful-report                  -> WARNING/INFO (a <report> fired)

Usage:  svrl-summary.py <svrl-file> [--fail-on error|any]
  --fail-on error : exit 1 only if any ERROR-role failed-assert (default)
  --fail-on any   : exit 1 if any failed-assert (incl. warnings)

Shared by the per-stack invocation scripts and by CI so the pass/fail
definition is identical everywhere.
"""
import sys
import xml.etree.ElementTree as ET

SVRL = "{http://purl.oclc.org/dsdl/svrl}"


def main() -> int:
    args = sys.argv[1:]
    fail_on = "error"
    if "--fail-on" in args:
        i = args.index("--fail-on")
        fail_on = args[i + 1]
        del args[i:i + 2]
    if len(args) != 1:
        print("usage: svrl-summary.py <svrl-file> [--fail-on error|any]",
              file=sys.stderr)
        return 2

    root = ET.parse(args[0]).getroot()
    errors, warnings, reports = [], [], []
    for fa in root.iter(f"{SVRL}failed-assert"):
        role = (fa.get("role") or "").lower()
        text = " ".join((fa.findtext(f"{SVRL}text") or "").split())
        (errors if role == "error" else warnings).append((role, text))
    for sr in root.iter(f"{SVRL}successful-report"):
        text = " ".join((sr.findtext(f"{SVRL}text") or "").split())
        reports.append(text)

    for role, text in errors:
        print(f"ERROR   {text}")
    for role, text in warnings:
        print(f"WARNING {text}")
    for text in reports:
        print(f"REPORT  {text}")

    print(f"\nsummary: {len(errors)} error(s), "
          f"{len(warnings)} warning failed-assert(s), "
          f"{len(reports)} report(s)")

    if fail_on == "any" and (errors or warnings):
        return 1
    if errors:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
