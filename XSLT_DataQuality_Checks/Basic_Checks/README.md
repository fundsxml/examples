# Basic XSLT Data Quality Checks

This directory contains an XSLT 2.0 stylesheet that transforms FundsXML documents into HTML data quality reports.

## File Overview

| Property | Value |
|----------|-------|
| **File** | `basic_checks.xslt` |
| **XSLT Version** | 2.0 |
| **Output Format** | HTML |
| **Check Sections** | 5 main validation areas |
| **Purpose** | Generate readable data quality reports |

## Requirements

**XSLT 2.0 processor required** - This stylesheet uses XSLT 2.0 features:
- `xs:string` sequences
- `format-number()` with custom patterns
- `abs()` function

Recommended processors:
- Saxon-HE 10+ (free, open source)
- Saxon-EE (commercial)
- AltovaXML (commercial)

**Note:** xsltproc, libxslt, and built-in browser XSLT do NOT support XSLT 2.0.

## Validation Checks Performed

### 1. Structural Checks

Basic validation of required document elements:

| Check | Severity | Condition |
|-------|----------|-----------|
| Fund LEI | SUCCESS/WARNING | Fund has LEI identifier |
| Portfolio Count | SUCCESS/WARNING | At least one portfolio exists |
| NAV in Fund Currency | SUCCESS/ERROR | Total Asset Value in fund currency |

### 2. ShareClass NAV Summation

Validates that ShareClass NAVs sum to Fund Total NAV:

```
Σ(ShareClass NAV) = Fund Total NAV
```

| Result | Difference | Status |
|--------|------------|--------|
| PASS | < 0.01 | ✓ CHECK PASSED |
| WARNING | 0.01 - 1.00 | ⚠ ROUNDING DIFFERENCE |
| FAIL | ≥ 1.00 | ✗ CHECK FAILED |

### 3. ShareClass Price Calculation

Validates price consistency for each ShareClass:

```
Calculated Price = NAV ÷ Shares Outstanding
```

Compares calculated price to reported price:

| Result | Difference | Status |
|--------|------------|--------|
| OK | < 0.1 | ✓ OK |
| ROUNDING | 0.1 - 1.0 | ⚠ ROUNDING |
| ERROR | ≥ 1.0 | ✗ ERROR |

### 4. Portfolio Position Reconciliation

Validates that position values sum to Fund NAV:

```
Σ(Position TotalValue in Fund Currency) = Fund Total NAV
```

| Result | Difference | Status |
|--------|------------|--------|
| PASS | < 1.00 | ✓ CHECK PASSED |
| FAIL | ≥ 1.00 | ✗ ERROR |

### 5. Percentage Allocation

Validates that position percentages sum to 100%:

```
Σ(Position TotalPercentage) = 100%
```

| Result | Deviation | Status |
|--------|-----------|--------|
| PASS | ≤ 1% | ✓ CHECK PASSED (Tolerance: 1%) |
| FAIL | > 1% | ✗ ERROR |

### 6. Asset-Specific Checks

Additional validations based on asset types:

| Check | Asset Types | Severity |
|-------|-------------|----------|
| Fund Currency Values | All | ERROR if missing |
| ISIN Present | EQ, BO, SC | ERROR if missing |
| Counterparty ID | AC (Account) | WARNING if missing |
| Exposure Data | OP, FU, FX, SW | WARNING if missing |
| Underlying Assets | OP, FU | ERROR if missing |
| Value Direction | All with multi-currency | ERROR if inconsistent |

## Sample Output

The generated HTML report includes:

- **Fund Header** - Name, LEI, NAV Date
- **Structural Checks Section** - Pass/fail indicators
- **Detailed Tables** - Values, calculations, differences
- **Color-Coded Status** - Green (pass), Orange (warning), Red (error)
- **Report Timestamp** - Generation date/time

### Screenshot Description

```
┌─────────────────────────────────────────────────────────────┐
│  FundsXML4 Data Quality Report                              │
│  Report Date: 2025-10-01T12:00:00                          │
│  Content Date: 2025-10-01                                   │
├─────────────────────────────────────────────────────────────┤
│  Fund: Erste Responsible Stock Global                       │
│  LEI: 529900T8BM49AURSDO55                                 │
│  NAV Date: 2025-10-01                                       │
├─────────────────────────────────────────────────────────────┤
│  Structural Checks                                          │
│  ✓ Fund has LEI: 529900T8BM49AURSDO55                      │
│  ✓ File has 1 portfolio(s)                                  │
│  ✓ Fund Total Asset Value is in fund currency (EUR)        │
├─────────────────────────────────────────────────────────────┤
│  1. Check: Sum of ShareClass NAVs vs. Fund NAV             │
│  ┌─────────────────────────────────────┬──────────────────┐ │
│  │ Fund Total Net Asset Value          │ 125,000,000.00   │ │
│  │ ShareClass EUR R01                  │  75,000,000.00   │ │
│  │ ShareClass USD R01                  │  50,000,000.00   │ │
│  │ Sum of all ShareClass NAVs          │ 125,000,000.00   │ │
│  │ Difference                          │          0.00   │ │
│  │ Status                              │ ✓ CHECK PASSED   │ │
│  └─────────────────────────────────────┴──────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Running the Transformation

### Command Line

#### Saxon (All Platforms)

```bash
# Basic usage
saxon -s:input.xml -xsl:basic_checks.xslt -o:report.html

# Full path example
java -jar /opt/saxon/saxon-he.jar \
    -s:../../FundsXML_Files/4.2.9/Mixed-Fund_Positions.xml \
    -xsl:basic_checks.xslt \
    -o:dq_report.html

# Open result in browser
open dq_report.html  # macOS
xdg-open dq_report.html  # Linux
start dq_report.html  # Windows
```

#### Windows (PowerShell)

```powershell
# Set paths
$SAXON = "C:\saxon\saxon-he.jar"
$INPUT = "..\..\FundsXML_Files\4.2.9\Mixed-Fund_Positions.xml"
$XSLT = "basic_checks.xslt"
$OUTPUT = "dq_report.html"

# Run transformation
java -jar $SAXON -s:$INPUT -xsl:$XSLT -o:$OUTPUT

# Open in default browser
Start-Process $OUTPUT
```

#### macOS (Terminal)

```bash
#!/bin/bash
INPUT="${1:-../../FundsXML_Files/4.2.9/Mixed-Fund_Positions.xml}"
OUTPUT="${2:-dq_report.html}"

saxon -s:"$INPUT" -xsl:basic_checks.xslt -o:"$OUTPUT"
open "$OUTPUT"
```

#### Linux (Bash)

```bash
#!/bin/bash
INPUT="${1:-../../FundsXML_Files/4.2.9/Mixed-Fund_Positions.xml}"
OUTPUT="${2:-dq_report.html}"
SAXON_JAR="${SAXON_JAR:-/opt/saxon/saxon-he.jar}"

java -jar "$SAXON_JAR" -s:"$INPUT" -xsl:basic_checks.xslt -o:"$OUTPUT"
xdg-open "$OUTPUT" 2>/dev/null || echo "Report saved to: $OUTPUT"
```

## Programming Language Examples

### Java (Full Application)

```java
package com.example.fundsxml;

import net.sf.saxon.s9api.*;
import javax.xml.transform.stream.StreamSource;
import java.io.*;
import java.nio.file.*;
import java.util.*;

/**
 * FundsXML Data Quality Report Generator
 * Usage: java DQReportGenerator <input.xml> [output.html]
 */
public class DQReportGenerator {

    private final Processor processor;
    private final XsltExecutable stylesheet;

    public DQReportGenerator(String xsltPath) throws SaxonApiException {
        this.processor = new Processor(false);
        XsltCompiler compiler = processor.newXsltCompiler();
        this.stylesheet = compiler.compile(new StreamSource(new File(xsltPath)));
    }

    public void generateReport(String inputXml, String outputHtml) throws SaxonApiException {
        Xslt30Transformer transformer = stylesheet.load30();
        Serializer serializer = processor.newSerializer(new File(outputHtml));
        serializer.setOutputProperty(Serializer.Property.METHOD, "html");
        serializer.setOutputProperty(Serializer.Property.INDENT, "yes");

        transformer.transform(new StreamSource(new File(inputXml)), serializer);
    }

    public void generateBatch(List<String> inputFiles, String outputDir) throws Exception {
        Files.createDirectories(Paths.get(outputDir));

        for (String inputFile : inputFiles) {
            String baseName = Paths.get(inputFile).getFileName().toString()
                .replaceFirst("[.][^.]+$", "");
            String outputFile = Paths.get(outputDir, baseName + "_report.html").toString();

            try {
                generateReport(inputFile, outputFile);
                System.out.println("Generated: " + outputFile);
            } catch (SaxonApiException e) {
                System.err.println("Error processing " + inputFile + ": " + e.getMessage());
            }
        }
    }

    public static void main(String[] args) {
        if (args.length < 1) {
            System.err.println("Usage: DQReportGenerator <input.xml> [output.html]");
            System.err.println("       DQReportGenerator --batch <file1.xml> <file2.xml> ... --output-dir <dir>");
            System.exit(1);
        }

        String xsltPath = System.getenv().getOrDefault("BASIC_CHECKS_XSLT", "basic_checks.xslt");

        try {
            DQReportGenerator generator = new DQReportGenerator(xsltPath);

            if ("--batch".equals(args[0])) {
                List<String> files = new ArrayList<>();
                String outputDir = "reports";

                for (int i = 1; i < args.length; i++) {
                    if ("--output-dir".equals(args[i]) && i + 1 < args.length) {
                        outputDir = args[++i];
                    } else {
                        files.add(args[i]);
                    }
                }

                generator.generateBatch(files, outputDir);
            } else {
                String inputXml = args[0];
                String outputHtml = args.length > 1 ? args[1] :
                    inputXml.replaceFirst("[.][^.]+$", "_report.html");

                generator.generateReport(inputXml, outputHtml);
                System.out.println("Report generated: " + outputHtml);
            }

        } catch (Exception e) {
            System.err.println("Error: " + e.getMessage());
            e.printStackTrace();
            System.exit(2);
        }
    }
}
```

**Maven pom.xml:**
```xml
<dependencies>
    <dependency>
        <groupId>net.sf.saxon</groupId>
        <artifactId>Saxon-HE</artifactId>
        <version>12.4</version>
    </dependency>
</dependencies>
```

### Python (Full Application)

```python
#!/usr/bin/env python3
"""
FundsXML Data Quality Report Generator
Usage: python dq_report_generator.py <input.xml> [--output FILE] [--batch]
"""

import argparse
import sys
import os
from pathlib import Path
from datetime import datetime

try:
    from saxonche import PySaxonProcessor
    SAXON_AVAILABLE = True
except ImportError:
    SAXON_AVAILABLE = False


class DQReportGenerator:
    """Generates HTML data quality reports from FundsXML files"""

    def __init__(self, xslt_path: str = "basic_checks.xslt"):
        if not SAXON_AVAILABLE:
            raise RuntimeError("saxonche is required. Install with: pip install saxonche")

        self.processor = PySaxonProcessor(license=False)
        self.xslt_processor = self.processor.new_xslt30_processor()

        if not os.path.exists(xslt_path):
            raise FileNotFoundError(f"XSLT file not found: {xslt_path}")

        self.xslt_processor.compile_stylesheet(stylesheet_file=xslt_path)

    def generate_report(self, input_xml: str, output_html: str = None) -> str:
        """Generate a single report"""
        if output_html is None:
            output_html = Path(input_xml).stem + "_report.html"

        input_path = str(Path(input_xml).absolute())
        output_path = str(Path(output_html).absolute())

        self.xslt_processor.transform_to_file(
            source_file=input_path,
            output_file=output_path
        )

        return output_path

    def generate_batch(self, input_files: list, output_dir: str = "reports") -> dict:
        """Generate reports for multiple files"""
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        results = {}

        for input_file in input_files:
            base_name = Path(input_file).stem
            output_file = str(Path(output_dir) / f"{base_name}_report.html")

            try:
                self.generate_report(input_file, output_file)
                results[input_file] = {"status": "success", "output": output_file}
                print(f"Generated: {output_file}")
            except Exception as e:
                results[input_file] = {"status": "error", "message": str(e)}
                print(f"Error processing {input_file}: {e}", file=sys.stderr)

        return results


def main():
    parser = argparse.ArgumentParser(
        description='Generate FundsXML Data Quality Reports',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python dq_report_generator.py input.xml
  python dq_report_generator.py input.xml --output report.html
  python dq_report_generator.py *.xml --batch --output-dir reports/
        """
    )
    parser.add_argument('input', nargs='+', help='XML file(s) to process')
    parser.add_argument('--output', '-o', help='Output file (single file mode)')
    parser.add_argument('--output-dir', '-d', default='reports',
                        help='Output directory (batch mode)')
    parser.add_argument('--batch', '-b', action='store_true',
                        help='Batch mode for multiple files')
    parser.add_argument('--xslt', default='basic_checks.xslt',
                        help='Path to XSLT stylesheet')
    parser.add_argument('--open', action='store_true',
                        help='Open report in browser after generation')

    args = parser.parse_args()

    try:
        generator = DQReportGenerator(args.xslt)
    except Exception as e:
        print(f"Error initializing generator: {e}", file=sys.stderr)
        sys.exit(2)

    if args.batch or len(args.input) > 1:
        # Batch mode
        results = generator.generate_batch(args.input, args.output_dir)
        success = sum(1 for r in results.values() if r["status"] == "success")
        print(f"\nProcessed {len(results)} files, {success} successful")
    else:
        # Single file mode
        input_file = args.input[0]
        output_file = generator.generate_report(input_file, args.output)
        print(f"Report generated: {output_file}")

        if args.open:
            import webbrowser
            webbrowser.open(f"file://{os.path.abspath(output_file)}")


if __name__ == '__main__':
    main()
```

### .NET/C# (Full Application)

```csharp
using System;
using System.Collections.Generic;
using System.IO;
using Saxon.Api;

namespace FundsXML.Reports
{
    /// <summary>
    /// FundsXML Data Quality Report Generator
    /// </summary>
    public class DQReportGenerator
    {
        private readonly Processor _processor;
        private readonly XsltExecutable _stylesheet;

        public DQReportGenerator(string xsltPath)
        {
            _processor = new Processor();
            var compiler = _processor.NewXsltCompiler();
            _stylesheet = compiler.Compile(new Uri(Path.GetFullPath(xsltPath)));
        }

        public string GenerateReport(string inputXml, string outputHtml = null)
        {
            outputHtml ??= Path.ChangeExtension(inputXml, null) + "_report.html";

            var transformer = _stylesheet.Load30();
            using var input = new FileStream(inputXml, FileMode.Open, FileAccess.Read);
            using var output = new FileStream(outputHtml, FileMode.Create, FileAccess.Write);

            var serializer = _processor.NewSerializer(output);
            serializer.SetOutputProperty(Serializer.METHOD, "html");
            serializer.SetOutputProperty(Serializer.INDENT, "yes");

            transformer.Transform(input, serializer);
            return outputHtml;
        }

        public Dictionary<string, string> GenerateBatch(
            IEnumerable<string> inputFiles, string outputDir = "reports")
        {
            Directory.CreateDirectory(outputDir);
            var results = new Dictionary<string, string>();

            foreach (var inputFile in inputFiles)
            {
                var baseName = Path.GetFileNameWithoutExtension(inputFile);
                var outputFile = Path.Combine(outputDir, $"{baseName}_report.html");

                try
                {
                    GenerateReport(inputFile, outputFile);
                    results[inputFile] = outputFile;
                    Console.WriteLine($"Generated: {outputFile}");
                }
                catch (Exception ex)
                {
                    Console.Error.WriteLine($"Error processing {inputFile}: {ex.Message}");
                    results[inputFile] = null;
                }
            }

            return results;
        }
    }

    class Program
    {
        static int Main(string[] args)
        {
            if (args.Length < 1)
            {
                Console.WriteLine("Usage: DQReportGenerator <input.xml> [output.html]");
                Console.WriteLine("       DQReportGenerator --batch <files...> --output-dir <dir>");
                return 1;
            }

            var xsltPath = Environment.GetEnvironmentVariable("BASIC_CHECKS_XSLT")
                ?? "basic_checks.xslt";

            try
            {
                var generator = new DQReportGenerator(xsltPath);

                if (args[0] == "--batch")
                {
                    var files = new List<string>();
                    var outputDir = "reports";

                    for (int i = 1; i < args.Length; i++)
                    {
                        if (args[i] == "--output-dir" && i + 1 < args.Length)
                            outputDir = args[++i];
                        else
                            files.Add(args[i]);
                    }

                    generator.GenerateBatch(files, outputDir);
                }
                else
                {
                    var inputXml = args[0];
                    var outputHtml = args.Length > 1 ? args[1] : null;
                    var result = generator.GenerateReport(inputXml, outputHtml);
                    Console.WriteLine($"Report generated: {result}");
                }

                return 0;
            }
            catch (Exception ex)
            {
                Console.Error.WriteLine($"Error: {ex.Message}");
                return 2;
            }
        }
    }
}
```

### Node.js (Full Application)

```javascript
#!/usr/bin/env node
/**
 * FundsXML Data Quality Report Generator
 * Usage: node dq-report-generator.js <input.xml> [--output FILE]
 */

const SaxonJS = require('saxon-js');
const fs = require('fs');
const path = require('path');
const { program } = require('commander');

class DQReportGenerator {
    constructor(sefPath) {
        this.sefPath = sefPath;
        this.stylesheet = null;
    }

    async initialize() {
        // Load pre-compiled SEF
        if (!fs.existsSync(this.sefPath)) {
            throw new Error(`SEF file not found: ${this.sefPath}

Compile with: xslt3 -xsl:basic_checks.xslt -export:basic_checks.sef.json -t`);
        }
        this.stylesheet = JSON.parse(fs.readFileSync(this.sefPath, 'utf8'));
    }

    async generateReport(inputXml, outputHtml = null) {
        if (!this.stylesheet) {
            await this.initialize();
        }

        outputHtml = outputHtml || inputXml.replace(/\.[^.]+$/, '_report.html');

        const result = await SaxonJS.transform({
            stylesheetInternal: this.stylesheet,
            sourceFileName: path.resolve(inputXml),
            destination: 'serialized'
        });

        fs.writeFileSync(outputHtml, result.principalResult);
        return outputHtml;
    }

    async generateBatch(inputFiles, outputDir = 'reports') {
        fs.mkdirSync(outputDir, { recursive: true });
        const results = {};

        for (const inputFile of inputFiles) {
            const baseName = path.basename(inputFile, path.extname(inputFile));
            const outputFile = path.join(outputDir, `${baseName}_report.html`);

            try {
                await this.generateReport(inputFile, outputFile);
                results[inputFile] = { status: 'success', output: outputFile };
                console.log(`Generated: ${outputFile}`);
            } catch (error) {
                results[inputFile] = { status: 'error', message: error.message };
                console.error(`Error processing ${inputFile}: ${error.message}`);
            }
        }

        return results;
    }
}

async function main() {
    program
        .name('dq-report-generator')
        .description('Generate FundsXML Data Quality Reports')
        .argument('<input...>', 'XML file(s) to process')
        .option('-o, --output <file>', 'Output file (single file mode)')
        .option('-d, --output-dir <dir>', 'Output directory (batch mode)', 'reports')
        .option('-b, --batch', 'Batch mode for multiple files')
        .option('--sef <file>', 'Path to compiled SEF file', 'basic_checks.sef.json')
        .option('--open', 'Open report in browser')
        .parse();

    const options = program.opts();
    const inputFiles = program.args;

    const generator = new DQReportGenerator(options.sef);

    try {
        await generator.initialize();
    } catch (error) {
        console.error(`Error: ${error.message}`);
        process.exit(2);
    }

    if (options.batch || inputFiles.length > 1) {
        const results = await generator.generateBatch(inputFiles, options.outputDir);
        const success = Object.values(results).filter(r => r.status === 'success').length;
        console.log(`\nProcessed ${Object.keys(results).length} files, ${success} successful`);
    } else {
        const outputFile = await generator.generateReport(inputFiles[0], options.output);
        console.log(`Report generated: ${outputFile}`);

        if (options.open) {
            const { exec } = require('child_process');
            const cmd = process.platform === 'darwin' ? 'open' :
                       process.platform === 'win32' ? 'start' : 'xdg-open';
            exec(`${cmd} "${path.resolve(outputFile)}"`);
        }
    }
}

main().catch(console.error);
```

**Compile XSLT to SEF first:**
```bash
npm install -g xslt3
xslt3 -xsl:basic_checks.xslt -export:basic_checks.sef.json -t
```

## Customizing the Report

### Changing Styles

Modify the CSS in the `<style>` section:

```xslt
<style>
    /* Change success color from green to blue */
    .check-passed { color: #0066cc; font-weight: bold; }

    /* Change table header color */
    th { background: #1a237e; color: white; }
</style>
```

### Adding New Checks

Add new validation logic in the `check-fund` template:

```xslt
<!-- Add custom check -->
<div class="check-result">
    <xsl:attribute name="class">
        <xsl:choose>
            <xsl:when test="your-condition">check-result success</xsl:when>
            <xsl:otherwise>check-result error</xsl:otherwise>
        </xsl:choose>
    </xsl:attribute>
    <xsl:choose>
        <xsl:when test="your-condition">
            <span class="check-passed">✓ Custom check passed</span>
        </xsl:when>
        <xsl:otherwise>
            <span class="check-failed">✗ Custom check failed</span>
        </xsl:otherwise>
    </xsl:choose>
</div>
```

## Troubleshooting

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| "Unknown function: abs" | XSLT 1.0 processor | Use Saxon-HE or other XSLT 2.0 processor |
| "No context item" | Empty document | Check input XML is valid FundsXML |
| "Transform failed" | XSLT error | Check XSLT file path and syntax |
| "Empty output" | No Fund elements | Verify document structure |

### Debug Tips

1. **Check input:** Validate input XML with `xmllint --noout input.xml`
2. **Verbose mode:** Add `-t` flag to Saxon for timing info
3. **Test XPath:** Use Oxygen XML or online XPath testers

## Resources

- [Parent XSLT README](../README.md)
- [Enhanced Report](../Enhanced_Check/README.md)
- [Saxon Documentation](https://www.saxonica.com/documentation/)
