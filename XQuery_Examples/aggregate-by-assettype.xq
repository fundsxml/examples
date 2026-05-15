(: ---------------------------------------------------------------------------
   aggregate-by-assettype.xq  —  XQuery 3.1

   Portfolio exposure grouped by AssetType. Positions carry no AssetType; it
   lives in AssetMasterData, so each Position is joined to its Asset by the
   shared UniqueID (the standard FundsXML position<->asset link).

   FundsXML 4.x has no XML namespace — query bare element names.

   Output: <ExposureByAssetType> with one <Bucket> per AssetType, sorted by
   value descending, plus a grand total (sanity-check against 100% / fund NAV).
--------------------------------------------------------------------------- :)
declare option saxon:output "indent=yes";

let $doc      := /FundsXML4
let $fund     := $doc/Funds/Fund[1]
let $ccy      := $fund/Currency
let $assets   := $doc/AssetMasterData/Asset
let $positions := $fund/FundDynamicData/Portfolios/Portfolio/Positions/Position

return
<ExposureByAssetType fund="{$fund/Names/OfficialName}" currency="{$ccy}">
{
  for $p in $positions
  let $a    := $assets[UniqueID = $p/UniqueID]
  let $type := ($a/AssetType, 'UNKNOWN')[1]
  group by $type
  let $value := sum($p/TotalValue/Amount[@ccy = $ccy] ! number(.))
  let $pct   := sum($p/TotalPercentage ! number(.))
  order by $value descending
  return
    <Bucket assetType="{$type}">
      <Positions>{count($p)}</Positions>
      <Value currency="{$ccy}">{format-number($value, '#0.00')}</Value>
      <Percentage>{format-number($pct, '#0.0000')}</Percentage>
    </Bucket>
}
  <Total>
    <Positions>{count($positions)}</Positions>
    <Value currency="{$ccy}">{format-number(
      sum($positions/TotalValue/Amount[@ccy = $ccy] ! number(.)), '#0.00')}</Value>
    <Percentage>{format-number(
      sum($positions/TotalPercentage ! number(.)), '#0.0000')}</Percentage>
  </Total>
</ExposureByAssetType>
