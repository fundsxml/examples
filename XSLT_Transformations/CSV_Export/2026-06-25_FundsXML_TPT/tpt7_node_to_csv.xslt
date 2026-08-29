<?xml version="1.0" encoding="UTF-8"?>
<!--
  ===================================================================
  TPT V7.0 CSV export  -  REVERSE: from the FundsXML TPT7 node
  ===================================================================

  WHAT THIS DOES
  ==============
  Flattens the native FundsXML representation of a Tripartite Template report -
      RegulatoryReportings / IndirectReporting
        / TripartiteTemplateSolvencyII_V7 / Portfolio
  - into the same flat 152-column TPT V7.0 CSV that tpt_v7_export.xslt produces.

  HOW IT DIFFERS FROM tpt_v7_export.xslt
  ======================================
  tpt_v7_export.xslt reconstructs a TPT line from the look-through portfolio
  (FundDynamicData/.../Position) joined to AssetMasterData/Asset. Here the TPT7
  node ALREADY stores every TPT field as a structured element, so this is a
  near 1:1 element-to-column copy - no UniqueID join, no AssetType heuristics.

  * One header row = the 152 TPT column names, in TPT order (identical layout).
  * One data row per <Position> of every <Portfolio>; portfolio-level columns
    (1-11, 115-126) repeat on each row of the portfolio block.
  * Fields the node does not carry are emitted empty, keeping all 152 columns.

  CONVENTIONS (same as the forward exporter)
  ==========================================
  * FundsXML 4.x has NO XML namespace -> bare-element XPath.
  * RFC-4180 quoting via f:csv; numeric formatting via f:num.
  * Parameter $delimiter (default ",").
-->
<xsl:stylesheet version="2.0"
                xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:xs="http://www.w3.org/2001/XMLSchema"
                xmlns:f="urn:fundsxml:tpt"
                exclude-result-prefixes="xs f">

  <xsl:output method="text" encoding="UTF-8"/>
  <xsl:param name="delimiter" as="xs:string" select="','"/>

  <!-- RFC-4180 quote one value (empty sequence -> empty quoted field). -->
  <xsl:function name="f:csv" as="xs:string">
    <xsl:param name="v"/>
    <xsl:sequence select="concat('&quot;',
                                 replace(string-join($v ! string(.), ''), '&quot;', '&quot;&quot;'),
                                 '&quot;')"/>
  </xsl:function>

  <!-- Format a numeric value with fixed decimals; empty in -> empty out. -->
  <xsl:function name="f:num" as="xs:string">
    <xsl:param name="v"/>
    <xsl:param name="pattern" as="xs:string"/>
    <xsl:sequence select="if (string($v) castable as xs:double and string($v) != '')
                          then format-number(xs:double($v), $pattern)
                          else ''"/>
  </xsl:function>

  <xsl:template match="/">
    <xsl:variable name="d"  select="$delimiter"/>
    <xsl:variable name="nl" select="'&#10;'"/>
    <xsl:variable name="root" select="FundsXML4"/>

    <!-- Header: the 152 TPT column names, in TPT order (identical to the
         forward exporter so the two outputs are directly comparable). -->
    <xsl:text>1_Portfolio_identifying_data,2_Type_of_identification_code_for_the_fund_share_or_portfolio,3_Portfolio_name,4_Portfolio_currency_(B),5_Net_asset_valuation_of_the_portfolio_or_the_share_class_in_portfolio_currency,6_Valuation_date,7_Reporting_date,8_Share_price,8b_Total_number_of_shares,9_Cash_ratio,10_Portfolio_modified_duration,11_Complete_SCR_delivery,12_CIC_code_of_the_instrument,13_Economic_zone_of_the_quotation_place,14_Identification_code_of_the_instrument,15_Type_of_identification_code_for_the_instrument,16_Grouping_code_for_multiple_leg_instruments,17_Instrument_name,17b_Asset_liability,18_Quantity,19_Nominal_amount,20_Contract_size_for_derivatives,21_Quotation_currency_(A),22_Market_valuation_in_quotation_currency_(A),23_Clean_market_valuation_in_quotation_currency_(A),24_Market_valuation_in_portfolio_currency_(B),25_Clean_market_valuation_in_portfolio_currency_(B),26_Valuation_weight,27_Market_exposure_amount_in_quotation_currency_(A),28_Market_exposure_amount_in_portfolio_currency_(B),29_Market_exposure_amount_for_the_3rd_quotation_currency_(C),30_Market_exposure_in_weight,31_Market_exposure_for_the_3rd_currency_in_weight_over_NAV,32_Interest_rate_type,33_Coupon_rate,34_Interest_rate_reference_identification,35_Identification_type_for_interest_rate_index,36_Interest_rate_index_name,37_Interest_rate_margin,38_Coupon_payment_frequency,39_Maturity_date,40_Redemption_type,41_Redemption_rate,42_Callable_putable,43_Call_put_date,44_Issuer_bearer_option_exercise,45_Strike_price_for_embedded_(call_put)_options,46_Issuer_name,47_Issuer_identification_code,48_Type_of_identification_code_for_issuer,49_Name_of_the_group_of_the_issuer,50_Identification_of_the_group,51_Type_of_identification_code_for_issuer_group,52_Issuer_country,53_Issuer_economic_area,54_Economic_sector,55_Covered_not_covered,56_Securitisation,57_Explicit_guarantee_by_the_country_of_issue,58_Subordinated_debt,58b_Nature_of_the_tranche,59_Credit_quality_step,60_Call_Put_Cap_Floor,61_Strike_price,62_Conversion_factor_(convertibles)_concordance_factor_parity_(options),63_Effective_date_of_instrument,64_Exercise_type,65_Hedging_rolling,67_CIC_of_the_underlying_asset,68_Identification_code_of_the_underlying_asset,69_Type_of_identification_code_for_the_underlying_asset,70_Name_of_the_underlying_asset,71_Quotation_currency_of_the_underlying_asset_(C),72_Last_valuation_price_of_the_underlying_asset,73_Country_of_quotation_of_the_underlying_asset,74_Economic_area_of_quotation_of_the_underlying_asset,75_Coupon_rate_of_the_underlying_asset,76_Coupon_payment_frequency_of_the_underlying_asset,77_Maturity_date_of_the_underlying_asset,78_Redemption_profile_of_the_underlying_asset,79_Redemption_rate_of_the_underlying_asset,80_Issuer_name_of_the_underlying_asset,81_Issuer_identification_code_of_the_underlying_asset,82_Type_of_issuer_identification_code_of_the_underlying_asset,83_Name_of_the_group_of_the_issuer_of_the_underlying_asset,84_Identification_of_the_group_of_the_underlying_asset,85_Type_of_the_group_identification_code_of_the_underlying_asset,86_Issuer_country_of_the_underlying_asset,87_Issuer_economic_area_of_the_underlying_asset,88_Explicit_guarantee_by_the_country_of_issue_of_the_underlying_asset,89_Credit_quality_step_of_the_underlying_asset,90_Modified_duration_to_maturity_date,91_Modified_duration_to_next_option_exercise_date,92_Credit_sensitivity,93_Sensitivity_to_underlying_asset_price_(delta),94_Convexity_gamma_for_derivatives,94b_Vega,95_Identification_of_the_original_portfolio_for_positions_embedded_in_a_fund,97_SCR_mrkt_IR_up_weight_over_NAV,98_SCR_mrkt_IR_down_weight_over_NAV,99_SCR_mrkt_eq_type1_weight_over_NAV,100_SCR_mrkt_eq_type2_weight_over_NAV,101_SCR_mrkt_prop_weight_over_NAV,102_SCR_mrkt_spread_bonds_weight_over_NAV,103_SCR_mrkt_spread_structured_weight_over_NAV,104_SCR_mrkt_spread_derivatives_up_weight_over_NAV,105_SCR_mrkt_spread_derivatives_down_weight_over_NAV,105a_SCR_mrkt_FX_up_weight_over_NAV,105b_SCR_mrkt_FX_down_weight_over_NAV,106_Asset_pledged_as_collateral,107_Place_of_deposit,108_Participation,110_Valorisation_method,111_Value_of_acquisition,112_Credit_rating,113_Rating_agency,114_Issuer_economic_area,115_Fund_issuer_code,116_Fund_issuer_code_type,117_Fund_issuer_name,118_Fund_issuer_sector,119_Fund_issuer_group_code,120_Fund_issuer_group_code_type,121_Fund_issuer_group_name,122_Fund_issuer_country,123_Fund_CIC,123a_Fund_custodian_country,124_Duration,125_Accrued_income_(Security Denominated Currency),126_Accrued_income_(Portfolio Denominated Currency),127_Bond_floor_(convertible_instrument_only),128_Option_premium_(convertible_instrument_only),129_Valuation_yield,130_Valuation_z_spread,131_Underlying_asset_category,132_Infrastructure_investment,133_custodian_name,134_type1_private_equity_portfolio_eligibility,135_type1_private_equity_issuer_beta,137_Counterparty_sector,138_Collateral_eligibility,139_Collateral_Market_valuation_in_portfolio_currency,140_Custodian_identification_code,141_Type_of_custodian_identification_code,142_Bail-in_Rule,143_Maturity_date_expected,144_Modified_duration_to_maturity_date_expected,145_Credit_sensitivity_expected,146_PIK,147_Infrastructure_investment_additional_QRT,148_Economic_sector_NACE2.1,1000_TPT_Version</xsl:text>
    <xsl:value-of select="$nl"/>

    <!-- One block per TPT7 Portfolio. -->
    <xsl:for-each select="$root/RegulatoryReportings/IndirectReporting/TripartiteTemplateSolvencyII_V7/Portfolio">
      <xsl:variable name="pf"  select="."/>
      <xsl:variable name="qrt" select="$pf/QRTPortfolioInformation"/>

      <xsl:for-each select="$pf/Positions/Position">
        <xsl:variable name="pos"  select="."/>
        <xsl:variable name="val"  select="$pos/Valuation"/>
        <xsl:variable name="irc"  select="$pos/InterestRateInstrumentCharacteristics"/>
        <xsl:variable name="crd"  select="$pos/CreditRiskData"/>

        <xsl:value-of select="string-join((
          (: 1-11 Portfolio characteristics :)
          f:csv($pf/PortfolioID/Code),
          f:csv($pf/PortfolioID/CodificationSystem),
          f:csv($pf/PortfolioName),
          f:csv($pf/PortfolioCurrency),
          f:csv(f:num($pf/TotalNetAssets,'0.00')),
          f:csv($pf/ValuationDate),
          f:csv($pf/ReportingDate),
          f:csv(f:num($pf/ShareClass/SharePrice,'0.000000')),
          f:csv(f:num($pf/ShareClass/TotalNumberOfShares,'0.00')),
          f:csv(f:num($pf/CashPercentage,'0.000000')),
          f:csv(f:num($pf/PortfolioModifiedDuration,'0.000000')),
          f:csv($pf/CompleteSCRDelivery),
          (: 12-17 Instrument codification :)
          f:csv($pos/InstrumentCIC),
          f:csv($pos/EconomicArea),                        (: 13 economic zone :)
          f:csv($pos/InstrumentCode/Code),
          f:csv($pos/InstrumentCode/CodificationSystem),
          f:csv($pos/GroupID),                             (: 16 grouping code :)
          f:csv($pos/InstrumentName),
          (: 17b-31 Valuations and exposures :)
          f:csv(''),                                       (: 17b asset/liability :)
          f:csv(f:num($val/Quantity,'0.00')),
          f:csv(f:num($val/TotalNominalValueQC,'0.00')),
          f:csv(f:num($val/ContractSize,'0.00')),          (: 20 contract size :)
          f:csv($val/QuotationCurrency),
          f:csv(f:num($val/MarketValueQC,'0.00')),
          f:csv(f:num($val/CleanValueQC,'0.00')),
          f:csv(f:num($val/MarketValuePC,'0.00')),
          f:csv(f:num($val/CleanValuePC,'0.00')),
          f:csv(f:num($val/PositionWeight,'0.000000')),
          f:csv(f:num($val/MarketExposureQC,'0.00')),
          f:csv(f:num($val/MarketExposurePC,'0.00')),
          f:csv(f:num($val/MarketExposureUC,'0.00')),       (: 29 3rd-ccy exposure :)
          f:csv(f:num($val/MarketExposureWeight,'0.000000')),
          f:csv(f:num($val/MarketExposureUCWeight,'0.000000')), (: 31 3rd-ccy exposure weight :)
          (: 32-45 Interest-rate instrument characteristics :)
          f:csv($irc/RateType),                            (: 32 interest rate type :)
          f:csv(f:num($irc/CouponRate,'0.000000')),
          f:csv(''),                                       (: 34 IR reference id :)
          f:csv(''),                                       (: 35 IR index id type :)
          f:csv($irc/VariableRate/IndexName),              (: 36 IR index name :)
          f:csv(f:num($irc/VariableRate/Margin,'0.000000')), (: 37 IR margin :)
          f:csv($irc/CouponFrequency),
          f:csv($irc/Redemption/MaturityDate),
          f:csv($irc/Redemption/RedemptionType),           (: 40 redemption type :)
          f:csv(f:num($irc/Redemption/RedemptionRate,'0.00')), (: 41 redemption rate :)
          f:csv(''),                                       (: 42 callable/putable :)
          f:csv(''),                                       (: 43 call/put date :)
          f:csv(''),                                       (: 44 issuer/bearer exercise :)
          f:csv(''),                                       (: 45 embedded strike :)
          (: 46-59 Issuer data :)
          f:csv($crd/InstrumentIssuer/Name),
          f:csv($crd/InstrumentIssuer/Code),
          f:csv($crd/InstrumentIssuer/CodeType),
          f:csv($crd/IssuerGroup/Name),                    (: 49 issuer group name :)
          f:csv($crd/IssuerGroup/Code),                    (: 50 issuer group id :)
          f:csv($crd/IssuerGroup/CodeType),                (: 51 issuer group id type :)
          f:csv($crd/IssuerCountry),
          f:csv($crd/EconomicArea),                        (: 53 issuer economic area :)
          f:csv($crd/EconomicSector),                      (: 54 economic sector :)
          f:csv($crd/Covered),                             (: 55 covered/not covered :)
          f:csv($pos/Securitisation/Securitised),          (: 56 securitisation :)
          f:csv($crd/StateGuarantee),                      (: 57 state guarantee :)
          f:csv($pos/SubordinatedDebt),                    (: 58 subordinated debt :)
          f:csv($pos/Securitisation/TrancheLevel),         (: 58b tranche nature :)
          f:csv($crd/CreditQualityStep),                   (: 59 credit quality step :)
          (: 60-66 Derivatives additional characteristics :)
          f:csv(''), f:csv(''), f:csv(''), f:csv(''), f:csv(''), f:csv(''),
          (: 67-89 Underlying asset of derivatives :)
          f:csv(''), f:csv(''), f:csv(''), f:csv(''), f:csv(''), f:csv(''),
          f:csv(''), f:csv(''), f:csv(''), f:csv(''), f:csv(''), f:csv(''),
          f:csv(''), f:csv(''), f:csv(''), f:csv(''), f:csv(''), f:csv(''),
          f:csv(''), f:csv(''), f:csv(''), f:csv(''), f:csv(''),
          (: 90-94b Analytics :)
          f:csv(f:num($pos/Analytics/ModifiedDurationToMaturity,'0.000000')),
          f:csv(f:num($pos/Analytics/ModifiedDurationToCall,'0.000000')),
          f:csv(f:num($pos/Analytics/CreditSensitivity,'0.000000')),
          f:csv(f:num($pos/Analytics/Delta,'0.000000')),
          f:csv(f:num($pos/Analytics/Convexity,'0.000000')),
          f:csv(f:num($pos/Analytics/Vega,'0.000000')),
          (: 95 Transparency / look-through :)
          f:csv($pos/LookThroughIdentifier),
          (: 97-105b Indicative SCR contributions :)
          f:csv(f:num($pos/ContributionToSCR/MktIntUp,'0.000000')),
          f:csv(f:num($pos/ContributionToSCR/MktIntDown,'0.000000')),
          f:csv(f:num($pos/ContributionToSCR/MktEqGlobal,'0.000000')),
          f:csv(f:num($pos/ContributionToSCR/MktEqOther,'0.000000')),
          f:csv(f:num($pos/ContributionToSCR/MktProp,'0.000000')),
          f:csv(''), f:csv(''), f:csv(''), f:csv(''),
          f:csv(f:num($pos/ContributionToSCR/MktFXUp,'0.000000')),
          f:csv(f:num($pos/ContributionToSCR/MktFXDown,'0.000000')),
          (: 106-114 QRT instrument additional info :)
          f:csv(''), f:csv(''), f:csv(''), f:csv(''), f:csv(''), f:csv(''),
          f:csv(''), f:csv(''),
          (: 115-126 QRT portfolio characteristics :)
          f:csv($qrt/FundIssuer/Code),                     (: 115 fund issuer code :)
          f:csv($qrt/FundIssuer/CodeType),                 (: 116 fund issuer code type :)
          f:csv($qrt/FundIssuer/Name),                     (: 117 fund issuer name :)
          f:csv($qrt/FundIssuer/EconomicSector),           (: 118 fund issuer sector :)
          f:csv($qrt/FundIssuerGroup/Code),                (: 119 fund issuer group code :)
          f:csv($qrt/FundIssuerGroup/CodeType),            (: 120 fund issuer group code type :)
          f:csv($qrt/FundIssuerGroup/Name),                (: 121 fund issuer group name :)
          f:csv($qrt/FundIssuer/Country),                  (: 122 fund issuer country :)
          f:csv($qrt/FundCIC),                             (: 123 fund CIC :)
          f:csv($qrt/FundCustodianCountry),                (: 123a fund custodian country :)
          f:csv(f:num($qrt/Duration,'0.000000')),          (: 124 duration :)
          f:csv(f:num($val/AccruedIncomeQC,'0.00')),       (: 125 accrued income (sec ccy) :)
          f:csv(f:num($val/AccruedIncomePC,'0.00')),       (: 126 accrued income (ptf ccy) :)
          (: 127-131 Convertibles / no-yield-curve specifics :)
          f:csv(''), f:csv(''), f:csv(''), f:csv(''),
          f:csv($pos/QRTPositionInformation/UnderlyingAssetCategory), (: 131 :)
          (: 132-148 Additional V4..V7 fields :)
          f:csv(''), f:csv(''), f:csv(''), f:csv(''), f:csv(''), f:csv(''),
          f:csv(''), f:csv(''), f:csv(''), f:csv(''), f:csv(''), f:csv(''),
          f:csv(''), f:csv(''), f:csv(''), f:csv(''),
          (: 1000 TPT version :)
          f:csv(($pf/TPTVersion, 'V7.0')[1])
        ), $d)"/>
        <xsl:value-of select="$nl"/>
      </xsl:for-each>
    </xsl:for-each>
  </xsl:template>
</xsl:stylesheet>
