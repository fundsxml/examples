#!/usr/bin/env python3
"""Run an XSLT 2.0 stylesheet via saxonche (Saxon's Python API).

Usage:  python run_transform.py <stylesheet.xslt> <input.xml> <output> [k=v ...]
Exit:   0 success, 2 setup error.

The repo's stylesheets are XSLT 2.0. `lxml` only supports XSLT 1.0 and cannot
run them — `pip install saxonche` provides Saxon's XSLT 3.0 engine.
"""
import sys


def main() -> int:
    if len(sys.argv) < 4:
        print("usage: run_transform.py <xslt> <input.xml> <output> [k=v ...]",
              file=sys.stderr)
        return 2
    xsl, src, out = sys.argv[1:4]
    params = dict(p.split("=", 1) for p in sys.argv[4:] if "=" in p)

    try:
        from saxonche import PySaxonProcessor
    except ImportError:
        print("saxonche not installed. Run: pip install saxonche",
              file=sys.stderr)
        return 2

    with PySaxonProcessor(license=False) as proc:
        xslt = proc.new_xslt30_processor()
        for k, v in params.items():
            xslt.set_parameter(k, proc.make_string_value(v))
        xslt.transform_to_file(source_file=src, stylesheet_file=xsl,
                               output_file=out)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
