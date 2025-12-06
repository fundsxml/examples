# Enhanced FundsXML Data Quality Report

This directory contains an XSLT 1.0 stylesheet that generates a comprehensive, professional HTML dashboard for FundsXML data quality analysis.

## File Overview

| Property | Value |
|----------|-------|
| **File** | `FundsXML_CompleteDQReport_HTML.xsl` |
| **XSLT Version** | 1.0 (maximum compatibility) |
| **Output Format** | HTML (responsive dashboard) |
| **Report Sections** | 10 comprehensive areas |
| **Styling** | Professional gradient design |
| **Sample Output** | `FundsXML Complete Data Quality Report.pdf` |

## Key Features

### Maximum Compatibility (XSLT 1.0)

This stylesheet uses only XSLT 1.0 features, ensuring it works with:
- Any browser's built-in XSLT processor
- xsltproc (pre-installed on macOS/Linux)
- All programming language XML libraries
- Saxon (all versions)
- Microsoft MSXML

### Professional Dashboard Design

- **Gradient headers** - Modern blue theme
- **Sticky navigation** - Quick section access
- **Score cards** - Visual quality metrics
- **Color-coded status** - Instant issue identification
- **Progress bars** - Distribution visualization
- **Print-friendly** - Clean print output
- **Responsive layout** - Grid-based sections

## Report Sections

### 1. Executive Dashboard

High-level quality overview:

| Metric | Description | Visualization |
|--------|-------------|---------------|
| Overall Quality Score | Aggregate score | Large percentage |
| Structure Integrity | Document structure | Percentage card |
| Data Completeness | Required fields | Percentage card |
| Temporal Consistency | Date alignment | Percentage card |
| Value Accuracy | Calculation checks | Percentage card |

**Summary Statistics:**
- Total Funds
- Total Assets
- Total Positions
- Share Classes
- Unique Currencies
- Asset Types

### 2. Document Structure Validation

| Check | Description | Status |
|-------|-------------|--------|
| ControlData Present | Document has control data | PASS/FAIL |
| ContentDate Present | Valid content date | PASS/FAIL |
| Funds Section | Contains fund data | PASS/FAIL |
| Assets Section | Contains asset data | PASS/FAIL |
| Fund Names | All funds have names | PASS/FAIL |
| LEI Format | 20 characters (ISO 17442) | PASS/FAIL |
| Currency Format | 3 characters (ISO 4217) | PASS/FAIL |

### 3. Asset Analysis

**Asset Type Distribution:**
- Visual progress bars for each type
- Count and percentage per type
- Sorted by frequency

**Identifier Completeness:**
| Identifier | Coverage | Status |
|------------|----------|--------|
| ISIN | 90%+ = PASS | Coverage bar |
| SEDOL | 50%+ = PASS | Coverage bar |
| WKN | 50%+ = PASS | Coverage bar |
| Ticker | 50%+ = PASS | Coverage bar |

**Position-Asset Linkage:**
- Orphaned positions (no matching asset)
- Unused assets (not referenced)

### 4. Temporal Consistency

| Validation | Expected | Result |
|------------|----------|--------|
| ContentDate Format | YYYY-MM-DD (10 chars) | Value + Status |
| DocumentGenerated | Present | Timestamp |
| NAV Dates Present | All funds | Count check |
| NAV Date = ContentDate | Alignment | Match check |

### 5. Position Value Validation

| Check | Description | Severity |
|-------|-------------|----------|
| TotalValue Present | All positions have value | ERROR if missing |
| TotalPercentage Present | All have percentage | ERROR if missing |
| Positive Values | No unexpected negatives | WARNING if found |
| Currency Present | All have currency code | ERROR if missing |

**NAV Reconciliation per Fund:**
- Fund NAV value
- Position percentage sum
- Tolerance check (95-105%)

### 6. Share Class Analysis

| Validation | Description |
|------------|-------------|
| ISIN Format | 12 characters |
| NAV Price Present | Price exists |
| Shares Outstanding | Share count exists |
| TNA Present | Total Net Assets exists |

**Per-Fund Detail Table:**
- Share class name
- ISIN
- NAV Price
- Shares
- TNA
- Calculation check (Price × Shares ≈ TNA)

### 7. Currency Exposure Analysis

Per fund breakdown:
| Currency | Total Value | Percentage | Positions | Risk Level |
|----------|-------------|------------|-----------|------------|
| EUR | 100,000,000 | 80% | 15 | BASE |
| USD | 25,000,000 | 20% | 5 | MEDIUM |

**Risk Level Badges:**
- BASE - Fund base currency
- LOW - < 10% exposure
- MEDIUM - 10-25% exposure
- HIGH - > 25% exposure

### 8. Portfolio Composition

**Top 15 Holdings per Fund:**
| Rank | Asset Name | ISIN | Type | Value | % |
|------|------------|------|------|-------|---|
| 1 | Asset A | XX... | EQ | 10M | 8% |
| ... | ... | ... | ... | ... | ... |

### 9. Exposure Analysis

| Check | Description |
|-------|-------------|
| Positions with Exposure | Count with exposure data |
| Total Exposures | Total exposure records |
| Exposure Types | All have type defined |

### 10. Data Integrity Summary

**Comprehensive Validation Matrix:**

| Category | Rule | Issues | Severity | Status |
|----------|------|--------|----------|--------|
| Completeness | Missing Fund Names | 0 | CRITICAL | PASS |
| Identifiers | Invalid LEI Format | 0 | HIGH | PASS |
| Temporal | Missing NAV Dates | 0 | HIGH | PASS |
| Format | Invalid Currency Codes | 0 | MEDIUM | PASS |
| Values | Missing Position Values | 0 | HIGH | PASS |
| Linkage | Orphaned Positions | 0 | CRITICAL | PASS |

**Entity Summary:**
| Entity | Total | With Issues | Quality Score |
|--------|-------|-------------|---------------|
| Funds | X | Y | Z% |
| Assets | X | Y | Z% |
| Positions | X | Y | Z% |
| Share Classes | X | Y | Z% |

## Sample Output

A sample PDF output is included in this directory:
- **File:** `FundsXML Complete Data Quality Report.pdf`
- **Pages:** Multi-page comprehensive report
- **Demonstrates:** All 10 sections with real data

## Running the Transformation

### Command Line Tools (XSLT 1.0 Compatible)

#### xsltproc (macOS/Linux - Fastest)

```bash
# macOS (pre-installed)
xsltproc FundsXML_CompleteDQReport_HTML.xsl input.xml > report.html

# Linux
sudo apt install xsltproc  # if not installed
xsltproc FundsXML_CompleteDQReport_HTML.xsl input.xml > report.html
```

#### Saxon (All Platforms)

```bash
saxon -s:input.xml -xsl:FundsXML_CompleteDQReport_HTML.xsl -o:report.html
```

#### msxsl (Windows)

```cmd
msxsl input.xml FundsXML_CompleteDQReport_HTML.xsl -o report.html
```

#### xmlstarlet (Cross-platform)

```bash
xmlstarlet tr FundsXML_CompleteDQReport_HTML.xsl input.xml > report.html
```

### Platform-Specific Scripts

#### Windows (PowerShell)

```powershell
param(
    [Parameter(Mandatory=$true)]
    [string]$InputXml,

    [string]$OutputHtml = "dq_report.html",
    [switch]$OpenBrowser
)

$XSLT = "FundsXML_CompleteDQReport_HTML.xsl"

# Try xsltproc first (if available via WSL or Cygwin)
if (Get-Command xsltproc -ErrorAction SilentlyContinue) {
    xsltproc $XSLT $InputXml | Out-File -FilePath $OutputHtml -Encoding utf8
}
# Fall back to Saxon
elseif (Test-Path "C:\saxon\saxon-he.jar") {
    java -jar "C:\saxon\saxon-he.jar" -s:$InputXml -xsl:$XSLT -o:$OutputHtml
}
# Fall back to .NET XslCompiledTransform
else {
    $xslt = New-Object System.Xml.Xsl.XslCompiledTransform
    $xslt.Load($XSLT)
    $xslt.Transform($InputXml, $OutputHtml)
}

Write-Host "Report generated: $OutputHtml"

if ($OpenBrowser) {
    Start-Process $OutputHtml
}
```

#### macOS / Linux (Bash)

```bash
#!/bin/bash
# generate_report.sh - Generate FundsXML Data Quality Report

set -e

INPUT="${1:?Usage: $0 <input.xml> [output.html]}"
OUTPUT="${2:-${INPUT%.xml}_report.html}"
XSLT="$(dirname "$0")/FundsXML_CompleteDQReport_HTML.xsl"

echo "Generating report..."
echo "  Input: $INPUT"
echo "  Output: $OUTPUT"

xsltproc "$XSLT" "$INPUT" > "$OUTPUT"

echo "Report generated successfully!"

# Open in browser (optional)
if [ "$3" = "--open" ]; then
    if [[ "$OSTYPE" == "darwin"* ]]; then
        open "$OUTPUT"
    else
        xdg-open "$OUTPUT" 2>/dev/null || echo "Open $OUTPUT in your browser"
    fi
fi
```

## Programming Language Examples

### Java (Built-in XSLT 1.0)

```java
package com.example.fundsxml;

import javax.xml.transform.*;
import javax.xml.transform.stream.*;
import java.io.*;
import java.nio.file.*;
import java.util.*;

/**
 * Enhanced FundsXML Data Quality Report Generator
 * Uses built-in Java XSLT 1.0 processor (no external dependencies)
 */
public class EnhancedReportGenerator {

    private final TransformerFactory factory;
    private final Templates templates;

    public EnhancedReportGenerator(String xsltPath) throws TransformerException {
        this.factory = TransformerFactory.newInstance();
        this.templates = factory.newTemplates(new StreamSource(new File(xsltPath)));
    }

    public String generateReport(String inputXml, String outputHtml)
            throws TransformerException, IOException {

        if (outputHtml == null) {
            outputHtml = inputXml.replaceFirst("\\.[^.]+$", "_report.html");
        }

        Transformer transformer = templates.newTransformer();
        transformer.setOutputProperty(OutputKeys.METHOD, "html");
        transformer.setOutputProperty(OutputKeys.INDENT, "yes");
        transformer.setOutputProperty(OutputKeys.ENCODING, "UTF-8");

        transformer.transform(
            new StreamSource(new File(inputXml)),
            new StreamResult(new FileOutputStream(outputHtml))
        );

        return outputHtml;
    }

    public Map<String, String> generateBatch(List<String> inputFiles, String outputDir)
            throws Exception {

        Files.createDirectories(Paths.get(outputDir));
        Map<String, String> results = new LinkedHashMap<>();

        for (String inputFile : inputFiles) {
            String baseName = Paths.get(inputFile).getFileName().toString()
                .replaceFirst("\\.[^.]+$", "");
            String outputFile = Paths.get(outputDir, baseName + "_report.html").toString();

            try {
                generateReport(inputFile, outputFile);
                results.put(inputFile, outputFile);
                System.out.println("Generated: " + outputFile);
            } catch (Exception e) {
                System.err.println("Error: " + inputFile + " - " + e.getMessage());
                results.put(inputFile, null);
            }
        }

        return results;
    }

    public static void main(String[] args) {
        if (args.length < 1) {
            System.err.println("Usage: java EnhancedReportGenerator <input.xml> [output.html]");
            System.exit(1);
        }

        String xsltPath = System.getenv().getOrDefault(
            "ENHANCED_XSLT", "FundsXML_CompleteDQReport_HTML.xsl");

        try {
            EnhancedReportGenerator generator = new EnhancedReportGenerator(xsltPath);
            String inputXml = args[0];
            String outputHtml = args.length > 1 ? args[1] : null;

            String result = generator.generateReport(inputXml, outputHtml);
            System.out.println("Report generated: " + result);

        } catch (Exception e) {
            System.err.println("Error: " + e.getMessage());
            e.printStackTrace();
            System.exit(2);
        }
    }
}
```

### Python (lxml - No External Dependencies)

```python
#!/usr/bin/env python3
"""
Enhanced FundsXML Data Quality Report Generator
Uses lxml (XSLT 1.0) - works without Saxon
"""

import argparse
import os
import sys
import webbrowser
from pathlib import Path
from typing import Dict, List, Optional

from lxml import etree


class EnhancedReportGenerator:
    """Generates enhanced HTML data quality dashboards from FundsXML"""

    def __init__(self, xslt_path: str = "FundsXML_CompleteDQReport_HTML.xsl"):
        if not os.path.exists(xslt_path):
            raise FileNotFoundError(f"XSLT file not found: {xslt_path}")

        with open(xslt_path, 'rb') as f:
            xslt_doc = etree.parse(f)
        self.transform = etree.XSLT(xslt_doc)

    def generate_report(self, input_xml: str, output_html: str = None) -> str:
        """Generate a single report"""
        if output_html is None:
            output_html = Path(input_xml).stem + "_report.html"

        with open(input_xml, 'rb') as f:
            doc = etree.parse(f)

        result = self.transform(doc)

        with open(output_html, 'wb') as f:
            f.write(etree.tostring(result, pretty_print=True, method='html'))

        return output_html

    def generate_batch(self, input_files: List[str],
                       output_dir: str = "reports") -> Dict[str, Optional[str]]:
        """Generate reports for multiple files"""
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        results = {}

        for input_file in input_files:
            base_name = Path(input_file).stem
            output_file = str(Path(output_dir) / f"{base_name}_report.html")

            try:
                self.generate_report(input_file, output_file)
                results[input_file] = output_file
                print(f"Generated: {output_file}")
            except Exception as e:
                results[input_file] = None
                print(f"Error processing {input_file}: {e}", file=sys.stderr)

        return results


def main():
    parser = argparse.ArgumentParser(
        description='Generate Enhanced FundsXML Data Quality Reports'
    )
    parser.add_argument('input', nargs='+', help='XML file(s) to process')
    parser.add_argument('-o', '--output', help='Output file (single file mode)')
    parser.add_argument('-d', '--output-dir', default='reports',
                        help='Output directory (batch mode)')
    parser.add_argument('-b', '--batch', action='store_true',
                        help='Batch mode for multiple files')
    parser.add_argument('--xslt', default='FundsXML_CompleteDQReport_HTML.xsl',
                        help='Path to XSLT stylesheet')
    parser.add_argument('--open', action='store_true',
                        help='Open report in browser')

    args = parser.parse_args()

    try:
        generator = EnhancedReportGenerator(args.xslt)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)

    if args.batch or len(args.input) > 1:
        results = generator.generate_batch(args.input, args.output_dir)
        success = sum(1 for v in results.values() if v is not None)
        print(f"\nGenerated {success}/{len(results)} reports")
    else:
        output_file = generator.generate_report(args.input[0], args.output)
        print(f"Report generated: {output_file}")

        if args.open:
            webbrowser.open(f"file://{os.path.abspath(output_file)}")


if __name__ == '__main__':
    main()
```

### .NET/C# (Built-in XSLT 1.0)

```csharp
using System;
using System.Collections.Generic;
using System.IO;
using System.Xml;
using System.Xml.Xsl;

namespace FundsXML.Reports
{
    /// <summary>
    /// Enhanced FundsXML Data Quality Report Generator
    /// Uses built-in .NET XSLT 1.0 processor
    /// </summary>
    public class EnhancedReportGenerator
    {
        private readonly XslCompiledTransform _xslt;

        public EnhancedReportGenerator(string xsltPath)
        {
            _xslt = new XslCompiledTransform();
            _xslt.Load(xsltPath);
        }

        public string GenerateReport(string inputXml, string outputHtml = null)
        {
            outputHtml ??= Path.ChangeExtension(inputXml, null) + "_report.html";

            using var writer = XmlWriter.Create(outputHtml, new XmlWriterSettings
            {
                Indent = true,
                OmitXmlDeclaration = true
            });

            _xslt.Transform(inputXml, writer);
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
                    Console.Error.WriteLine($"Error: {inputFile} - {ex.Message}");
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
                Console.WriteLine("Usage: EnhancedReportGenerator <input.xml> [output.html]");
                return 1;
            }

            var xsltPath = Environment.GetEnvironmentVariable("ENHANCED_XSLT")
                ?? "FundsXML_CompleteDQReport_HTML.xsl";

            try
            {
                var generator = new EnhancedReportGenerator(xsltPath);
                var result = generator.GenerateReport(args[0],
                    args.Length > 1 ? args[1] : null);
                Console.WriteLine($"Report generated: {result}");
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

### Node.js (xslt-processor - Pure JavaScript)

```javascript
#!/usr/bin/env node
/**
 * Enhanced FundsXML Data Quality Report Generator
 * Uses xslt-processor (XSLT 1.0, pure JavaScript)
 */

const { Xslt, XmlParser } = require('xslt-processor');
const fs = require('fs');
const path = require('path');
const { program } = require('commander');

class EnhancedReportGenerator {
    constructor(xsltPath) {
        if (!fs.existsSync(xsltPath)) {
            throw new Error(`XSLT file not found: ${xsltPath}`);
        }
        const xsltContent = fs.readFileSync(xsltPath, 'utf8');
        this.xsltDoc = XmlParser.parse(xsltContent);
    }

    generateReport(inputXml, outputHtml = null) {
        if (!outputHtml) {
            outputHtml = inputXml.replace(/\.[^.]+$/, '_report.html');
        }

        const xmlContent = fs.readFileSync(inputXml, 'utf8');
        const xmlDoc = XmlParser.parse(xmlContent);

        const result = Xslt.process(xmlDoc, this.xsltDoc);
        fs.writeFileSync(outputHtml, result);

        return outputHtml;
    }

    generateBatch(inputFiles, outputDir = 'reports') {
        fs.mkdirSync(outputDir, { recursive: true });
        const results = {};

        for (const inputFile of inputFiles) {
            const baseName = path.basename(inputFile, path.extname(inputFile));
            const outputFile = path.join(outputDir, `${baseName}_report.html`);

            try {
                this.generateReport(inputFile, outputFile);
                results[inputFile] = outputFile;
                console.log(`Generated: ${outputFile}`);
            } catch (error) {
                results[inputFile] = null;
                console.error(`Error: ${inputFile} - ${error.message}`);
            }
        }

        return results;
    }
}

program
    .name('enhanced-report-generator')
    .description('Generate Enhanced FundsXML Data Quality Reports')
    .argument('<input...>', 'XML file(s) to process')
    .option('-o, --output <file>', 'Output file')
    .option('-d, --output-dir <dir>', 'Output directory', 'reports')
    .option('-b, --batch', 'Batch mode')
    .option('--xslt <file>', 'XSLT file', 'FundsXML_CompleteDQReport_HTML.xsl')
    .option('--open', 'Open in browser')
    .action((input, options) => {
        try {
            const generator = new EnhancedReportGenerator(options.xslt);

            if (options.batch || input.length > 1) {
                const results = generator.generateBatch(input, options.outputDir);
                const success = Object.values(results).filter(Boolean).length;
                console.log(`\nGenerated ${success}/${Object.keys(results).length} reports`);
            } else {
                const output = generator.generateReport(input[0], options.output);
                console.log(`Report generated: ${output}`);

                if (options.open) {
                    const { exec } = require('child_process');
                    const cmd = process.platform === 'darwin' ? 'open' :
                               process.platform === 'win32' ? 'start' : 'xdg-open';
                    exec(`${cmd} "${path.resolve(output)}"`);
                }
            }
        } catch (error) {
            console.error(`Error: ${error.message}`);
            process.exit(2);
        }
    })
    .parse();
```

### PHP (Built-in XSLTProcessor)

```php
<?php
/**
 * Enhanced FundsXML Data Quality Report Generator
 * Uses built-in PHP XSLTProcessor (XSLT 1.0)
 */

class EnhancedReportGenerator {
    private XSLTProcessor $xslt;
    private DOMDocument $stylesheet;

    public function __construct(string $xsltPath) {
        if (!file_exists($xsltPath)) {
            throw new Exception("XSLT file not found: $xsltPath");
        }

        $this->stylesheet = new DOMDocument();
        $this->stylesheet->load($xsltPath);

        $this->xslt = new XSLTProcessor();
        $this->xslt->importStylesheet($this->stylesheet);
    }

    public function generateReport(string $inputXml, ?string $outputHtml = null): string {
        if ($outputHtml === null) {
            $outputHtml = preg_replace('/\.[^.]+$/', '_report.html', $inputXml);
        }

        $xml = new DOMDocument();
        $xml->load($inputXml);

        $result = $this->xslt->transformToDoc($xml);
        $result->save($outputHtml);

        return $outputHtml;
    }

    public function generateBatch(array $inputFiles, string $outputDir = 'reports'): array {
        if (!is_dir($outputDir)) {
            mkdir($outputDir, 0755, true);
        }

        $results = [];

        foreach ($inputFiles as $inputFile) {
            $baseName = pathinfo($inputFile, PATHINFO_FILENAME);
            $outputFile = "$outputDir/{$baseName}_report.html";

            try {
                $this->generateReport($inputFile, $outputFile);
                $results[$inputFile] = $outputFile;
                echo "Generated: $outputFile\n";
            } catch (Exception $e) {
                $results[$inputFile] = null;
                fwrite(STDERR, "Error: $inputFile - {$e->getMessage()}\n");
            }
        }

        return $results;
    }
}

// CLI usage
if (php_sapi_name() === 'cli' && isset($argv[1])) {
    $xsltPath = getenv('ENHANCED_XSLT') ?: 'FundsXML_CompleteDQReport_HTML.xsl';

    try {
        $generator = new EnhancedReportGenerator($xsltPath);
        $output = $generator->generateReport($argv[1], $argv[2] ?? null);
        echo "Report generated: $output\n";
    } catch (Exception $e) {
        fwrite(STDERR, "Error: {$e->getMessage()}\n");
        exit(2);
    }
}
```

## Generating PDF from HTML

### wkhtmltopdf (Cross-platform)

```bash
# Install
# macOS: brew install wkhtmltopdf
# Linux: sudo apt install wkhtmltopdf
# Windows: choco install wkhtmltopdf

wkhtmltopdf report.html report.pdf
```

### Chrome Headless

```bash
# Generate PDF with Chrome
google-chrome --headless --print-to-pdf=report.pdf report.html

# Or with Chromium
chromium --headless --print-to-pdf=report.pdf report.html
```

### Puppeteer (Node.js)

```javascript
const puppeteer = require('puppeteer');

async function htmlToPdf(htmlFile, pdfFile) {
    const browser = await puppeteer.launch();
    const page = await browser.newPage();
    await page.goto(`file://${require('path').resolve(htmlFile)}`,
        { waitUntil: 'networkidle0' });
    await page.pdf({ path: pdfFile, format: 'A4', printBackground: true });
    await browser.close();
}

htmlToPdf('report.html', 'report.pdf');
```

## Customizing the Report

### Changing Colors/Theme

Edit the CSS in the `<style>` section:

```xslt
/* Change primary color from blue to green */
.main-header {
    background: linear-gradient(135deg, #1b5e20 0%, #43a047 50%, #66bb6a 100%);
}

/* Change section colors */
.section-structure .section-header { border-color: #1b5e20; }
.section-structure .section-header .icon { background: #1b5e20; }
```

### Adding/Removing Sections

Comment out or remove section blocks:

```xslt
<!-- Remove Currency Exposure section -->
<!--
<div id="currency" class="section section-currency">
    ...
</div>
-->
```

### Modifying Quality Thresholds

Adjust percentage checks:

```xslt
<!-- Change tolerance from 95-105% to 98-102% -->
<xsl:when test="$totalPct >= 98 and $totalPct &lt;= 102">
    <span class="status-pass">Within tolerance</span>
</xsl:when>
```

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Empty report | Invalid XML structure | Validate input against FundsXML schema |
| Missing styles | Browser security | Serve via HTTP or use inline styles |
| Encoding issues | Wrong charset | Ensure UTF-8 encoding in source |
| Large file slow | Complex XSLT | Process smaller files or use streaming |

### Browser XSLT Limitations

Some browsers restrict local XSLT processing:

```bash
# Chrome: disable security for local files (development only)
google-chrome --allow-file-access-from-files --disable-web-security

# Better: serve via local HTTP
python -m http.server 8000
# Then open http://localhost:8000/report.html
```

## Resources

- [Parent XSLT README](../README.md)
- [Basic Checks](../Basic_Checks/README.md)
- [FundsXML Sample Files](../../FundsXML_Files/)
- [W3C XSLT 1.0 Specification](https://www.w3.org/TR/xslt)
