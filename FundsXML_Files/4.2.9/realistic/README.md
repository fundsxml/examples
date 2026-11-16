# Realistic FundsXML 4.2.9 samples

![FundsXML 4.2.9](https://img.shields.io/badge/FundsXML-4.2.9-blue)

Four complete month-end files of fictional funds, sized and structured like real reporting data: hundreds of
positions, a month of transactions and income, several share classes with a daily NAV history. The small
samples in `../positions/` stay the place to learn the structure; these files are for testing tools, mappings
and performance on data that looks like production.

All four are valid against the
[4.2.9 schema](https://github.com/fundsxml/schema/releases/download/4.2.9/FundsXML.xsd) and pass
[`basic_checks.sch`](../../../Schematron_DataQuality_Checks/Basic_Checks/basic_checks.sch) without errors or
warnings (checked in CI).

| File | Size | Net assets (EUR) | Positions | Share classes | Transactions | Income | Shows |
|---|---|---|---|---|---|---|---|
| `Global-Equity-Fund_2025-10.xml` | 0.6 MB | 602,060,878.93 | 123: 112 equities in 7 currencies, 2 index futures, 3 FX forwards, 5 accounts, fee accrual | 3: EUR R acc, EUR I dist, USD R hedged | 67 (trades, a stock split, subscriptions/redemptions) | 31 dividends with withholding tax, account interest | Fund static data (companies, managers, benchmark, costs, SFDR), daily prices and benchmark values, distribution, fees, flows, performance with data series, breakdowns, risk codes, exposures, NACE industry codes |
| `Euro-Bond-Fund_2025-10.xml` | 1.0 MB | 838,581,814.97 | 207: 200 bonds (fixed, floating, zero; sovereign, agency, covered, corporate), 4 interest rate futures, 1 interest rate swap, account, fee accrual | 2: EUR R acc, EUR I dist | 56 (trades with accrued interest, flows) | coupons, account interest | Accrued interest, dirty prices, yields, durations, ratings, maturity/rating/issuer-type breakdowns |
| `Multi-Asset-Derivatives-Fund_2025-10.xml` | 0.5 MB | 278,791,093.07 | 81 over 12 asset types: equities, bonds, ETFs, warrants, certificates, options, futures, FX forwards, swaps (IRS, cross currency, CDS, total return), call money, accounts, fee accrual | 4: EUR R, EUR I, CHF and USD hedged | 56 | dividends, coupons, interest | Counterparties, swap legs, underlyings with delta, delta-adjusted and commitment exposures, leverage and VaR |
| `Fund-of-Funds_2025-10.xml` | 0.4 MB | 155,706,556.38 | 38: 35 target funds of 5 managers, 2 accounts, fee accrual | 2: EUR T acc, EUR A dist | 30 | fund distributions, interest | `FundOfFundFlag`, look-through level 1 (`PositionsDecomposed`) into the target funds' securities |

Reporting date is 2025-10-31; transactions, income, subscriptions and redemptions cover October 2025.

## What is consistent

The generator checks these before it writes a file (and CI checks the first two with `fund-summary.xq`):

- The positions (incl. cash, accrued interest, derivative valuations and the accrued fees) add up to the fund's
  net assets to the cent; `TotalPercentage` adds up to exactly 100.
- The share classes' net assets add up to the fund's net assets; NAV per share × shares outstanding gives the
  share class's net assets. A hedged class reports its net assets in its own currency and in EUR.
- `Prices` holds the NAV of every business day since 2025-09-30; the 1-month performance follows from it
  (for distributing classes with the distribution reinvested).
- Every subscription/redemption in `Flows` has a matching `CASH` transaction; trades settle T+2 within
  October; securities sold out during the month stay in `AssetMasterData`.
- Bond values are clean value + accrued interest (ACT/ACT from the last coupon date); FX forwards, futures and
  swaps carry their valuation as `TotalValue` and their notional or commitment as `Exposure`.

Market values, prices and FX rates are invented and only plausible, not real market data.

## Identifiers are synthetic

No identifier in these files belongs to a real company, fund or security:

| Identifier | Pattern | Why it cannot be real |
|---|---|---|
| ISIN | country + `XMPL` + 5 characters + Luhn check digit, e.g. `ATXMPLF01010` | National numbering agencies of these countries start the national part with a digit; ESMA FIRDS has no ISIN with these prefixes |
| LEI | `XMPL00` + 12 characters + ISO 7064 MOD 97-10 check digits, e.g. `XMPL00FNDGLOBEQ00172` | No LEI issuer uses the prefix `XMPL`; GLEIF knows none of them |

Both have valid check digits, so validators accept them. Company names ("Example Asset Management GmbH",
"Northbridge Securities SE", …), fund names, issuers and the rating agency are fictional. Market identifier codes
(XETR, XNYS, …), currencies and countries are real reference data.

## Regenerate

```bash
python FundsXML_Files/4.2.9/realistic/make_realistic.py                 # writes the four files here
python FundsXML_Files/4.2.9/realistic/make_realistic.py --lint FundsXML_Files tests/fixtures
python FundsXML_Files/4.2.9/realistic/make_realistic.py --verify-online # asks GLEIF and ESMA FIRDS
```

Standard library only. The output is deterministic (fixed seeds, `Decimal` arithmetic, LF line endings); CI
regenerates the files and fails when they differ from the committed ones. `--lint` checks the check digits of
every ISIN and LEI; `--verify-online` asks GLEIF and ESMA FIRDS that none of the synthetic identifiers is
registered (not run in CI).
