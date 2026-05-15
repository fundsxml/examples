#!/usr/bin/env python3
"""Run an XQuery against FundsXML via saxonche (Saxon's Python API).

Usage:  python run_xquery.py <query.xq> <input.xml> [k=v ...]
Exit:   0 success, 2 setup error.

`pip install saxonche` provides Saxon's XQuery 3.1 engine. lxml has no XQuery.
External query variables are passed as k=v args (string-typed), e.g. n=5.
"""
import sys


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: run_xquery.py <query.xq> <input.xml> [k=v ...]",
              file=sys.stderr)
        return 2
    query, src = sys.argv[1], sys.argv[2]
    params = dict(p.split("=", 1) for p in sys.argv[3:] if "=" in p)

    try:
        from saxonche import PySaxonProcessor
    except ImportError:
        print("saxonche not installed. Run: pip install saxonche",
              file=sys.stderr)
        return 2

    with PySaxonProcessor(license=False) as proc:
        xq = proc.new_xquery_processor()
        xq.set_context(file_name=src)
        for k, v in params.items():
            xq.set_parameter(k, proc.make_string_value(v))
        xq.set_query_file(query)
        sys.stdout.write(xq.run_query_to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
