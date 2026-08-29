# XSLT Data Quality Transformations

This directory contains XSLT stylesheets for transforming FundsXML documents into HTML data quality reports.

## What is XSLT?

XSLT (Extensible Stylesheet Language Transformations) is a W3C standard for transforming XML documents into other formats such as HTML, text, or different XML structures. It uses XPath expressions to navigate and select content from XML documents.

### XSLT Versions

| Version | Year | Key Features | Processor Support |
|---------|------|--------------|-------------------|
| **1.0** | 1999 | Basic transformations, templates | Universal |
| **2.0** | 2007 | Grouping, sequences, regex, functions | Saxon, AltovaXML |
| **3.0** | 2017 | Streaming, JSON, maps, higher-order functions | Saxon 9.8+ |

### Files in This Repository

| File | XSLT Version | Description |
|------|--------------|-------------|
| `Basic_Checks/basic_checks.xslt` | 2.0 | Core validation checks, HTML output |
| `Enhanced_Check/FundsXML_CompleteDQReport_HTML.xsl` | 1.0 | Comprehensive dashboard report |
| `Custom_Internal_Checks/custom_internal_checks.xslt` | 2.0 | Parameterised house rules (asset-type whitelist, ID convention, concentration limit, OTC counterparty LEI) |

**Running the XSLT 2.0 stylesheets without installing anything:** the Saxon-HE
runner in `XSLT_Transformations/invocation/` (Maven Wrapper, deps from Maven
Central) and its Python twin (`run_transform.py`, `saxonche`) take
`<xslt> <xml> <out> [name=value…]`, e.g. from the repo root:

```bash
./mvnw -q -pl XSLT_Transformations/invocation compile exec:java \
  -Dexec.args="XSLT_DataQuality_Checks/Basic_Checks/basic_checks.xslt \
               FundsXML_Files/4.2.9/positions/Mixed-Fund_Positions.xml report.html"
```

**Compatibility Notes:**
- XSLT 1.0 files work with any processor (maximum compatibility)
- XSLT 2.0 files require Saxon or equivalent (recommended for full features)

## XSLT Processors

### Command Line Tools

| Tool | XSLT Version | Platform | License | Installation |
|------|--------------|----------|---------|--------------|
| **Saxon-HE** | 1.0, 2.0, 3.0 | Cross-platform (Java) | MPL | Recommended |
| **xsltproc** | 1.0 | macOS, Linux | MIT | Pre-installed/apt |
| **msxsl** | 1.0 | Windows | Microsoft | Download |
| **xmlstarlet** | 1.0 | Cross-platform | MIT | Package managers |

### Installation

#### Saxon-HE (Recommended)

**Windows (Chocolatey)**
```powershell
choco install saxonhe
# Verify installation
saxon --version
```

**Windows (Manual)**
```powershell
# Download latest release
Invoke-WebRequest -Uri "https://github.com/Saxonica/Saxon-HE/releases/download/SaxonHE12-4/SaxonHE12-4J.zip" -OutFile "saxon.zip"
Expand-Archive saxon.zip -DestinationPath C:\saxon
# Add to PATH or use full path: java -jar C:\saxon\saxon-he-12.4.jar
```

**macOS (Homebrew)**
```bash
brew install saxon
# Verify
saxon --version
```

**Linux (Ubuntu/Debian)**
```bash
sudo apt install libsaxonhe-java
# Use as: java -jar /usr/share/java/Saxon-HE.jar
```

**Linux (Manual)**
```bash
wget https://github.com/Saxonica/Saxon-HE/releases/download/SaxonHE12-4/SaxonHE12-4J.zip
sudo unzip SaxonHE12-4J.zip -d /opt/saxon
# Add alias to ~/.bashrc:
echo 'alias saxon="java -jar /opt/saxon/saxon-he-12.4.jar"' >> ~/.bashrc
```

#### xsltproc

**macOS**
```bash
# Pre-installed on macOS
xsltproc --version
```

**Linux (Ubuntu/Debian)**
```bash
sudo apt install xsltproc
```

**Windows (via WSL or Cygwin)**
```bash
# In WSL
sudo apt install xsltproc
```

#### xmlstarlet

**macOS**
```bash
brew install xmlstarlet
```

**Linux**
```bash
sudo apt install xmlstarlet
```

**Windows**
```powershell
choco install xmlstarlet
```

## Basic Usage

### Saxon

```bash
# Basic transformation
saxon -s:input.xml -xsl:stylesheet.xslt -o:output.html

# With parameters
saxon -s:input.xml -xsl:stylesheet.xslt -o:output.html param1=value1

# Verbose output
saxon -s:input.xml -xsl:stylesheet.xslt -o:output.html -t
```

### xsltproc (XSLT 1.0 only)

```bash
# Basic transformation
xsltproc stylesheet.xsl input.xml > output.html

# With parameters
xsltproc --stringparam param1 "value1" stylesheet.xsl input.xml > output.html

# Output to file
xsltproc -o output.html stylesheet.xsl input.xml
```

### xmlstarlet

```bash
# Basic transformation
xmlstarlet tr stylesheet.xsl input.xml > output.html

# With parameters
xmlstarlet tr -s param1="value1" stylesheet.xsl input.xml > output.html
```

## Programming Language Support

### Compatibility Matrix

| Language | XSLT 1.0 Library | XSLT 2.0+ Library |
|----------|------------------|-------------------|
| **Java** | javax.xml.transform | Saxon-HE |
| **Python** | lxml | saxonche |
| **.NET/C#** | System.Xml.Xsl | Saxon.Api (NuGet) |
| **Node.js** | xslt-processor, libxslt | saxon-js |
| **PHP** | XSLTProcessor | shell_exec + Saxon |

### Java

#### Built-in (XSLT 1.0)
```java
import javax.xml.transform.*;
import javax.xml.transform.stream.*;
import java.io.*;

TransformerFactory factory = TransformerFactory.newInstance();
Transformer transformer = factory.newTransformer(
    new StreamSource(new File("stylesheet.xslt")));
transformer.transform(
    new StreamSource(new File("input.xml")),
    new StreamResult(new FileOutputStream("output.html")));
```

#### Saxon (XSLT 2.0/3.0)

**Maven Dependency:**
```xml
<dependency>
    <groupId>net.sf.saxon</groupId>
    <artifactId>Saxon-HE</artifactId>
    <version>12.4</version>
</dependency>
```

**Gradle:**
```groovy
implementation 'net.sf.saxon:Saxon-HE:12.4'
```

### Python

Install both engines once via the repo venv (cross-platform):
```bash
python -m venv .venv && . .venv/bin/activate && pip install -e .
```

#### lxml (XSLT 1.0)

```python
from lxml import etree

xslt = etree.parse("stylesheet.xslt")
transform = etree.XSLT(xslt)
doc = etree.parse("input.xml")
result = transform(doc)

with open("output.html", "wb") as f:
    f.write(etree.tostring(result, pretty_print=True))
```

#### saxonche (XSLT 2.0/3.0)
(installed by the `pip install -e .` above — `lxml` + `saxonche`)

```python
from saxonche import PySaxonProcessor

with PySaxonProcessor(license=False) as proc:
    xslt = proc.new_xslt30_processor()
    xslt.compile_stylesheet(stylesheet_file="stylesheet.xslt")
    xslt.transform_to_file(source_file="input.xml", output_file="output.html")
```

### .NET/C#

#### Built-in (XSLT 1.0)
```csharp
using System.Xml;
using System.Xml.Xsl;

var xslt = new XslCompiledTransform();
xslt.Load("stylesheet.xslt");
xslt.Transform("input.xml", "output.html");
```

#### Saxon.Api (XSLT 2.0/3.0)

**NuGet:**
```bash
dotnet add package Saxon-HE
```

```csharp
using Saxon.Api;

var processor = new Processor();
var compiler = processor.NewXsltCompiler();
var executable = compiler.Compile(new Uri("stylesheet.xslt"));
var transformer = executable.Load30();

using var input = new FileStream("input.xml", FileMode.Open);
using var output = new FileStream("output.html", FileMode.Create);
transformer.Transform(input, processor.NewSerializer(output));
```

### Node.js

#### xslt-processor (XSLT 1.0)
```bash
npm install xslt-processor
```

```javascript
const { Xslt, XmlParser } = require('xslt-processor');
const fs = require('fs');

const xml = fs.readFileSync('input.xml', 'utf8');
const xslt = fs.readFileSync('stylesheet.xslt', 'utf8');

const result = Xslt.process(XmlParser.parse(xml), XmlParser.parse(xslt));
fs.writeFileSync('output.html', result);
```

#### saxon-js (XSLT 2.0/3.0)
```bash
npm install saxon-js
npm install -g xslt3  # For compiling stylesheets
```

```bash
# Pre-compile XSLT to SEF (required for saxon-js)
xslt3 -xsl:stylesheet.xslt -export:stylesheet.sef.json -t
```

```javascript
const SaxonJS = require('saxon-js');
const fs = require('fs');

const result = await SaxonJS.transform({
    stylesheetFileName: "stylesheet.sef.json",
    sourceFileName: "input.xml",
    destination: "serialized"
});

fs.writeFileSync('output.html', result.principalResult);
```

### PHP

#### Built-in (XSLT 1.0)
```php
$xslt = new XSLTProcessor();
$xsl = new DOMDocument();
$xsl->load('stylesheet.xslt');
$xslt->importStylesheet($xsl);

$xml = new DOMDocument();
$xml->load('input.xml');

$result = $xslt->transformToDoc($xml);
$result->save('output.html');
```

#### Shell Fallback (XSLT 2.0)
```php
$output = shell_exec('java -jar /path/to/saxon.jar -s:input.xml -xsl:stylesheet.xslt');
file_put_contents('output.html', $output);
```

## IDE Integration

### Oxygen XML Editor

1. Open the XSLT stylesheet
2. Go to **Document > Transformation > Configure Transformation Scenario**
3. Create new scenario:
   - Set XSLT version (1.0 or 2.0)
   - Select XML input file
   - Configure output file
4. Run transformation (Ctrl+Shift+T)

### VS Code

**Install XML Extension:**
1. Install "XML" extension by Red Hat
2. Install "XSLT/XPath" extension

**Configure tasks.json:**
```json
{
    "version": "2.0.0",
    "tasks": [
        {
            "label": "XSLT Transform",
            "type": "shell",
            "command": "saxon",
            "args": [
                "-s:${file}",
                "-xsl:${workspaceFolder}/stylesheet.xslt",
                "-o:${fileBasenameNoExtension}_output.html"
            ],
            "group": "build"
        }
    ]
}
```

### IntelliJ IDEA

1. Install "XPathView + XSLT" plugin
2. Right-click XSLT file > **Run As XSLT Stylesheet**
3. Configure:
   - Input XML file
   - Output format and location
   - XSLT processor (built-in or Saxon)

## Available XSLT Files

| File | Description | Version |
|------|-------------|---------|
| [Basic Checks](./Basic_Checks/README.md) | Core validation with 5 check sections | XSLT 2.0 |
| [Enhanced Report](./Enhanced_Check/README.md) | 10-section dashboard with visual indicators | XSLT 1.0 |

## Troubleshooting

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `Unknown function` | XSLT 2.0 function with 1.0 processor | Use Saxon or compatible processor |
| `No match for context item` | Wrong XPath expression | Check document structure |
| `XSLT version not supported` | Processor doesn't support version | Upgrade processor or use compatible XSLT |
| `Output encoding error` | Character encoding mismatch | Set correct encoding in output declaration |
| `Template conflict` | Multiple templates with same priority | Add priority attributes |

### Version-Specific Issues

**XSLT 2.0 Features Not in 1.0:**
- `xsl:for-each-group`
- `xsl:function`
- Regular expressions (`matches()`, `replace()`)
- Sequences (`xs:string*`)
- `format-number()` with picture string

**Workarounds for XSLT 1.0:**
```xslt
<!-- Instead of xsl:for-each-group, use Muenchian grouping -->
<xsl:key name="items-by-type" match="item" use="@type"/>
<xsl:for-each select="item[generate-id() = generate-id(key('items-by-type', @type)[1])]">
    <!-- Grouped processing -->
</xsl:for-each>
```

### Performance Tips

1. **Compile once, run many**: For multiple transformations, compile the stylesheet once
2. **Use keys**: Define `xsl:key` for frequent lookups
3. **Avoid deep recursion**: Use iteration when possible
4. **Streaming**: For large documents, use Saxon streaming (XSLT 3.0)

## Resources

- **W3C XSLT 1.0**: [https://www.w3.org/TR/xslt](https://www.w3.org/TR/xslt)
- **W3C XSLT 2.0**: [https://www.w3.org/TR/xslt20/](https://www.w3.org/TR/xslt20/)
- **W3C XSLT 3.0**: [https://www.w3.org/TR/xslt-30/](https://www.w3.org/TR/xslt-30/)
- **Saxon Documentation**: [https://www.saxonica.com/documentation/](https://www.saxonica.com/documentation/)
- **XSLT Tutorial**: [https://www.w3schools.com/xml/xsl_intro.asp](https://www.w3schools.com/xml/xsl_intro.asp)
