(: ---------------------------------------------------------------------------
   top-holdings.xq  —  XQuery 3.1

   The N largest holdings by value in fund currency, with the asset name
   resolved from AssetMasterData (Position<->Asset joined by UniqueID).

   External parameter:  $n  (number of holdings, default 10)
     Saxon CLI:  n=5   (XQuery takes bare name=value, not -param:)
     s9api:      qe.setExternalVariable(new QName("n"), new XdmAtomicValue(5))

   FundsXML 4.x has no XML namespace — query bare element names.
--------------------------------------------------------------------------- :)
declare option saxon:output "indent=yes";
declare variable $n external := 10;

let $doc    := /FundsXML4
let $fund   := $doc/Funds/Fund[1]
let $ccy    := $fund/Currency
let $assets := $doc/AssetMasterData/Asset

return
<TopHoldings fund="{$fund/Names/OfficialName}" currency="{$ccy}" n="{$n}">
{
  for $p in $fund/FundDynamicData/Portfolios/Portfolio/Positions/Position
  let $v := number($p/TotalValue/Amount[@ccy = $ccy])
  order by $v descending
  count $rank
  where $rank <= xs:integer($n)
  return
    <Holding rank="{$rank}">
      <Id>{string(($p/Identifiers/ISIN, $p/UniqueID)[1])}</Id>
      <Name>{string(($assets[UniqueID = $p/UniqueID]/Name, '—')[1])}</Name>
      <Value currency="{$ccy}">{format-number($v, '#0.00')}</Value>
      <Weight>{format-number(number($p/TotalPercentage) div 100, '0.00%')}</Weight>
    </Holding>
}
</TopHoldings>
