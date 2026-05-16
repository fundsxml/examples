#!/usr/bin/env python3
"""Schematron validation in Python via saxonche (Saxon's Python API).

Usage:  python validate_schematron.py <schema.sch> <xml-file> [--fail-on ...]
Exit:   0 = no error-role failed-assert, 1 = at least one, 2 = setup error

basic_checks.sch uses queryBinding="xslt2", so an XSLT 2.0 processor is
required. `lxml` only does XSLT 1.0 and CANNOT run this ruleset — saxonche
(installed via the repo's pyproject.toml: `pip install -e .`) embeds Saxon's
XSLT 3.0 engine.

Reference variant: SchXslt has no PyPI package, so the SchXslt pipeline
stylesheets are reused straight out of the SchXslt CLI jar, located via
$FUNDSXML_SCHXSLT_JAR or the Maven local repo (see _find_schxslt_jar). The
Java Schematron example is the verified, fully standalone path (Maven
Wrapper). The whole `xslt/` tree is extracted to a temp dir so the
pipeline's relative xsl:import/include resolve, then:
  1) compile the .sch into an SVRL stylesheet,
  2) apply it to the instance to get SVRL,
  3) classify with the shared svrl-summary.py.
"""
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]

# The SchXslt pipeline stylesheets are reused straight out of the SchXslt CLI
# jar. There is no PyPI distribution of SchXslt, so this (reference) Python
# stack locates the jar standalone, in order:
#   1. $FUNDSXML_SCHXSLT_JAR (explicit path)
#   2. the Maven local repo — the Java Schematron module already declares
#      name.dmaus.schxslt:cli:1.10.1, so `./mvnw -pl Schematron_DataQuality_
#      Checks/Basic_Checks/invocation compile` populates ~/.m2 with it.
_SCHXSLT_VERSION = "1.10.1"
_M2 = Path(os.environ.get("MAVEN_REPO_LOCAL",
                          Path.home() / ".m2" / "repository"))


def _find_schxslt_jar() -> Path:
    env = os.environ.get("FUNDSXML_SCHXSLT_JAR")
    if env:
        return Path(env)
    return (_M2 / "name" / "dmaus" / "schxslt" / "cli" / _SCHXSLT_VERSION
            / f"cli-{_SCHXSLT_VERSION}.jar")


CLI_JAR = _find_schxslt_jar()


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
        print(f"SchXslt jar not found at {CLI_JAR}.\n"
              "Set $FUNDSXML_SCHXSLT_JAR, or populate the Maven local repo "
              "once with:\n"
              "  ./mvnw -q -pl Schematron_DataQuality_Checks/Basic_Checks/"
              "invocation compile\n"
              "(the Java Schematron example runs fully standalone via the "
              "Maven Wrapper and is the verified path.)", file=sys.stderr)
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
