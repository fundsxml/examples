<?xml version="1.0" encoding="UTF-8"?>
<!--
  Factsheet (XSL-FO) — XSLT 2.0 producing XSL-FO for PDF rendering.

  Pipeline (two steps):
    1) Saxon : FundsXML + this stylesheet           -> factsheet.fo  (XSL-FO)
    2) Apache FOP : factsheet.fo                     -> factsheet.pdf

  Apache FOP is a separate renderer (not bundled here). Typical invocation:
     fop -fo factsheet.fo -pdf factsheet.pdf
  The XSL-FO output is well-formed XML and can be checked with xmllint even
  without FOP installed.

  FundsXML 4.x has no namespace — XPath uses bare element names.
-->
<xsl:stylesheet version="2.0"
                xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:fo="http://www.w3.org/1999/XSL/Format"
                xmlns:xs="http://www.w3.org/2001/XMLSchema"
                exclude-result-prefixes="xs">

  <xsl:output method="xml" indent="yes" encoding="UTF-8"/>

  <xsl:template match="/">
    <xsl:variable name="fund" select="FundsXML4/Funds/Fund[1]"/>
    <xsl:variable name="ccy" select="$fund/Currency"/>
    <xsl:variable name="nav"
      select="number($fund/FundDynamicData/TotalAssetValues/TotalAssetValue/TotalNetAssetValue/Amount[@ccy=$ccy])"/>

    <fo:root xmlns:fo="http://www.w3.org/1999/XSL/Format">
      <fo:layout-master-set>
        <fo:simple-page-master master-name="A4"
            page-height="297mm" page-width="210mm"
            margin="18mm">
          <fo:region-body/>
        </fo:simple-page-master>
      </fo:layout-master-set>

      <fo:page-sequence master-reference="A4">
        <fo:flow flow-name="xsl-region-body"
                 font-family="serif" font-size="9pt" color="#1a2238">

          <fo:block font-size="16pt" font-weight="bold"
                    border-bottom="2pt solid #1a2238" padding-bottom="3pt">
            <xsl:value-of select="$fund/Names/OfficialName"/>
          </fo:block>
          <fo:block font-size="8pt" color="#555555" space-after="8pt">
            LEI <xsl:value-of select="$fund/Identifiers/LEI"/> ·
            Base currency <xsl:value-of select="$ccy"/> ·
            NAV date <xsl:value-of select="$fund/FundDynamicData/TotalAssetValues/TotalAssetValue/NavDate"/>
          </fo:block>

          <fo:block font-weight="bold" space-after="3pt">Key figures</fo:block>
          <fo:block space-after="8pt">
            Total net assets:
            <xsl:value-of select="format-number($nav,'#,##0')"/>&#160;<xsl:value-of select="$ccy"/> ·
            Positions: <xsl:value-of select="count($fund//Positions/Position)"/> ·
            Share classes: <xsl:value-of select="count($fund/SingleFund/ShareClasses/ShareClass)"/>
          </fo:block>

          <fo:block font-weight="bold" space-after="3pt">Top 10 holdings</fo:block>
          <fo:table table-layout="fixed" width="100%" font-size="8pt">
            <fo:table-column column-width="8%"/>
            <fo:table-column column-width="22%"/>
            <fo:table-column column-width="44%"/>
            <fo:table-column column-width="16%"/>
            <fo:table-column column-width="10%"/>
            <fo:table-header font-weight="bold" background-color="#1a2238" color="#ffffff">
              <fo:table-row>
                <fo:table-cell padding="3pt"><fo:block>#</fo:block></fo:table-cell>
                <fo:table-cell padding="3pt"><fo:block>ISIN / ID</fo:block></fo:table-cell>
                <fo:table-cell padding="3pt"><fo:block>Name</fo:block></fo:table-cell>
                <fo:table-cell padding="3pt"><fo:block text-align="right">Value</fo:block></fo:table-cell>
                <fo:table-cell padding="3pt"><fo:block text-align="right">Wt.</fo:block></fo:table-cell>
              </fo:table-row>
            </fo:table-header>
            <fo:table-body>
              <xsl:for-each select="$fund//Positions/Position">
                <xsl:sort select="number(TotalValue/Amount[@ccy=$ccy])"
                          data-type="number" order="descending"/>
                <xsl:if test="position() le 10">
                  <xsl:variable name="aid" select="UniqueID"/>
                  <fo:table-row>
                    <fo:table-cell padding="2pt"><fo:block><xsl:value-of select="position()"/></fo:block></fo:table-cell>
                    <fo:table-cell padding="2pt"><fo:block><xsl:value-of select="(Identifiers/ISIN,UniqueID)[1]"/></fo:block></fo:table-cell>
                    <fo:table-cell padding="2pt"><fo:block><xsl:value-of select="(/FundsXML4/AssetMasterData/Asset[UniqueID=$aid]/Name,'—')[1]"/></fo:block></fo:table-cell>
                    <fo:table-cell padding="2pt"><fo:block text-align="right"><xsl:value-of select="format-number(number(TotalValue/Amount[@ccy=$ccy]),'#,##0')"/></fo:block></fo:table-cell>
                    <fo:table-cell padding="2pt"><fo:block text-align="right"><xsl:value-of select="format-number(number(TotalPercentage) div 100,'0.00%')"/></fo:block></fo:table-cell>
                  </fo:table-row>
                </xsl:if>
              </xsl:for-each>
            </fo:table-body>
          </fo:table>

          <fo:block font-size="7pt" color="#777777" space-before="14pt">
            Generated from FundsXML by factsheet_fo.xslt (XSLT 2.0 -> XSL-FO -> Apache FOP). Illustrative — not investment advice.
          </fo:block>
        </fo:flow>
      </fo:page-sequence>
    </fo:root>
  </xsl:template>
</xsl:stylesheet>
