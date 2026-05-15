#!/usr/bin/env python3
"""Schematron validation in Python via saxonche (Saxon's Python API).

Usage:  python validate_schematron.py <schema.sch> <xml-file> [--fail-on ...]
Exit:   0 = no error-role failed-assert, 1 = at least one, 2 = setup error

basic_checks.sch uses queryBinding="xslt2", so an XSLT 2.0 processor is
required. `lxml` only does XSLT 1.0 and CANNOT run this ruleset — saxonche
(`pip install saxonche`) embeds Saxon's XSLT 3.0 engine.

The SchXslt pipeline stylesheets are reused straight out of the SchXslt CLI jar
(this Python stack will resolve it via pyproject.toml once migrated; the Java
Schematron example already runs standalone via the Maven Wrapper). The whole
`xslt/` tree is extracted
to a temp dir so the pipeline's relative xsl:import/include resolve, then:
  1) compile the .sch into an SVRL stylesheet,
  2) apply it to the instance to get SVRL,
  3) classify with the shared svrl-summary.py.
"""
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
CLI_JAR = REPO_ROOT / ".lib" / "schxslt-cli-1.10.1.jar"


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: validate_schematron.py <schema.sch> <xml-file> "
              "[--fail-on error|any]", file=sys.stderr)
        return 2
    sch, xml = sys.argv[1], sys.argv[2]

    try:
        from saxonche import PySaxonProcessor
    except ImportError:
        print("saxonche not installed. Run: pip install saxonche\n"
              "(lxml cannot be used here — basic_checks.sch is XSLT 2.0.)",
              file=sys.stderr)
        return 2

    if not CLI_JAR.is_file():
        print("SchXslt jar missing (this Python stack is migrated to a build "
              "system in a later phase; the Java example already runs "
              "standalone: ./mvnw -pl Schematron_DataQuality_Checks/"
              "Basic_Checks/invocation compile exec:java)", file=sys.stderr)
        return 2

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        with zipfile.ZipFile(CLI_JAR) as z:
            for n in z.namelist():
                if n.startswith("xslt/"):
                    z.extract(n, tmp)
        pipeline = tmp / "xslt" / "2.0" / "pipeline-for-svrl.xsl"
        compiled = tmp / "compiled.xsl"
        svrl = tmp / "report.svrl"

        with PySaxonProcessor(license=False) as proc:
            xslt = proc.new_xslt30_processor()
            xslt.transform_to_file(source_file=sch,
                                   stylesheet_file=str(pipeline),
                                   output_file=str(compiled))
            xslt.transform_to_file(source_file=xml,
                                   stylesheet_file=str(compiled),
                                   output_file=str(svrl))

        return subprocess.call([sys.executable, str(HERE / "svrl-summary.py"),
                                str(svrl), *sys.argv[3:]])


if __name__ == "__main__":
    sys.exit(main())
