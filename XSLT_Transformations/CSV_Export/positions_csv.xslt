<?xml version="1.0" encoding="UTF-8"?>
<!--
  CSV export — XSLT 2.0, text output.

  Flattens fund positions into one CSV row per position, joined to
  AssetMasterData by UniqueID. RFC-4180-style quoting: every field is wrapped
  in double quotes and embedded quotes are doubled, so commas/quotes in names
  are safe.

  FundsXML 4.x has no namespace — XPath uses bare element names.
  Parameter: $delimiter (default ",").
-->
<xsl:stylesheet version="2.0"
                xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:xs="http://www.w3.org/2001/XMLSchema"
                exclude-result-prefixes="xs">

  <xsl:output method="text" encoding="UTF-8"/>
  <xsl:param name="delimiter" as="xs:string" select="','"/>

  <xsl:template match="/">
    <xsl:variable name="fund" select="FundsXML4/Funds/Fund[1]"/>
    <xsl:variable name="ccy" select="$fund/Currency"/>
    <xsl:variable name="d" select="$delimiter"/>
    <!-- Header -->
    <xsl:text>FundLEI,DocumentID,UniqueID,ISIN,AssetName,AssetType,Currency,ValueFundCcy,Percentage&#10;</xsl:text>
    <xsl:for-each select="$fund//Positions/Position">
      <xsl:variable name="aid" select="UniqueID"/>
      <xsl:variable name="asset" select="/FundsXML4/AssetMasterData/Asset[UniqueID=$aid]"/>
      <xsl:value-of select="string-join((
        concat('&quot;',$fund/Identifiers/LEI,'&quot;'),
        concat('&quot;',/FundsXML4/ControlData/UniqueDocumentID,'&quot;'),
        concat('&quot;',UniqueID,'&quot;'),
        concat('&quot;',(Identifiers/ISIN,$asset/Identifiers/ISIN,'')[1],'&quot;'),
        concat('&quot;',replace(string(($asset/Name,'')[1]),'&quot;','&quot;&quot;'),'&quot;'),
        concat('&quot;',($asset/AssetType,'')[1],'&quot;'),
        concat('&quot;',(Currency,'')[1],'&quot;'),
        concat('&quot;',format-number(number(TotalValue/Amount[@ccy=$ccy]),'0.00'),'&quot;'),
        concat('&quot;',format-number(number(TotalPercentage),'0.00'),'&quot;')
      ), $d)"/>
      <xsl:text>&#10;</xsl:text>
    </xsl:for-each>
  </xsl:template>
</xsl:stylesheet>
