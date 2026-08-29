<?xml version="1.0" encoding="UTF-8"?>
<!--
  Custom_Internal_Checks — XSLT 2.0, HTML report.

  Example COMPANY-INTERNAL data-quality rules (not part of the FundsXML
  standard). These illustrate the kind of house rules an asset manager layers
  on top of schema + Schematron validation:

    R1  AssetType whitelist  — the firm only holds an approved set of asset
        types; anything else is flagged.
    R2  Position UniqueID convention — internal IDs must match ID_<3 digits>.
    R3  Concentration limit — no single position may exceed 20% of fund NAV.
    R4  Counterparty LEI on OTC — OTC derivatives (FX, SW) must carry a
        counterparty LEI.

  FundsXML 4.x has no namespace — XPath uses bare element names.
  Output: a self-contained HTML report; one section per rule.
-->
<xsl:stylesheet version="2.0"
                xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:xs="http://www.w3.org/2001/XMLSchema"
                exclude-result-prefixes="xs">

  <xsl:output method="html" indent="yes" encoding="UTF-8"/>

  <!-- Configurable house parameters -->
  <xsl:param name="allowedAssetTypes" as="xs:string"
             select="'EQ BO SC OP FU FX SW WA CE AC RP RE CM'"/>
  <!-- Untyped on purpose: command-line runners (RunTransform, run_transform.py,
       Saxon CLI) hand parameters over as strings, and a typed xs:decimal param
       rejects a string with a type error. Cast where it is used. -->
  <xsl:param name="concentrationLimitPct" select="20"/>
  <xsl:variable name="limitPct" as="xs:decimal" select="xs:decimal($concentrationLimitPct)"/>

  <xsl:variable name="allowed" select="tokenize(normalize-space($allowedAssetTypes),'\s+')"/>

  <xsl:template match="/">
    <html lang="en">
      <head>
        <title>FundsXML Custom Internal DQ Report</title>
        <style>
          body{font-family:system-ui,Arial,sans-serif;margin:2rem;color:#1a1a1a}
          h1{font-size:1.4rem} h2{font-size:1.05rem;margin-top:1.6rem}
          table{border-collapse:collapse;width:100%;margin:.5rem 0}
          th,td{border:1px solid #d0d0d0;padding:.4rem .6rem;text-align:left;font-size:.9rem}
          th{background:#f3f4f6}
          .ok{color:#15803d;font-weight:600}.fail{color:#b91c1c;font-weight:600}
          .pill{display:inline-block;padding:.1rem .5rem;border-radius:1rem;font-size:.8rem}
          .pass{background:#dcfce7;color:#15803d}.viol{background:#fee2e2;color:#b91c1c}
        </style>
      </head>
      <body>
        <h1>Custom Internal Data-Quality Report</h1>
        <p>
          Document: <xsl:value-of select="FundsXML4/ControlData/UniqueDocumentID"/>
          · Version: <xsl:value-of select="(FundsXML4/ControlData/Version,'(none/4.0.0)')[1]"/>
          · Generated: <xsl:value-of select="FundsXML4/ControlData/DocumentGenerated"/>
        </p>

        <!-- R1: AssetType whitelist -->
        <h2>R1 — AssetType whitelist</h2>
        <xsl:variable name="badTypes"
          select="//AssetMasterData/Asset[not(AssetType = $allowed)]"/>
        <xsl:choose>
          <xsl:when test="empty($badTypes)">
            <p class="ok">PASS — all asset types within the approved set
              (<xsl:value-of select="$allowedAssetTypes"/>).</p>
          </xsl:when>
          <xsl:otherwise>
            <p class="fail">FAIL — <xsl:value-of select="count($badTypes)"/> asset(s) with a non-approved type.</p>
            <table><tr><th>UniqueID</th><th>Name</th><th>AssetType</th></tr>
              <xsl:for-each select="$badTypes">
                <tr><td><xsl:value-of select="UniqueID"/></td>
                    <td><xsl:value-of select="Name"/></td>
                    <td><xsl:value-of select="AssetType"/></td></tr>
              </xsl:for-each>
            </table>
          </xsl:otherwise>
        </xsl:choose>

        <!-- R2: UniqueID naming convention -->
        <h2>R2 — Position UniqueID convention (ID_&lt;digits&gt;)</h2>
        <xsl:variable name="badIds"
          select="//Position[not(matches(UniqueID,'^ID_\d{3,}$'))]"/>
        <xsl:choose>
          <xsl:when test="empty($badIds)">
            <p class="ok">PASS — all position IDs follow the convention.</p>
          </xsl:when>
          <xsl:otherwise>
            <p class="fail">FAIL — <xsl:value-of select="count($badIds)"/> non-conforming ID(s).</p>
            <table><tr><th>UniqueID</th></tr>
              <xsl:for-each select="$badIds"><tr><td><xsl:value-of select="UniqueID"/></td></tr></xsl:for-each>
            </table>
          </xsl:otherwise>
        </xsl:choose>

        <!-- R3: Concentration limit -->
        <h2>R3 — Concentration limit (max <xsl:value-of select="$concentrationLimitPct"/>% per position)</h2>
        <xsl:variable name="over"
          select="//Position[number(TotalPercentage) gt $limitPct]"/>
        <xsl:choose>
          <xsl:when test="empty($over)">
            <p class="ok">PASS — no position exceeds the concentration limit.</p>
          </xsl:when>
          <xsl:otherwise>
            <p class="fail">FAIL — <xsl:value-of select="count($over)"/> position(s) over the limit.</p>
            <table><tr><th>UniqueID</th><th>TotalPercentage</th></tr>
              <xsl:for-each select="$over">
                <tr><td><xsl:value-of select="UniqueID"/></td>
                    <td><xsl:value-of select="TotalPercentage"/>%</td></tr>
              </xsl:for-each>
            </table>
          </xsl:otherwise>
        </xsl:choose>

        <!-- R4: OTC derivative counterparty LEI -->
        <h2>R4 — OTC derivative counterparty LEI (FX, SW)</h2>
        <xsl:variable name="otcNoLei"
          select="//AssetMasterData/Asset[AssetType=('FX','SW')]
                   [not(.//Counterparty/Identifiers/LEI)]"/>
        <xsl:choose>
          <xsl:when test="empty($otcNoLei)">
            <p class="ok">PASS — every OTC derivative has a counterparty LEI.</p>
          </xsl:when>
          <xsl:otherwise>
            <p class="fail">FAIL — <xsl:value-of select="count($otcNoLei)"/> OTC asset(s) missing counterparty LEI.</p>
            <table><tr><th>UniqueID</th><th>Name</th><th>AssetType</th></tr>
              <xsl:for-each select="$otcNoLei">
                <tr><td><xsl:value-of select="UniqueID"/></td>
                    <td><xsl:value-of select="Name"/></td>
                    <td><xsl:value-of select="AssetType"/></td></tr>
              </xsl:for-each>
            </table>
          </xsl:otherwise>
        </xsl:choose>

        <hr/>
        <p style="font-size:.8rem;color:#666">
          Generated by custom_internal_checks.xslt (XSLT 2.0). House rules only —
          run alongside XSD and Schematron validation, not instead of them.
        </p>
      </body>
    </html>
  </xsl:template>
</xsl:stylesheet>
