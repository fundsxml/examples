<?xml version="1.0" encoding="UTF-8"?>
<!--
  ===================================================================
  TPT V7.0 (Tripartite Template) CSV export  -  XSLT 2.0, text output
  ===================================================================

  WHAT THIS DOES
  ==============
  Reproduces, as faithfully as the source data allows, the FinDatEx / EFAMA
  "Tripartite Template" version 7.0 (TPT V7.0, dated 2024-11-25) as a flat CSV.
  The TPT is the European fund-industry standard for Solvency-II "look-through"
  reporting: insurers receive, per fund/share-class, a line for every single
  instrument the fund holds, described by a fixed list of 152 data columns.

  The authoritative column list (and the FundsXML mapping for almost every
  field) comes from the FinDatEx TPT V7.0 template spreadsheet (sheet
  "TPT V7.0", column "Fundxml data name and path"), published at
  https://findatex.eu/ ; the spreadsheet itself is not part of this repo.
  See README.md for the full column-by-column mapping table.

  OUTPUT SHAPE
  ============
  * One header row  = the 152 TPT column names, verbatim, in TPT order.
  * One full position block PER SHARE CLASS (ISIN) of every <Fund>: a single
    TPT CSV may carry several ISINs. A fund with N share classes and M positions
    yields N*M data rows. Funds without a share class emit one block, keyed by
    the fund ISIN/LEI.
  * Portfolio-level columns (1-11, 115-126) repeat on every row of a block;
    the share-class identification (1,2,3,8,8b) varies per ISIN, while the NAV
    (col 5) and the look-through positions stay at fund level so the valuation
    weights reconcile.

  HOW FundsXML MAPS TO TPT
  ========================
  TPT's paths are conceptual. In real FundsXML 4.x the data for one TPT line is
  split across two places, joined by the position's <UniqueID>:
    - the holding/valuation lives on   .../Positions/Position
    - the static/issuer master data on  AssetMasterData/Asset[UniqueID=...]
  A <Position> carries exactly ONE "holding" child whose element name is the
  instrument family (Bond, Equity, ShareClass, Warrant, Option, Future,
  FXForward, Swap, Repo, RealEstate, CallMoney, Account, FixedTimeDeposit, ...).
  We pick that child generically ($hold) so quantity / price / market value /
  accrued interest read the same way regardless of asset type.

  MISSING DATA
  ============
  Many TPT fields (derivatives detail, SCR contributions, QRT extras, ...) have
  a matching node in FundsXML.xsd but are simply NOT populated in the sample
  files. To stay structurally faithful to the template we still emit ALL 152
  columns, leaving such cells empty rather than dropping the column.

  CONVENTIONS
  ===========
  * FundsXML 4.x has NO XML namespace -> XPath uses bare element names.
  * RFC-4180 quoting: every field is wrapped in double quotes and embedded
    quotes are doubled (f:csv), so commas/quotes in names never break columns.
  * Parameter $delimiter (default ",").
-->
<xsl:stylesheet version="2.0"
                xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:xs="http://www.w3.org/2001/XMLSchema"
                xmlns:f="urn:fundsxml:tpt"
                exclude-result-prefixes="xs f">

  <xsl:output method="text" encoding="UTF-8"/>
  <xsl:param name="delimiter" as="xs:string" select="','"/>

  <!-- TPT version label emitted in column 1000_TPT_Version. -->
  <xsl:variable name="tptVersion" as="xs:string" select="'V7.0'"/>

  <!-- ============================================================ -->
  <!-- Helper functions                                             -->
  <!-- ============================================================ -->

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

  <!-- Derive the CIC instrument category char from a FundsXML AssetType code.
       TPT CIC categories: 1 govt bond, 2 corporate bond, 3 equity,
       4 collective-investment, 5 structured note, 6 collateralised,
       7 cash/deposit, 9 property, A future, B call, C put, D swap,
       E forward, F credit-derivative, 0 other.
       FundsXML cannot distinguish e.g. govt vs corporate bond or call vs put,
       so this is a documented best-effort heuristic (see README). -->
  <xsl:function name="f:cic-category" as="xs:string">
    <xsl:param name="t" as="xs:string?"/>
    <xsl:sequence select="
      if ($t='BO') then '2'
      else if ($t='EQ' or $t='WA') then '3'
      else if ($t='SC') then '4'
      else if ($t='CE') then '5'
      else if ($t='AC' or $t='CM' or $t='FT' or $t='RP') then '7'
      else if ($t='RE') then '9'
      else if ($t='FU') then 'A'
      else if ($t='OP') then 'B'
      else if ($t='SW') then 'D'
      else if ($t='FX') then 'E'
      else '0'"/>
  </xsl:function>

  <!-- Map a FundsXML AssetType code to the TPT field 131 "Underlying asset
       category" closed list (Solvency II QRT S.06.03):
       1 govt bond, 2 corporate bond, 3L listed equity, 3X unlisted equity,
       4 collective investment, 5 structured note, 6 collateralised,
       7 cash/deposits, 8 mortgages/loans, 9 properties, 0 other,
       A futures, B call, C put, D swaps, E forwards, F credit derivatives,
       L liabilities. FundsXML cannot distinguish govt vs corporate bonds
       (-> 2) or listed vs unlisted equity (-> 3L assumed); see README. -->
  <xsl:function name="f:uac" as="xs:string">
    <xsl:param name="t" as="xs:string?"/>
    <xsl:sequence select="
      if ($t='BO') then '2'
      else if ($t='EQ' or $t='WA') then '3L'
      else if ($t='SC') then '4'
      else if ($t='CE') then '5'
      else if ($t='AC' or $t='CM' or $t='FT' or $t='RP') then '7'
      else if ($t='RE') then '9'
      else if ($t='FU') then 'A'
      else if ($t='OP') then 'B'
      else if ($t='SW') then 'D'
      else if ($t='FX') then 'E'
      else if ($t='') then ''
      else '0'"/>
  </xsl:function>

  <!-- ============================================================ -->
  <xsl:template match="/">
    <xsl:variable name="d"  select="$delimiter"/>
    <xsl:variable name="nl" select="'&#10;'"/>
    <xsl:variable name="root" select="FundsXML4"/>

    <!-- Header: the 152 TPT column names, in TPT order. Kept as one literal
         (no column name contains a comma) and re-joined with the requested
         delimiter so the header always matches the data rows. -->
    <xsl:variable name="header" select="'1_Portfolio_identifying_data,2_Type_of_identification_code_for_the_fund_share_or_portfolio,3_Portfolio_name,4_Portfolio_currency_(B),5_Net_asset_valuation_of_the_portfolio_or_the_share_class_in_portfolio_currency,6_Valuation_date,7_Reporting_date,8_Share_price,8b_Total_number_of_shares,9_Cash_ratio,10_Portfolio_modified_duration,11_Complete_SCR_delivery,12_CIC_code_of_the_instrument,13_Economic_zone_of_the_quotation_place,14_Identification_code_of_the_instrument,15_Type_of_identification_code_for_the_instrument,16_Grouping_code_for_multiple_leg_instruments,17_Instrument_name,17b_Asset_liability,18_Quantity,19_Nominal_amount,20_Contract_size_for_derivatives,21_Quotation_currency_(A),22_Market_valuation_in_quotation_currency_(A),23_Clean_market_valuation_in_quotation_currency_(A),24_Market_valuation_in_portfolio_currency_(B),25_Clean_market_valuation_in_portfolio_currency_(B),26_Valuation_weight,27_Market_exposure_amount_in_quotation_currency_(A),28_Market_exposure_amount_in_portfolio_currency_(B),29_Market_exposure_amount_for_the_3rd_quotation_currency_(C),30_Market_exposure_in_weight,31_Market_exposure_for_the_3rd_currency_in_weight_over_NAV,32_Interest_rate_type,33_Coupon_rate,34_Interest_rate_reference_identification,35_Identification_type_for_interest_rate_index,36_Interest_rate_index_name,37_Interest_rate_margin,38_Coupon_payment_frequency,39_Maturity_date,40_Redemption_type,41_Redemption_rate,42_Callable_putable,43_Call_put_date,44_Issuer_bearer_option_exercise,45_Strike_price_for_embedded_(call_put)_options,46_Issuer_name,47_Issuer_identification_code,48_Type_of_identification_code_for_issuer,49_Name_of_the_group_of_the_issuer,50_Identification_of_the_group,51_Type_of_identification_code_for_issuer_group,52_Issuer_country,53_Issuer_economic_area,54_Economic_sector,55_Covered_not_covered,56_Securitisation,57_Explicit_guarantee_by_the_country_of_issue,58_Subordinated_debt,58b_Nature_of_the_tranche,59_Credit_quality_step,60_Call_Put_Cap_Floor,61_Strike_price,62_Conversion_factor_(convertibles)_concordance_factor_parity_(options),63_Effective_date_of_instrument,64_Exercise_type,65_Hedging_rolling,67_CIC_of_the_underlying_asset,68_Identification_code_of_the_underlying_asset,69_Type_of_identification_code_for_the_underlying_asset,70_Name_of_the_underlying_asset,71_Quotation_currency_of_the_underlying_asset_(C),72_Last_valuation_price_of_the_underlying_asset,73_Country_of_quotation_of_the_underlying_asset,74_Economic_area_of_quotation_of_the_underlying_asset,75_Coupon_rate_of_the_underlying_asset,76_Coupon_payment_frequency_of_the_underlying_asset,77_Maturity_date_of_the_underlying_asset,78_Redemption_profile_of_the_underlying_asset,79_Redemption_rate_of_the_underlying_asset,80_Issuer_name_of_the_underlying_asset,81_Issuer_identification_code_of_the_underlying_asset,82_Type_of_issuer_identification_code_of_the_underlying_asset,83_Name_of_the_group_of_the_issuer_of_the_underlying_asset,84_Identification_of_the_group_of_the_underlying_asset,85_Type_of_the_group_identification_code_of_the_underlying_asset,86_Issuer_country_of_the_underlying_asset,87_Issuer_economic_area_of_the_underlying_asset,88_Explicit_guarantee_by_the_country_of_issue_of_the_underlying_asset,89_Credit_quality_step_of_the_underlying_asset,90_Modified_duration_to_maturity_date,91_Modified_duration_to_next_option_exercise_date,92_Credit_sensitivity,93_Sensitivity_to_underlying_asset_price_(delta),94_Convexity_gamma_for_derivatives,94b_Vega,95_Identification_of_the_original_portfolio_for_positions_embedded_in_a_fund,97_SCR_mrkt_IR_up_weight_over_NAV,98_SCR_mrkt_IR_down_weight_over_NAV,99_SCR_mrkt_eq_type1_weight_over_NAV,100_SCR_mrkt_eq_type2_weight_over_NAV,101_SCR_mrkt_prop_weight_over_NAV,102_SCR_mrkt_spread_bonds_weight_over_NAV,103_SCR_mrkt_spread_structured_weight_over_NAV,104_SCR_mrkt_spread_derivatives_up_weight_over_NAV,105_SCR_mrkt_spread_derivatives_down_weight_over_NAV,105a_SCR_mrkt_FX_up_weight_over_NAV,105b_SCR_mrkt_FX_down_weight_over_NAV,106_Asset_pledged_as_collateral,107_Place_of_deposit,108_Participation,110_Valorisation_method,111_Value_of_acquisition,112_Credit_rating,113_Rating_agency,114_Issuer_economic_area,115_Fund_issuer_code,116_Fund_issuer_code_type,117_Fund_issuer_name,118_Fund_issuer_sector,119_Fund_issuer_group_code,120_Fund_issuer_group_code_type,121_Fund_issuer_group_name,122_Fund_issuer_country,123_Fund_CIC,123a_Fund_custodian_country,124_Duration,125_Accrued_income_(Security Denominated Currency),126_Accrued_income_(Portfolio Denominated Currency),127_Bond_floor_(convertible_instrument_only),128_Option_premium_(convertible_instrument_only),129_Valuation_yield,130_Valuation_z_spread,131_Underlying_asset_category,132_Infrastructure_investment,133_custodian_name,134_type1_private_equity_portfolio_eligibility,135_type1_private_equity_issuer_beta,137_Counterparty_sector,138_Collateral_eligibility,139_Collateral_Market_valuation_in_portfolio_currency,140_Custodian_identification_code,141_Type_of_custodian_identification_code,142_Bail-in_Rule,143_Maturity_date_expected,144_Modified_duration_to_maturity_date_expected,145_Credit_sensitivity_expected,146_PIK,147_Infrastructure_investment_additional_QRT,148_Economic_sector_NACE2.1,1000_TPT_Version'"/>
    <xsl:value-of select="string-join(tokenize($header, ','), $d)"/>
    <xsl:value-of select="$nl"/>

    <!-- One block of rows per fund. -->
    <xsl:for-each select="$root/Funds/Fund">
      <xsl:variable name="fund"  select="."/>
      <xsl:variable name="pccy"  select="string($fund/Currency)"/>

      <!-- Portfolio NAV in fund currency (col 5) and dates (cols 6-7). NAV and
           the look-through positions stay at fund level so the valuation
           weights reconcile, even when reporting several share classes. -->
      <xsl:variable name="nav"
                    select="($fund/FundDynamicData/TotalAssetValues/TotalAssetValue/TotalNetAssetValue/Amount[@ccy=$pccy])[last()]"/>
      <xsl:variable name="navDate"
                    select="($fund/FundDynamicData/Portfolios/Portfolio/NavDate,
                             $fund/FundDynamicData/TotalAssetValues/TotalAssetValue/NavDate)[1]"/>
      <xsl:variable name="repDate" select="$root/ControlData/ContentDate"/>

      <!-- Cash ratio (col 9): sum of the position weights of every cash-like
           position (AssetType AC account, CM call money, FT fixed-term deposit),
           expressed as a fraction of NAV (1 = 100%). TotalPercentage is a
           percent, hence the division by 100. -->
      <xsl:variable name="acUids" select="$root/AssetMasterData/Asset[AssetType=('AC','CM','FT')]/UniqueID"/>
      <xsl:variable name="cashRatio"
                    select="sum($fund/FundDynamicData/Portfolios/Portfolio/Positions/Position[UniqueID = $acUids]/TotalPercentage) div 100"/>

      <!-- One full position block PER SHARE CLASS (ISIN): a single TPT CSV may
           carry several ISINs. When the fund has no share class we still emit
           one block, identified by the fund ISIN/LEI. -->
      <xsl:variable name="scList" select="$fund/SingleFund/ShareClasses/ShareClass"/>
      <xsl:for-each select="if (exists($scList)) then $scList else '#fund'">
        <xsl:variable name="sc" select="if (. instance of node()) then . else ()"/>

        <!-- Portfolio identification (cols 1-3): this share class's ISIN
             (codification "1"), else the fund ISIN/LEI ("99"); the share class
             name, else the fund/CIS name. -->
        <xsl:variable name="portfolioId"
                      select="($sc/Identifiers/ISIN, $fund/Identifiers/ISIN, $fund/Identifiers/LEI)[1]"/>
        <xsl:variable name="portfolioIdType"
                      select="if ($sc/Identifiers/ISIN or $fund/Identifiers/ISIN) then '1' else '99'"/>
        <xsl:variable name="ptfName" select="($sc/Names/OfficialName, $fund/Names/OfficialName)[1]"/>

        <!-- Share price (col 8) and shares outstanding (col 8b) of this class. -->
        <xsl:variable name="sharePrice" select="($sc/Prices/Price/NavPrice)[last()]"/>
        <xsl:variable name="shares"     select="($sc/TotalAssetValues/TotalAssetValue/SharesOutstanding)[last()]"/>

      <xsl:for-each select="$fund/FundDynamicData/Portfolios/Portfolio/Positions/Position">
        <xsl:variable name="pos"   select="."/>
        <xsl:variable name="aid"   select="string($pos/UniqueID)"/>
        <xsl:variable name="asset" select="$root/AssetMasterData/Asset[UniqueID=$aid]"/>
        <xsl:variable name="bond"  select="$asset/AssetDetails/Bond"/>
        <xsl:variable name="atype" select="string($asset/AssetType)"/>

        <!-- Issuer lives under the instrument-family child of AssetDetails
             (Bond/Issuer, Equity/Issuer, ShareClass/Issuer, ...), so select it
             generically rather than from Bond alone. -->
        <xsl:variable name="issuer" select="$asset/AssetDetails/*/Issuer[1]"/>
        <!-- Field 47/48: the issuer code is the LEI, and field 48 is its TPT
             type code from the closed list "1 = LEI, 9 = None". -->
        <xsl:variable name="issuerCode" select="$issuer/Identifiers/LEI"/>
        <xsl:variable name="issuerCodeType"
                      select="if ($issuer/Identifiers/LEI) then '1'
                              else if ($issuer) then '9' else ''"/>

        <!-- The single "holding" child: any element that is not one of the
             generic position wrappers. Its name = the instrument family. -->
        <xsl:variable name="hold"
                      select="$pos/*[not(local-name() = ('UniqueID','Identifiers','Currency',
                                'TotalValue','TotalPercentage','Exposures','FXRates','Fee'))][1]"/>

        <xsl:variable name="qccy"  select="string($pos/Currency)"/>
        <xsl:variable name="isin"  select="($pos/Identifiers/ISIN, $asset/Identifiers/ISIN)[1]"/>

        <!-- Instrument identification (col 14) is mandatory: use the ISIN, and
             when there is none fall back to the asset UniqueID (codification
             "99" - code attributed by the undertaking, see col 15). -->
        <xsl:variable name="instrId" select="($isin, $aid)[1]"/>

        <!-- Quantity (col 18): number of units/shares/contracts. Unit-quoted
             instruments only (equities, funds, certificates, warrants,
             futures, options). Bonds carry a nominal -> reported in col 19
             instead, so that exactly ONE of col 18 / col 19 is populated. -->
        <xsl:variable name="qty" select="($hold/Units, $hold/Shares, $hold/Contracts)[1]"/>

        <!-- Market values: quotation ccy (A) and portfolio ccy (B). -->
        <xsl:variable name="mvQC"
                      select="($hold/MarketValue/Amount[@ccy=$qccy], $hold/MarketValue/Amount,
                               $pos/TotalValue/Amount[@ccy=$qccy])[1]"/>
        <xsl:variable name="mvPC"
                      select="($pos/TotalValue/Amount[@ccy=$pccy], $hold/MarketValue/Amount[@ccy=$pccy],
                               $pos/TotalValue/Amount)[1]"/>
        <xsl:variable name="accruedQC" select="($hold/InterestClaimGross/Amount[@ccy=$qccy], $hold/InterestClaimGross/Amount)[1]"/>
        <xsl:variable name="accruedPC" select="$hold/InterestClaimGross/Amount[@ccy=$pccy]"/>
        <xsl:variable name="cleanQC"
                      select="if ($mvQC != '' and $accruedQC != '') then xs:double($mvQC) - xs:double($accruedQC) else $mvQC"/>
        <xsl:variable name="cleanPC"
                      select="if ($mvPC != '' and $accruedPC != '') then xs:double($mvPC) - xs:double($accruedPC) else $mvPC"/>

        <!-- Nominal amount (col 19): par/nominal for bonds. For cash, deposits,
             derivatives and real estate (no unit count, no nominal element) the
             market value stands in as a nominal/exposure proxy, so that exactly
             one of col 18 (units) / col 19 (nominal) is always populated. -->
        <xsl:variable name="nominal"
                      select="if ($hold/Nominal) then $hold/Nominal
                              else if ($qty) then ()
                              else $mvQC"/>

        <!-- Exposures (cols 27-30): commitment-approach exposure per ccy. -->
        <xsl:variable name="expQC" select="($pos/Exposures/Exposure[1]/Value/Amount[@ccy=$qccy])[1]"/>
        <xsl:variable name="expPC" select="($pos/Exposures/Exposure[1]/Value/Amount[@ccy=$pccy])[1]"/>

        <!-- Weights over NAV (cols 26, 30). TotalPercentage is a percent. -->
        <xsl:variable name="weight" select="if ($pos/TotalPercentage != '') then xs:double($pos/TotalPercentage) div 100 else ()"/>
        <xsl:variable name="expWeight"
                      select="if ($expPC != '' and number($nav) and number($nav) != 0) then xs:double($expPC) div xs:double($nav) else $weight"/>

        <!-- Derived CIC (col 12): 2-char country + 1-char category. -->
        <xsl:variable name="cicCountry" select="(($asset/Country)[1], substring(string($isin),1,2))[1]"/>
        <xsl:variable name="cic"
                      select="if ($cicCountry != '') then concat($cicCountry, f:cic-category($atype)) else ''"/>

        <xsl:value-of select="string-join((
          (: 1-11 Portfolio characteristics :)
          f:csv($portfolioId),
          f:csv($portfolioIdType),
          f:csv($ptfName),
          f:csv($pccy),
          f:csv(f:num($nav,'0.00')),
          f:csv($navDate),
          f:csv($repDate),
          f:csv(f:num($sharePrice,'0.000000')),
          f:csv(f:num($shares,'0.00')),
          f:csv(f:num($cashRatio,'0.000000')),             (: 9  cash ratio (sum of AC weights) :)
          f:csv(''),                                       (: 10 ptf modified duration :)
          f:csv(''),                                       (: 11 complete SCR delivery :)
          (: 12-17 Instrument codification :)
          f:csv($cic),
          f:csv(''),                                       (: 13 economic zone :)
          f:csv($instrId),                                 (: 14 ISIN, else asset UniqueID :)
          f:csv(if ($isin != '') then '1' else '99'),
          f:csv(''),                                       (: 16 grouping code :)
          f:csv($asset/Name),
          (: 17b-31 Valuations and exposures :)
          f:csv(''),                                       (: 17b asset/liability :)
          f:csv(f:num($qty,'0.00')),
          f:csv(f:num($nominal,'0.00')),                   (: 19 nominal amount :)
          f:csv(''),                                       (: 20 contract size :)
          f:csv($qccy),
          f:csv(f:num($mvQC,'0.00')),
          f:csv(f:num($cleanQC,'0.00')),
          f:csv(f:num($mvPC,'0.00')),
          f:csv(f:num($cleanPC,'0.00')),
          f:csv(f:num($weight,'0.000000')),
          f:csv(f:num($expQC,'0.00')),
          f:csv(f:num($expPC,'0.00')),
          f:csv(''),                                       (: 29 3rd-ccy exposure :)
          f:csv(f:num($expWeight,'0.000000')),
          f:csv(''),                                       (: 31 3rd-ccy exposure weight :)
          (: 32-45 Interest-rate instrument characteristics :)
          f:csv(''),                                       (: 32 interest rate type :)
          (: 4.2.9 keeps the coupon under Bond/Coupon; flat InterestRate is legacy :)
          f:csv(f:num(($bond/Coupon/InterestRate, $bond/InterestRate)[1],'0.000000')),
          f:csv(''),                                       (: 34 IR reference id :)
          f:csv(''),                                       (: 35 IR index id type :)
          f:csv(''),                                       (: 36 IR index name :)
          f:csv(''),                                       (: 37 IR margin :)
          f:csv($bond/Coupon/PaymentFrequency),
          f:csv($bond/MaturityDate),
          f:csv(''),                                       (: 40 redemption type :)
          f:csv(''),                                       (: 41 redemption rate :)
          f:csv(''),                                       (: 42 callable/putable :)
          f:csv(''),                                       (: 43 call/put date :)
          f:csv(''),                                       (: 44 issuer/bearer exercise :)
          f:csv(''),                                       (: 45 embedded strike :)
          (: 46-59 Issuer data :)
          f:csv($issuer/Name),
          f:csv($issuerCode),
          f:csv($issuerCodeType),
          f:csv(''),                                       (: 49 issuer group name :)
          f:csv(''),                                       (: 50 issuer group id :)
          f:csv(''),                                       (: 51 issuer group id type :)
          f:csv(($issuer/Address/Country, $asset/Country)[1]),
          f:csv(''),                                       (: 53 issuer economic area :)
          f:csv(''),                                       (: 54 economic sector :)
          f:csv(''),                                       (: 55 covered/not covered :)
          f:csv(''),                                       (: 56 securitisation :)
          f:csv(''),                                       (: 57 state guarantee :)
          f:csv(''),                                       (: 58 subordinated debt :)
          f:csv(''),                                       (: 58b tranche nature :)
          f:csv(''),                                       (: 59 credit quality step :)
          (: 60-66 Derivatives additional characteristics :)
          f:csv(''), f:csv(''), f:csv(''), f:csv(''), f:csv(''), f:csv(''),
          (: 67-89 Underlying asset of derivatives :)
          f:csv(''), f:csv(''), f:csv(''), f:csv(''), f:csv(''), f:csv(''),
          f:csv(''), f:csv(''), f:csv(''), f:csv(''), f:csv(''), f:csv(''),
          f:csv(''), f:csv(''), f:csv(''), f:csv(''), f:csv(''), f:csv(''),
          f:csv(''), f:csv(''), f:csv(''), f:csv(''), f:csv(''),
          (: 90-94b Analytics :)
          f:csv(''), f:csv(''), f:csv(''), f:csv(''), f:csv(''), f:csv(''),
          (: 95 Transparency / look-through :)
          f:csv(''),
          (: 97-105b Indicative SCR contributions :)
          f:csv(''), f:csv(''), f:csv(''), f:csv(''), f:csv(''), f:csv(''),
          f:csv(''), f:csv(''), f:csv(''), f:csv(''), f:csv(''),
          (: 106-114 QRT instrument additional info :)
          f:csv(''), f:csv(''), f:csv(''), f:csv(''), f:csv(''), f:csv(''),
          f:csv(''), f:csv(''),
          (: 115-126 QRT portfolio characteristics :)
          f:csv(''),                                       (: 115 fund issuer code :)
          f:csv(''),                                       (: 116 fund issuer code type :)
          f:csv($root/ControlData/DataSupplier/Name),      (: 117 fund issuer name :)
          f:csv(''),                                       (: 118 fund issuer sector :)
          f:csv(''),                                       (: 119 fund issuer group code :)
          f:csv(''),                                       (: 120 fund issuer group code type :)
          f:csv(''),                                       (: 121 fund issuer group name :)
          f:csv($root/ControlData/DataSupplier/SystemCountry), (: 122 fund issuer country :)
          f:csv(''),                                       (: 123 fund CIC :)
          f:csv(''),                                       (: 123a fund custodian country :)
          f:csv(''),                                       (: 124 duration :)
          f:csv(''),                                       (: 125 accrued income (sec ccy) :)
          f:csv(''),                                       (: 126 accrued income (ptf ccy) :)
          (: 127-131 Convertibles / no-yield-curve specifics :)
          f:csv(''), f:csv(''), f:csv(''), f:csv(''),
          f:csv(f:uac($atype)),                            (: 131 underlying asset category (SII S.06.03 list) :)
          (: 132-148 Additional V4..V7 fields (132,133,134,135,137,138,139,140,
             141,142,143,144,145,146,147,148 = 16 columns; 136 not in TPT) :)
          f:csv(''), f:csv(''), f:csv(''), f:csv(''), f:csv(''), f:csv(''),
          f:csv(''), f:csv(''), f:csv(''), f:csv(''), f:csv(''), f:csv(''),
          f:csv(''), f:csv(''), f:csv(''), f:csv(''),
          (: 1000 TPT version :)
          f:csv($tptVersion)
        ), $d)"/>
        <xsl:value-of select="$nl"/>
      </xsl:for-each>
      </xsl:for-each>
    </xsl:for-each>
  </xsl:template>
</xsl:stylesheet>
