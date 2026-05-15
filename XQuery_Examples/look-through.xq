(: ---------------------------------------------------------------------------
   look-through.xq  —  XQuery 3.1

   Fund-of-funds look-through readiness. Positions whose Asset is of type SC
   (a fund / share-class investment) are not "final" holdings — to compute true
   exposure you would substitute the target fund's own portfolio, weighted by
   this position's weight. A single FundsXML file rarely contains the nested
   funds, so this query reports the look-through *candidates* and the residual
   directly-held portion.

   FundsXML 4.x has no XML namespace — query bare element names.
--------------------------------------------------------------------------- :)
declare option saxon:output "indent=yes";

let $doc    := /FundsXML4
let $fund   := $doc/Funds/Fund[1]
let $ccy    := $fund/Currency
let $assets := $doc/AssetMasterData/Asset
let $pos    := $fund/FundDynamicData/Portfolios/Portfolio/Positions/Position

let $scPos  := $pos[ some $a in $assets
                     satisfies $a/UniqueID = ./UniqueID and $a/AssetType = 'SC' ]
let $scPct  := sum($scPos/TotalPercentage ! number(.))

return
<LookThrough fund="{$fund/Names/OfficialName}" currency="{$ccy}">
  <Summary>
    <FundInvestments>{count($scPos)}</FundInvestments>
    <LookThroughWeight>{format-number($scPct div 100, '0.00%')}</LookThroughWeight>
    <DirectlyHeldWeight>{format-number((100 - $scPct) div 100, '0.00%')}</DirectlyHeldWeight>
  </Summary>
  <Candidates>
  {
    for $p in $scPos
    let $a := $assets[UniqueID = $p/UniqueID]
    order by number($p/TotalPercentage) descending
    return
      <Candidate>
        <Isin>{string(($p/Identifiers/ISIN, $a/Identifiers/ISIN, '—')[1])}</Isin>
        <Name>{string(($a/Name, '—')[1])}</Name>
        <Issuer>{string(($a/AssetDetails/ShareClass/Issuer/Name, '—')[1])}</Issuer>
        <Weight>{format-number(number($p/TotalPercentage) div 100, '0.00%')}</Weight>
        <Note>substitute target fund portfolio, scaled by this weight</Note>
      </Candidate>
  }
  </Candidates>
</LookThrough>
