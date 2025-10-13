<?xml version="1.0" encoding="UTF-8"?>
<!-- 
    FundsXML4 Data Quality Check Stylesheet
    ========================================
    This XSLT transforms FundsXML4 data into an HTML report that performs
    various data quality and consistency checks on fund data.
    
    Main validations performed:
    1. ShareClass NAV summation vs Fund Total NAV
    2. ShareClass price calculation (Price × Shares = NAV)
    3. Portfolio position values vs Fund Total Asset Value
    4. Portfolio percentage allocation (should sum to 100%)
    5. Asset-specific validations (ISIN, LEI, counterparty info, etc.)
-->
<xsl:stylesheet version="2.0" 
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:xs="http://www.w3.org/2001/XMLSchema"
    exclude-result-prefixes="xs">
    
    <!-- Output configuration: Generate HTML with proper formatting -->
    <xsl:output method="html" indent="yes" encoding="UTF-8"/>
    
    <!-- ============================================
         MAIN TEMPLATE
         Entry point that generates the HTML report structure
         ============================================ -->
    <xsl:template match="/">
        <html>
            <head>
                <title>FundsXML4 Data Quality Report</title>
                <style>
                    /* Main styles for the report */
                    body { font-family: Arial, sans-serif; margin: 20px; }
                    h1 { color: #333; }
                    h2 { color: #666; margin-top: 30px; }
                    
                    /* Fund information box styling */
                    .fund-info { background: #f0f0f0; padding: 15px; margin: 20px 0; border-radius: 5px; }
                    
                    /* Check status indicators */
                    .check-passed { color: green; font-weight: bold; }
                    .check-failed { color: red; font-weight: bold; }
                    .warning { color: orange; font-weight: bold; }
                    
                    /* Table styling */
                    table { border-collapse: collapse; width: 100%; margin: 20px 0; }
                    th, td { border: 1px solid #ddd; padding: 10px; text-align: left; }
                    th { background: #4CAF50; color: white; }
                    .number { text-align: right; font-family: monospace; }
                    
                    /* Summary section styling */
                    .summary { background: #e8f4f8; padding: 15px; border-radius: 5px; margin: 20px 0; }
                    
                    /* Check result boxes with colored borders */
                    .check-result { margin: 10px 0; padding: 10px; border-left: 4px solid; }
                    .check-result.error { border-color: red; background: #ffebee; }
                    .check-result.warning { border-color: orange; background: #fff3e0; }
                    .check-result.success { border-color: green; background: #e8f5e9; }
                </style>
            </head>
            <body>
                <h1>FundsXML4 Data Quality Report</h1>
                <p>Report Date: <xsl:value-of select="current-dateTime()"/></p>
                <p>Content Date: <xsl:value-of select="//ContentDate"/></p>
                
                <!-- Process each fund in the document -->
                <xsl:for-each select="//Fund">
                    <xsl:call-template name="check-fund"/>
                </xsl:for-each>
            </body>
        </html>
    </xsl:template>
    
    <!-- ============================================
         FUND CHECK TEMPLATE
         Performs all validation checks for a single fund
         ============================================ -->
    <xsl:template name="check-fund">
        <!-- Display fund header information -->
        <div class="fund-info">
            <h2>Fund: <xsl:value-of select="Names/OfficialName"/></h2>
            <p>LEI: <xsl:value-of select="Identifiers/LEI"/></p>
            <p>NAV Date: <xsl:value-of select="FundDynamicData/TotalAssetValues/TotalAssetValue/NavDate"/></p>
        </div>
        
        <!-- Store frequently used values in variables for efficiency -->
        <xsl:variable name="fundCurrency" select="Currency"/>
        <xsl:variable name="fundTotalNAV" select="FundDynamicData/TotalAssetValues/TotalAssetValue/TotalNetAssetValue/Amount[@ccy = $fundCurrency]"/>

        
        <!-- ============================================
             STRUCTURAL CHECKS
             Basic validation of required elements
             ============================================ -->
        <div class="summary">
            <h3>Structural Checks</h3>
            
            <!-- Check 1: Fund should have a LEI identifier -->
            <div class="check-result">
                <xsl:attribute name="class">
                    <xsl:choose>
                        <xsl:when test="Identifiers/LEI">check-result success</xsl:when>
                        <xsl:otherwise>check-result warning</xsl:otherwise>
                    </xsl:choose>
                </xsl:attribute>
                <xsl:choose>
                    <xsl:when test="Identifiers/LEI">
                        <span class="check-passed">✓ Fund has LEI: <xsl:value-of select="Identifiers/LEI"/></span>
                    </xsl:when>
                    <xsl:otherwise>
                        <span class="warning">⚠ WARNING: The fund should have a LEI</span>
                    </xsl:otherwise>
                </xsl:choose>
            </div>
            
            <!-- Check 2: File must contain at least one portfolio -->
            <div class="check-result">
                <xsl:attribute name="class">
                    <xsl:choose>
                        <xsl:when test="count(FundDynamicData/Portfolios/Portfolio) &gt; 0">check-result success</xsl:when>
                        <xsl:otherwise>check-result warning</xsl:otherwise>
                    </xsl:choose>
                </xsl:attribute>
                <xsl:choose>
                    <xsl:when test="count(FundDynamicData/Portfolios/Portfolio) &gt; 0">
                        <span class="check-passed">✓ File has <xsl:value-of select="count(FundDynamicData/Portfolios/Portfolio)"/> portfolio(s)</span>
                    </xsl:when>
                    <xsl:otherwise>
                        <span class="warning">⚠ WARNING: The file must have at least one portfolio</span>
                    </xsl:otherwise>
                </xsl:choose>
            </div>
            
            <!-- Check 3: Fund Total Asset Value must be in fund currency -->
            <div class="check-result">
                <xsl:attribute name="class">
                    <xsl:choose>
                        <xsl:when test="FundDynamicData/TotalAssetValues/TotalAssetValue/TotalNetAssetValue/Amount[@ccy = $fundCurrency]">check-result success</xsl:when>
                        <xsl:otherwise>check-result error</xsl:otherwise>
                    </xsl:choose>
                </xsl:attribute>
                <xsl:choose>
                    <xsl:when test="FundDynamicData/TotalAssetValues/TotalAssetValue/TotalNetAssetValue/Amount[@ccy = $fundCurrency]">
                        <span class="check-passed">✓ Fund Total Asset Value is in fund currency (<xsl:value-of select="$fundCurrency"/>)</span>
                    </xsl:when>
                    <xsl:otherwise>
                        <span class="check-failed">✗ ERROR: Fund Total Asset Value in fund currency not present</span>
                    </xsl:otherwise>
                </xsl:choose>
            </div>
        </div>
        
        <!-- ============================================
             CHECK 1: Sum of ShareClass NAVs vs. Fund NAV
             Validates that all ShareClass NAVs add up to the Fund's total NAV
             ============================================ -->
        <div class="summary">
            <h3>1. Check: Sum of ShareClass NAVs vs. Fund NAV</h3>
            
            <table>
                <tr>
                    <th>Description</th>
                    <th>Value (<xsl:value-of select="$fundCurrency"/>)</th>
                </tr>
                <tr>
                    <td>Fund Total Net Asset Value</td>
                    <td class="number"><xsl:value-of select="format-number($fundTotalNAV, '#,##0.00')"/></td>
                </tr>
                
                <!-- List each ShareClass with its NAV -->
                <xsl:for-each select="SingleFund/ShareClasses/ShareClass">
                    <tr>
                        <td>ShareClass <xsl:value-of select="Names/OfficialName"/> (ISIN: <xsl:value-of select="Identifiers/ISIN"/>)</td>
                        <td class="number"><xsl:value-of select="format-number(TotalAssetValues/TotalAssetValue/TotalNetAssetValue/Amount[@ccy = $fundCurrency], '#,##0.00')"/></td>
                    </tr>
                </xsl:for-each>
                
                <!-- Calculate and display the sum -->
                <xsl:variable name="sumShareClassNAV" select="sum(SingleFund/ShareClasses/ShareClass/TotalAssetValues/TotalAssetValue/TotalNetAssetValue/Amount[@ccy = $fundCurrency])"/>
                <tr style="font-weight: bold; border-top: 2px solid #333;">
                    <td>Sum of all ShareClass NAVs</td>
                    <td class="number"><xsl:value-of select="format-number($sumShareClassNAV, '#,##0.00')"/></td>
                </tr>
                <tr>
                    <td>Difference</td>
                    <td class="number">
                        <xsl:variable name="diff1" select="$fundTotalNAV - $sumShareClassNAV"/>
                        <xsl:value-of select="format-number($diff1, '#,##0.00')"/>
                    </td>
                </tr>
                <tr>
                    <td>Status</td>
                    <td>
                        <xsl:variable name="diff1" select="$fundTotalNAV - $sumShareClassNAV"/>
                        <xsl:choose>
                            <xsl:when test="abs($diff1) &lt; 0.01">
                                <span class="check-passed">✓ CHECK PASSED</span>
                            </xsl:when>
                            <xsl:when test="abs($diff1) &lt; 1">
                                <span class="warning">⚠ ROUNDING DIFFERENCE</span>
                            </xsl:when>
                            <xsl:otherwise>
                                <span class="check-failed">✗ CHECK FAILED</span>
                            </xsl:otherwise>
                        </xsl:choose>
                    </td>
                </tr>
            </table>
        </div>
        
        <!-- ============================================
             CHECK 2: ShareClass Price × Shares = NAV
             Validates price calculation for each ShareClass
             ============================================ -->
        <div class="summary">
            <h3>2. Check: ShareClass Price × Shares = NAV</h3>
            
            <table>
                <tr>
                    <th>ShareClass</th>
                    <th>Price</th>
                    <th>Shares</th>
                    <th>Reported NAV</th>
                    <th>Difference</th>
                    <th>Status</th>
                </tr>
                
                <xsl:for-each select="SingleFund/ShareClasses/ShareClass">
                    <!-- Get ShareClass-specific currency -->
                    <xsl:variable name="shareclassCCY" select="Currency"/>
                    <xsl:variable name="price" select="Prices/Price/NavPrice"/>
                    <xsl:variable name="shares" select="TotalAssetValues/TotalAssetValue/SharesOutstanding"/>
                    <xsl:variable name="reportedNAV" select="TotalAssetValues/TotalAssetValue/TotalNetAssetValue/Amount[@ccy = $shareclassCCY]"/>
                    <xsl:variable name="calculatedPrice" select="$reportedNAV div $shares"/>
                    <xsl:variable name="diff" select="$calculatedPrice - $price"/>
                    
                    <tr>
                        <td><xsl:value-of select="Identifiers/ISIN"/></td>
                        <td class="number">(<xsl:value-of select="$shareclassCCY"/>) <xsl:value-of select="format-number($price, '#,##0.00')"/></td>
                        <td class="number"><xsl:value-of select="format-number($shares, '#,##0')"/></td>
                        <td class="number"><xsl:value-of select="format-number($reportedNAV, '#,##0.00')"/></td>
                        <td class="number"><xsl:value-of select="format-number($diff, '#,##0.00')"/></td>
                        <td>
                            <xsl:choose>
                                <xsl:when test="abs($diff) &lt; 0.1">
                                    <span class="check-passed">✓ OK</span>
                                </xsl:when>
                                <xsl:when test="abs($diff) &lt; 1">
                                    <span class="warning">⚠ ROUNDING</span>
                                </xsl:when>
                                <xsl:otherwise>
                                    <span class="check-failed">✗ ERROR</span>
                                </xsl:otherwise>
                            </xsl:choose>
                        </td>
                    </tr>
                </xsl:for-each>
            </table>
        </div>
        
        <!-- ============================================
             CHECK 3: Portfolio Position Values = Fund Total Asset Value
             Validates that all portfolio positions sum to the fund's total
             ============================================ -->
        <div class="summary">
            <h3>3. ERROR: Portfolio Position Values vs. Fund Total Asset Value</h3>
            
            <!-- Only sum TotalValue/Amount in fund currency -->
            <xsl:variable name="sumPositionValues" select="sum(FundDynamicData/Portfolios/Portfolio/Positions/Position/TotalValue/Amount[@ccy = $fundCurrency])"/>
            
            <table>
                <tr>
                    <th>Description</th>
                    <th>Value (<xsl:value-of select="$fundCurrency"/>)</th>
                </tr>
                <tr>
                    <td>Sum of all portfolio positions (only in fund currency <xsl:value-of select="$fundCurrency"/>)</td>
                    <td class="number"><xsl:value-of select="format-number($sumPositionValues, '#,##0.00')"/></td>
                </tr>
                <tr>
                    <td>Fund Total Net Asset Value</td>
                    <td class="number"><xsl:value-of select="format-number($fundTotalNAV, '#,##0.00')"/></td>
                </tr>
                <tr>
                    <td>Difference</td>
                    <td class="number">
                        <xsl:variable name="diff" select="$sumPositionValues - $fundTotalNAV"/>
                        <xsl:value-of select="format-number($diff, '#,##0.00')"/>
                    </td>
                </tr>
                <tr>
                    <td>Status</td>
                    <td>
                        <xsl:variable name="diff" select="abs($sumPositionValues - $fundTotalNAV)"/>
                        <xsl:choose>
                            <xsl:when test="$diff &lt; 1">
                                <span class="check-passed">✓ CHECK PASSED</span>
                            </xsl:when>
                            <xsl:otherwise>
                                <span class="check-failed">✗ ERROR: Position values do not equal Fund Total Asset Value</span>
                            </xsl:otherwise>
                        </xsl:choose>
                    </td>
                </tr>
            </table>
        </div>
        
        <!-- ============================================
             CHECK 4: Portfolio Percentages = 100%
             Validates that all position percentages sum to 100%
             ============================================ -->
        <div class="summary">
            <h3>4. ERROR: Portfolio Percentages must add up to 100%</h3>
            
            <xsl:variable name="sumPercentages" select="sum(FundDynamicData/Portfolios/Portfolio/Positions/Position/TotalPercentage)"/>
            
            <table>
                <tr>
                    <th>Description</th>
                    <th>Value (%)</th>
                </tr>
                <tr>
                    <td>Sum of all position percentages</td>
                    <td class="number"><xsl:value-of select="format-number($sumPercentages, '#,##0.0000')"/>%</td>
                </tr>
                <tr>
                    <td>Expected value</td>
                    <td class="number">100.0000%</td>
                </tr>
                <tr>
                    <td>Difference</td>
                    <td class="number">
                        <xsl:variable name="diff" select="abs($sumPercentages - 100)"/>
                        <xsl:value-of select="format-number($diff, '#,##0.0000')"/>%
                    </td>
                </tr>
                <tr>
                    <td>Status</td>
                    <td>
                        <xsl:variable name="diff" select="abs($sumPercentages - 100)"/>
                        <xsl:choose>
                            <xsl:when test="$diff &lt;= 1">
                                <span class="check-passed">✓ CHECK PASSED (Tolerance: 1%)</span>
                            </xsl:when>
                            <xsl:otherwise>
                                <span class="check-failed">✗ ERROR: Percentages do not add up to 100% (tolerance: 1%)</span>
                            </xsl:otherwise>
                        </xsl:choose>
                    </td>
                </tr>
            </table>
        </div>
        
        <!-- ============================================
             ASSET-SPECIFIC CHECKS
             Validates asset-specific requirements based on asset type
             ============================================ -->
        <div class="summary">
            <h3>5. Asset-Specific Checks</h3>
            
            <!-- Check: All positions should have values in fund currency -->
            <div class="check-result">
                <xsl:attribute name="class">
                    <xsl:choose>
                        <xsl:when test="count(FundDynamicData/Portfolios/Portfolio/Positions/Position[not(TotalValue/Amount[@ccy = $fundCurrency])]) = 0">check-result success</xsl:when>
                        <xsl:otherwise>check-result error</xsl:otherwise>
                    </xsl:choose>
                </xsl:attribute>
                <xsl:choose>
                    <xsl:when test="count(FundDynamicData/Portfolios/Portfolio/Positions/Position[not(TotalValue/Amount[@ccy = $fundCurrency])]) = 0">
                        <span class="check-passed">✓ All fund positions have a value in fund currency (<xsl:value-of select="$fundCurrency"/>)</span>
                    </xsl:when>
                    <xsl:otherwise>
                        <span class="check-failed">✗ ERROR: Some positions do not have a value in fund currency (<xsl:value-of select="$fundCurrency"/>)</span>
                        <ul>
                            <xsl:for-each select="FundDynamicData/Portfolios/Portfolio/Positions/Position[not(TotalValue/Amount[@ccy = $fundCurrency])]">
                                <li>Position <xsl:value-of select="UniqueID"/> missing value in fund currency <xsl:value-of select="$fundCurrency"/>
                                    <xsl:if test="TotalValue/Amount">
                                        (has: <xsl:for-each select="TotalValue/Amount">
                                            <xsl:value-of select="@ccy"/>
                                            <xsl:if test="position() != last()">, </xsl:if>
                                        </xsl:for-each>)
                                    </xsl:if>
                                </li>
                            </xsl:for-each>
                        </ul>
                    </xsl:otherwise>
                </xsl:choose>
            </div>
            
            <!-- Check: Equity (EQ), Bond (BO), and ShareClass (SC) assets must have ISIN -->
            <xsl:variable name="assetsRequiringISIN" select="//AssetMasterData/Asset[AssetType = 'EQ' or AssetType = 'BO' or AssetType = 'SC']"/>
            <div class="check-result">
                <xsl:attribute name="class">
                    <xsl:choose>
                        <xsl:when test="count($assetsRequiringISIN[not(Identifiers/ISIN)]) = 0">check-result success</xsl:when>
                        <xsl:otherwise>check-result error</xsl:otherwise>
                    </xsl:choose>
                </xsl:attribute>
                <xsl:choose>
                    <xsl:when test="count($assetsRequiringISIN[not(Identifiers/ISIN)]) = 0">
                        <span class="check-passed">✓ All Equity, Bond, and ShareClass assets have ISIN</span>
                    </xsl:when>
                    <xsl:otherwise>
                        <span class="check-failed">✗ ERROR: Some Equity, Bond or ShareClass assets missing ISIN</span>
                        <ul>
                            <xsl:for-each select="$assetsRequiringISIN[not(Identifiers/ISIN)]">
                                <li>Asset <xsl:value-of select="Name"/> (Type: <xsl:value-of select="AssetType"/>) missing ISIN</li>
                            </xsl:for-each>
                        </ul>
                    </xsl:otherwise>
                </xsl:choose>
            </div>
            
            <!-- Check: Account (AC) assets should have counterparty LEI or BIC -->
            <xsl:variable name="accountAssets" select="//AssetMasterData/Asset[AssetType = 'AC']"/>
            <div class="check-result">
                <xsl:attribute name="class">
                    <xsl:choose>
                        <xsl:when test="count($accountAssets[not(AssetDetails/Account/Counterparty/Identifiers/LEI) and not(AssetDetails/Account/Counterparty/Identifiers/BIC)]) = 0">check-result success</xsl:when>
                        <xsl:otherwise>check-result warning</xsl:otherwise>
                    </xsl:choose>
                </xsl:attribute>
                <xsl:choose>
                    <xsl:when test="count($accountAssets[not(AssetDetails/Account/Counterparty/Identifiers/LEI) and not(AssetDetails/Account/Counterparty/Identifiers/BIC)]) = 0">
                        <span class="check-passed">✓ All Accounts have LEI or BIC for counterparty</span>
                    </xsl:when>
                    <xsl:otherwise>
                        <span class="warning">⚠ WARNING: Some Accounts missing LEI or BIC for counterparty</span>
                        <ul>
                            <xsl:for-each select="$accountAssets[not(AssetDetails/Account/Counterparty/Identifiers/LEI) and not(AssetDetails/Account/Counterparty/Identifiers/BIC)]">
                                <li>Account <xsl:value-of select="Name"/> missing LEI or BIC</li>
                            </xsl:for-each>
                        </ul>
                    </xsl:otherwise>
                </xsl:choose>
            </div>
            
            <!-- Check: Derivatives should have exposure values -->
            <xsl:variable name="derivativeAssets" select="//AssetMasterData/Asset[AssetType = 'OP' or AssetType = 'FU' or AssetType = 'FX' or AssetType = 'SW']"/>
            <div class="check-result">
                <xsl:attribute name="class">
                    <xsl:choose>
                        <xsl:when test="count($derivativeAssets) = 0">check-result success</xsl:when>
                        <xsl:when test="count($derivativeAssets[not(AssetDetails//Exposure)]) = 0">check-result success</xsl:when>
                        <xsl:otherwise>check-result warning</xsl:otherwise>
                    </xsl:choose>
                </xsl:attribute>
                <xsl:choose>
                    <xsl:when test="count($derivativeAssets) = 0">
                        <span class="check-passed">✓ No derivatives (options, futures, fx forward, swap) present</span>
                    </xsl:when>
                    <xsl:when test="count($derivativeAssets[not(AssetDetails//Exposure)]) = 0">
                        <span class="check-passed">✓ All derivatives have exposure</span>
                    </xsl:when>
                    <xsl:otherwise>
                        <span class="warning">⚠ WARNING: Some derivatives missing exposure</span>
                        <ul>
                            <xsl:for-each select="$derivativeAssets[not(AssetDetails//Exposure)]">
                                <li>Asset <xsl:value-of select="Name"/> (Type: <xsl:value-of select="AssetType"/>) missing exposure</li>
                            </xsl:for-each>
                        </ul>
                    </xsl:otherwise>
                </xsl:choose>
            </div>
            
            <!-- Check: Options and Futures must have underlying assets -->
            <xsl:variable name="optionsFuturesAssets" select="//AssetMasterData/Asset[AssetType = 'OP' or AssetType = 'FU']"/>
            <div class="check-result">
                <xsl:attribute name="class">
                    <xsl:choose>
                        <xsl:when test="count($optionsFuturesAssets) = 0">check-result success</xsl:when>
                        <xsl:when test="count($optionsFuturesAssets[not(AssetDetails/Option/Underlyings/Underlying) and not(AssetDetails/Future/Underlyings/Underlying)]) = 0">check-result success</xsl:when>
                        <xsl:otherwise>check-result error</xsl:otherwise>
                    </xsl:choose>
                </xsl:attribute>
                <xsl:choose>
                    <xsl:when test="count($optionsFuturesAssets) = 0">
                        <span class="check-passed">✓ No options or futures present</span>
                    </xsl:when>
                    <xsl:when test="count($optionsFuturesAssets[not(AssetDetails/Option/Underlyings/Underlying) and not(AssetDetails/Future/Underlyings/Underlying)]) = 0">
                        <span class="check-passed">✓ All options and futures have underlying(s)</span>
                    </xsl:when>
                    <xsl:otherwise>
                        <span class="check-failed">✗ ERROR: All assets of type options, futures must have an underlying</span>
                        <ul>
                            <xsl:for-each select="$optionsFuturesAssets">
                                <!-- Check if this specific asset has the required underlying based on its type -->
                                <xsl:variable name="hasUnderlying">
                                    <xsl:choose>
                                        <xsl:when test="AssetType = 'OP' and AssetDetails/Option/Underlyings/Underlying">true</xsl:when>
                                        <xsl:when test="AssetType = 'FU' and AssetDetails/Future/Underlyings/Underlying">true</xsl:when>
                                        <xsl:otherwise>false</xsl:otherwise>
                                    </xsl:choose>
                                </xsl:variable>
                                <xsl:if test="$hasUnderlying = 'false'">
                                    <li>
                                        <xsl:value-of select="Name"/> 
                                        (Type: <xsl:value-of select="AssetType"/>
                                        <xsl:if test="Identifiers/ISIN">, ISIN: <xsl:value-of select="Identifiers/ISIN"/></xsl:if>
                                        <xsl:if test="UniqueID">, ID: <xsl:value-of select="UniqueID"/></xsl:if>
                                        ) missing underlying
                                    </li>
                                </xsl:if>
                            </xsl:for-each>
                        </ul>
                    </xsl:otherwise>
                </xsl:choose>
            </div>
            
            <!-- Check: TotalValues must have consistent direction across all currencies -->
            <div class="check-result">
                <xsl:variable name="directionErrors" as="xs:string*">
                    <xsl:for-each select="FundDynamicData/Portfolios/Portfolio/Positions/Position">
                        <xsl:variable name="position" select="."/>
                        <xsl:variable name="positionId" select="UniqueID"/>
                        
                        <!-- Check if position has multiple currencies with conflicting value directions -->
                        <xsl:if test="count(TotalValue/Amount) &gt; 1">
                            <!-- Consider values > 1 as significantly positive, < -1 as significantly negative -->
                            <xsl:variable name="hasPositiveSignificant" select="count(TotalValue/Amount[number(.) &gt; 1]) &gt; 0"/>
                            <xsl:variable name="hasNegativeSignificant" select="count(TotalValue/Amount[number(.) &lt; -1]) &gt; 0"/>
                            
                            <xsl:if test="$hasPositiveSignificant and $hasNegativeSignificant">
                                <xsl:value-of select="concat('Position ', $positionId, ' has mixed value directions across currencies')"/>
                            </xsl:if>
                        </xsl:if>
                    </xsl:for-each>
                </xsl:variable>
                
                <xsl:attribute name="class">
                    <xsl:choose>
                        <xsl:when test="count($directionErrors) = 0">check-result success</xsl:when>
                        <xsl:otherwise>check-result error</xsl:otherwise>
                    </xsl:choose>
                </xsl:attribute>
                
                <xsl:choose>
                    <xsl:when test="count($directionErrors) = 0">
                        <span class="check-passed">✓ All TotalValues have consistent direction across currencies</span>
                    </xsl:when>
                    <xsl:otherwise>
                        <span class="check-failed">✗ ERROR: TotalValues must have the same direction in all currencies</span>
                        <ul>
                            <xsl:for-each select="$directionErrors">
                                <li><xsl:value-of select="."/></li>
                            </xsl:for-each>
                        </ul>
                    </xsl:otherwise>
                </xsl:choose>
            </div>
        </div>
        
    </xsl:template>
    
</xsl:stylesheet>