(: ---------------------------------------------------------------------------
   fund-summary.xq  —  XQuery 3.1

   One-shot fund overview: identifiers, currency, NAV, share classes and a
   reconciliation block (sum of position values vs. fund TotalNetAssetValue;
   sum of position percentages). Useful as a quick integration health check.

   Works across versions (4.2.9 / 4.1.0 / 4.0.0) — backward compatible, and
   ControlData/Version is simply absent for 4.0.0.

   FundsXML 4.x has no XML namespace — query bare element names.
--------------------------------------------------------------------------- :)
declare option saxon:output "indent=yes";

let $doc   := /FundsXML4
let $cd    := $doc/ControlData
let $fund  := $doc/Funds/Fund[1]
let $ccy   := $fund/Currency
let $nav   := number($fund/FundDynamicData/TotalAssetValues/TotalAssetValue
                      /TotalNetAssetValue/Amount[@ccy = $ccy])
let $posSum := sum($fund/FundDynamicData/Portfolios/Portfolio/Positions/Position
                   /TotalValue/Amount[@ccy = $ccy] ! number(.))
let $pctSum := sum($fund/FundDynamicData/Portfolios/Portfolio/Positions/Position
                   /TotalPercentage ! number(.))

return
<FundSummary>
  <Document>
    <Id>{string($cd/UniqueDocumentID)}</Id>
    <Version>{string(($cd/Version, 'n/a (4.0.0 has no Version element)')[1])}</Version>
    <ContentDate>{string($cd/ContentDate)}</ContentDate>
  </Document>
  <Fund>
    <Name>{string($fund/Names/OfficialName)}</Name>
    <LEI>{string(($fund/Identifiers/LEI, '—')[1])}</LEI>
    <Currency>{string($ccy)}</Currency>
    <TotalNetAssetValue>{format-number($nav, '#0.00')}</TotalNetAssetValue>
    <Positions>{count($fund/FundDynamicData/Portfolios/Portfolio/Positions/Position)}</Positions>
    <ShareClasses>
    {
      for $sc in $fund/SingleFund/ShareClasses/ShareClass
      return <ShareClass isin="{$sc/Identifiers/ISIN}" ccy="{$sc/Currency}"
                         navPrice="{$sc/Prices/Price/NavPrice}">
               {string($sc/Names/OfficialName)}</ShareClass>
    }
    </ShareClasses>
  </Fund>
  <Reconciliation>
    <SumPositionValues>{format-number($posSum, '#0.00')}</SumPositionValues>
    <NavDelta>{format-number(abs($posSum - $nav), '#0.00')}</NavDelta>
    <SumPercentages>{format-number($pctSum, '#0.0000')}</SumPercentages>
    <PercentageOk>{abs($pctSum - 100) <= 1}</PercentageOk>
  </Reconciliation>
</FundSummary>
