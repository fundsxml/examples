<?xml version="1.0" encoding="UTF-8"?>
<!--
  Factsheet (HTML) — XSLT 2.0.

  Turns a FundsXML positions document into a one-page fund factsheet:
  header (name, LEI, currency, NAV date), key figures, share-class table and
  the top-10 holdings by weight. A print-friendly companion that produces
  XSL-FO (for PDF via Apache FOP) lives in factsheet_fo.xslt.

  FundsXML 4.x has no namespace — XPath uses bare element names.
-->
<xsl:stylesheet version="2.0"
                xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:xs="http://www.w3.org/2001/XMLSchema"
                exclude-result-prefixes="xs">

  <xsl:output method="html" indent="yes" encoding="UTF-8"/>

  <xsl:template match="/">
    <xsl:variable name="fund" select="FundsXML4/Funds/Fund[1]"/>
    <xsl:variable name="ccy" select="$fund/Currency"/>
    <xsl:variable name="nav"
      select="number($fund/FundDynamicData/TotalAssetValues/TotalAssetValue/TotalNetAssetValue/Amount[@ccy=$ccy])"/>
    <html lang="en">
      <head>
        <title>Factsheet — <xsl:value-of select="$fund/Names/OfficialName"/></title>
        <style>
          body{font-family:Georgia,'Times New Roman',serif;margin:2rem;color:#1a2238}
          .hd{border-bottom:3px solid #1a2238;padding-bottom:.6rem;margin-bottom:1rem}
          .hd h1{margin:0;font-size:1.5rem}
          .meta{color:#555;font-size:.85rem}
          .kpis{display:flex;gap:1.5rem;margin:1rem 0}
          .kpi{background:#f4f6fb;border-radius:.5rem;padding:.7rem 1rem}
          .kpi .v{font-size:1.2rem;font-weight:700}
          table{border-collapse:collapse;width:100%;margin:.5rem 0;font-size:.85rem}
          th,td{border-bottom:1px solid #d8dce6;padding:.4rem .6rem;text-align:left}
          th{background:#1a2238;color:#fff}
          td.n,th.n{text-align:right;font-variant-numeric:tabular-nums}
        </style>
      </head>
      <body>
        <div class="hd">
          <h1><xsl:value-of select="$fund/Names/OfficialName"/></h1>
          <div class="meta">
            LEI <xsl:value-of select="$fund/Identifiers/LEI"/> ·
            Base currency <xsl:value-of select="$ccy"/> ·
            NAV date <xsl:value-of select="$fund/FundDynamicData/TotalAssetValues/TotalAssetValue/NavDate"/>
          </div>
        </div>

        <div class="kpis">
          <div class="kpi"><div>Total Net Assets</div>
            <div class="v"><xsl:value-of select="format-number($nav,'#,##0')"/>&#160;<xsl:value-of select="$ccy"/></div></div>
          <div class="kpi"><div>Positions</div>
            <div class="v"><xsl:value-of select="count($fund//Positions/Position)"/></div></div>
          <div class="kpi"><div>Share classes</div>
            <div class="v"><xsl:value-of select="count($fund/SingleFund/ShareClasses/ShareClass)"/></div></div>
          <div class="kpi"><div>Ongoing costs</div>
            <div class="v"><xsl:value-of select="($fund/FundStaticData/OngoingCosts/OngoingCost/Percentage,'n/a')[1]"/>%</div></div>
        </div>

        <h3>Share classes</h3>
        <table>
          <tr><th>ISIN</th><th>Name</th><th>Ccy</th><th class="n">NAV price</th></tr>
          <xsl:for-each select="$fund/SingleFund/ShareClasses/ShareClass">
            <tr><td><xsl:value-of select="Identifiers/ISIN"/></td>
                <td><xsl:value-of select="Names/OfficialName"/></td>
                <td><xsl:value-of select="Currency"/></td>
                <td class="n"><xsl:value-of select="format-number(number(Prices/Price/NavPrice),'#,##0.00')"/></td></tr>
          </xsl:for-each>
        </table>

        <h3>Top 10 holdings</h3>
        <table>
          <tr><th>#</th><th>ISIN / ID</th><th>Name</th><th class="n">Value (<xsl:value-of select="$ccy"/>)</th><th class="n">Weight</th></tr>
          <xsl:for-each select="$fund//Positions/Position">
            <xsl:sort select="number(TotalValue/Amount[@ccy=$ccy])" data-type="number" order="descending"/>
            <xsl:if test="position() le 10">
              <xsl:variable name="aid" select="UniqueID"/>
              <tr>
                <td><xsl:value-of select="position()"/></td>
                <td><xsl:value-of select="(Identifiers/ISIN, UniqueID)[1]"/></td>
                <td><xsl:value-of select="(/FundsXML4/AssetMasterData/Asset[UniqueID=$aid]/Name, '—')[1]"/></td>
                <td class="n"><xsl:value-of select="format-number(number(TotalValue/Amount[@ccy=$ccy]),'#,##0')"/></td>
                <td class="n"><xsl:value-of select="format-number(number(TotalPercentage) div 100,'0.00%')"/></td>
              </tr>
            </xsl:if>
          </xsl:for-each>
        </table>

        <p style="font-size:.75rem;color:#777;margin-top:1.5rem">
          Generated from FundsXML by factsheet_html.xslt (XSLT 2.0). Illustrative — not investment advice.
        </p>
      </body>
    </html>
  </xsl:template>
</xsl:stylesheet>
