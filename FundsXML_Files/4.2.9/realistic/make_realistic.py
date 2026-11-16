#!/usr/bin/env python3
"""Generate realistic, schema-valid FundsXML 4.2.9 sample files (synthetic data).

Usage:
    python make_realistic.py [--out DIR] [--only NAME]   write the samples (default: this folder)
    python make_realistic.py --lint PATH...              check ISINs/LEIs of XML files (exit 1 on a problem)
    python make_realistic.py --verify-online             ask GLEIF and ESMA FIRDS that no synthetic
                                                         identifier of the samples is registered

The samples describe four fictional funds of a fictional management company at the
reporting date 2025-10-31, with the transactions, income, subscriptions and
redemptions of October 2025. Everything is invented, but consistent:

* positions (incl. cash, accrued interest and accrued fees) add up to the fund's net
  assets exactly; the position percentages add up to 100;
* share-class net assets add up to the fund's net assets; NAV per share x shares
  outstanding = share-class net assets (to the cent);
* the 1-month performance follows from the daily NAV history in Prices;
* subscriptions/redemptions (Flows) have matching CASH transactions;
* trades settle T+2 within October; fully sold securities stay in AssetMasterData.

Identifiers are synthetic with valid check digits: ISIN = country + "XMPL" + 5 characters
+ Luhn digit, LEI = "XMPL00" + 12 characters + MOD 97-10 check digits. No national numbering
agency issues ISINs starting with "XMPL" after the country code, and GLEIF has no LEI with that
prefix (verify with --verify-online). Market identifier codes (XETR, XNYS ...), currencies and
countries are real reference data.

The output is deterministic: a fixed seed per file, Decimal arithmetic, no dependence on the
platform's floating point maths, fixed timestamps, LF line endings. Standard library only.
"""
import argparse
import pathlib
import random
import re
import sys
from datetime import date, timedelta
from decimal import ROUND_HALF_EVEN, Decimal

D = Decimal
SCHEMA_URL = "https://github.com/fundsxml/schema/releases/download/4.2.9/FundsXML.xsd"
AS_OF = date(2025, 10, 31)
PREV_MONTH_END = date(2025, 9, 30)
GENERATED = "2025-11-03T06:15:00"
FX = {  # units of currency per 1 EUR at 2025-10-31 (illustrative)
    "EUR": D("1"), "USD": D("1.1554"), "GBP": D("0.8784"), "CHF": D("0.9282"), "JPY": D("177.84"),
    "SEK": D("10.9435"), "DKK": D("7.4651"), "CAD": D("1.6189"),
}


# ---------------------------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------------------------

def q(value, places="0.01"):
    return D(value).quantize(D(places), rounding=ROUND_HALF_EVEN)


def eur(amount, ccy):
    return q(D(amount) / FX[ccy])


def business_days(start, end):
    days, d = [], start
    while d <= end:
        if d.weekday() < 5:
            days.append(d)
        d += timedelta(days=1)
    return days


OCTOBER = business_days(date(2025, 10, 1), AS_OF)


def add_business_days(d, n):
    while n > 0:
        d += timedelta(days=1)
        if d.weekday() < 5:
            n -= 1
    return d


def largest_remainder(values, total, places="0.0001", target=D("100")):
    """Percentages of `values` (Decimal) in `total` rounded to `places`, summing exactly to target."""
    raw = [v / total * 100 for v in values]
    rounded = [q(r, places) for r in raw]
    diff = target - sum(rounded)
    if values:
        i = max(range(len(values)), key=lambda k: abs(values[k]))
        rounded[i] += diff
    return rounded


def luhn_digit(body11):
    digits = "".join(str(int(c, 36)) for c in body11)
    total = 0
    for i, ch in enumerate(reversed(digits)):
        n = int(ch) * (2 if i % 2 == 0 else 1)
        total += n - 9 if n > 9 else n
    return str((10 - total % 10) % 10)


def make_isin(country, code5):
    body = country + "XMPL" + code5
    assert len(body) == 11
    return body + luhn_digit(body)


def make_lei(code12):
    body = "XMPL00" + code12
    assert len(body) == 18
    n = int("".join(str(int(c, 36)) for c in body + "00"))
    return body + "%02d" % (98 - n % 97)


def isin_ok(v):
    return bool(re.fullmatch(r"[A-Z]{2}[A-Z0-9]{9}[0-9]", v)) and luhn_digit(v[:11]) == v[11]


def lei_ok(v):
    return bool(re.fullmatch(r"[A-Z0-9]{18}[0-9]{2}", v)) and int("".join(str(int(c, 36)) for c in v)) % 97 == 1


def esc(text):
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


class Writer:
    """Indented XML text writer (3 spaces, like the other samples)."""

    def __init__(self):
        self.lines = []
        self.depth = 0

    def open(self, tag, **attrs):
        self.lines.append("   " * self.depth + "<" + tag + self._attrs(attrs) + ">")
        self.depth += 1

    def close(self, tag):
        self.depth -= 1
        self.lines.append("   " * self.depth + "</" + tag + ">")

    def leaf(self, tag, text, **attrs):
        if text is None:
            return
        if isinstance(text, bool):
            text = "true" if text else "false"
        elif isinstance(text, Decimal):
            text = format(text, "f")
        self.lines.append("   " * self.depth + "<" + tag + self._attrs(attrs) + ">" + esc(text) + "</" + tag + ">")

    def empty(self, tag):
        self.lines.append("   " * self.depth + "<" + tag + "/>")

    def amounts(self, tag, *pairs):
        """<tag><Amount ccy="..">..</Amount>...</tag>; pairs of (value, ccy), duplicates dropped."""
        self.open(tag)
        seen = set()
        for value, ccy in pairs:
            if ccy in seen:
                continue
            seen.add(ccy)
            self.leaf("Amount", value, ccy=ccy)
        self.close(tag)

    @staticmethod
    def _attrs(attrs):
        return "".join(f' {k}="{esc(v)}"' for k, v in attrs.items() if v is not None)

    def text(self):
        return "\n".join(self.lines) + "\n"


# ---------------------------------------------------------------------------------------------
# fictional parties and the security universe (shared by all files)
# ---------------------------------------------------------------------------------------------

def party(code, name, country, city, legal_form=None):
    return {"lei": make_lei(code), "name": name, "country": country, "city": city, "legal_form": legal_form}


MANCO = party("EXAMPLEAM001", "Example Asset Management GmbH", "AT", "Vienna", "GmbH")
DEPOSITARY = party("EXAMPLEDB001", "Example Depositary Bank AG", "AT", "Vienna", "AG")
ADMINISTRATOR = party("EXAMPLEFS001", "Example Fund Services S.A.", "LU", "Luxembourg", "S.A.")
AUDITOR = party("EXAMPLEAU001", "Example Audit & Assurance GmbH", "AT", "Vienna", "GmbH")
PAYING_AGENT = party("EXAMPLEPA001", "Example Paying Agent Bank AG", "DE", "Frankfurt am Main", "AG")
BROKERS = [
    party("BRKNORTH0001", "Northbridge Securities SE", "DE", "Frankfurt am Main", "SE"),
    party("BRKHARB00001", "Harbourview Capital Markets Ltd", "GB", "London", "Ltd"),
    party("BRKALPEN0001", "Alpenrand Wertpapierhandel AG", "AT", "Vienna", "AG"),
    party("BRKLIBER0001", "Libertyport Brokerage LLC", "US", "New York", "LLC"),
]
OTC_COUNTERPARTIES = [
    party("CPTMERID0001", "Meridian Global Bank AG", "DE", "Frankfurt am Main", "AG"),
    party("CPTSTRAN0001", "Strandvik Investment Bank plc", "GB", "London", "plc"),
    party("CPTCASTE0001", "Castellane Banque S.A.", "FR", "Paris", "S.A."),
]
CLEARING_HOUSE = party("CCPEXAMP0001", "Example Clearing House AG", "DE", "Frankfurt am Main", "AG")
RATING_AGENCY = "Example Ratings Ltd"

MARKETS = {  # country -> (currency, MIC, legal suffix)
    "US": ("USD", "XNYS", "Inc."), "DE": ("EUR", "XETR", "AG"), "FR": ("EUR", "XPAR", "S.A."),
    "NL": ("EUR", "XAMS", "N.V."), "IT": ("EUR", "XMIL", "S.p.A."), "ES": ("EUR", "XMAD", "S.A."),
    "AT": ("EUR", "XWBO", "AG"), "FI": ("EUR", "XHEL", "Oyj"), "GB": ("GBP", "XLON", "plc"),
    "CH": ("CHF", "XSWX", "AG"), "JP": ("JPY", "XTKS", "K.K."), "SE": ("SEK", "XSTO", "AB"),
    "DK": ("DKK", "XCSE", "A/S"), "CA": ("CAD", "XTSE", "Corp."),
}
COUNTRY_MIX = ["US"] * 44 + ["DE"] * 6 + ["FR"] * 6 + ["NL"] * 4 + ["IT"] * 2 + ["ES"] * 2 + ["AT"] * 2 \
    + ["FI"] * 2 + ["GB"] * 8 + ["CH"] * 6 + ["JP"] * 8 + ["SE"] * 3 + ["DK"] * 2 + ["CA"] * 5
NAME_STEMS = ["Alder", "Brightwater", "Castell", "Dunmore", "Elmfield", "Fenwick", "Glenrock", "Harlow",
              "Ironvale", "Juniper", "Kestrel", "Larchmont", "Mistral", "Northgate", "Oakridge", "Pinecrest",
              "Quarrystone", "Redfern", "Silverline", "Thornbury", "Upland", "Valemont", "Westhaven", "Yarrow",
              "Zephyr", "Ashcombe", "Birchwood", "Coldstream", "Driftwood", "Eastbrook"]
SECTORS = [  # (name part, NACE code, NACE section)
    ("Semiconductors", "26.11", "C - Manufacturing"), ("Software", "62.01", "J - Information and communication"),
    ("Pharma", "21.20", "C - Manufacturing"), ("Energy", "35.11", "D - Electricity, gas, steam"),
    ("Logistics", "49.41", "H - Transportation and storage"), ("Materials", "24.10", "C - Manufacturing"),
    ("Foods", "10.89", "C - Manufacturing"), ("Motors", "29.10", "C - Manufacturing"),
    ("Telecom", "61.10", "J - Information and communication"), ("Bank", "64.19", "K - Financial and insurance"),
    ("Insurance", "65.12", "K - Financial and insurance"), ("Retail", "47.19", "G - Wholesale and retail trade"),
    ("Chemicals", "20.14", "C - Manufacturing"), ("Engineering", "28.29", "C - Manufacturing"),
    ("Media", "59.11", "J - Information and communication"), ("Healthcare", "86.10", "Q - Human health"),
    ("Real Estate", "68.20", "L - Real estate activities"), ("Utilities", "36.00", "E - Water supply"),
]


def build_universe():
    rng = random.Random(42_2025)
    pairs = [(s, sec) for s in NAME_STEMS for sec in SECTORS]
    rng.shuffle(pairs)
    equities = []
    for n, (stem, (sector, nace, section)) in enumerate(pairs[:170], start=1):
        country = rng.choice(COUNTRY_MIX)
        ccy, mic, suffix = MARKETS[country]
        price = D(rng.randrange(80, 15000)) if ccy == "JPY" else q(D(rng.randrange(850, 89000)) / 100)
        if ccy == "JPY":
            price *= 10
        equities.append({
            "kind": "EQ", "key": f"EQ{n}", "name": f"{stem} {sector} {suffix}", "country": country, "ccy": ccy,
            "mic": mic, "isin": make_isin(country, "E%04d" % n), "issuer_lei": make_lei("EQI%09d" % n),
            "issuer": f"{stem} {sector} {suffix}", "price": price, "nace": nace, "section": section,
            "market_cap": D(rng.randrange(8, 2400)) * 1_000_000_000 / 10,
            "dividend": rng.random() < 0.55,
        })
    issuers = [  # (name, country, ISIN prefix, sector, rating)
        ("Example Federal Treasury", "DE", "DE", "Sovereign", "AAA"), ("Example Republic Treasury", "FR", "FR", "Sovereign", "AA"),
        ("Example Kingdom Treasury", "ES", "ES", "Sovereign", "A"), ("Example State Treasury", "IT", "IT", "Sovereign", "BBB+"),
        ("Example Alpine Treasury", "AT", "AT", "Sovereign", "AA+"), ("Example Lowlands Treasury", "NL", "NL", "Sovereign", "AAA"),
        ("Example Development Bank", "LU", "XS", "Supranational/Agency", "AAA"),
        ("Example Regional Development Agency", "DE", "DE", "Supranational/Agency", "AA+"),
        ("Example Mortgage Bank AG", "DE", "DE", "Covered bond", "AAA"),
        ("Example Hypothekenbank AG", "AT", "AT", "Covered bond", "AA+"),
        ("Example Habitat Covered S.A.", "FR", "FR", "Covered bond", "AAA"),
    ]
    for e in equities[:50]:
        issuers.append((e["issuer"], e["country"], e["country"] if e["ccy"] == "EUR" else "XS", "Corporate",
                        rng.choice(["A+", "A", "A-", "BBB+", "BBB", "BBB-", "BB+"])))
    count_by_sector = {"Sovereign": range(10, 17), "Supranational/Agency": range(7, 12), "Covered bond": range(5, 9),
                       "Corporate": range(2, 5)}
    bonds = []
    n = 0
    for issuer_no, (issuer, country, isin_cc, sector, rating) in enumerate(issuers, start=1):
        for _ in range(rng.choice(count_by_sector[sector])):
            n += 1
            years = rng.randrange(1, 21)
            maturity = date(2026 + years - 1, rng.randrange(1, 13), rng.choice([1, 15, 28]))
            kind = "fix" if rng.random() < 0.82 else ("float" if rng.random() < 0.6 else "zero")
            coupon = D(rng.randrange(1, 45)) * D("0.125") if kind == "fix" else (
                D("0") if kind == "zero" else D("2.031"))  # float: current fixing 3M Euribor + spread
            price = q(D(rng.randrange(8600, 11150)) / 100, "0.001") if kind != "zero" else q(
                D(100) - D(years) * D(rng.randrange(180, 330)) / 100, "0.001")
            bonds.append({
                "kind": "BO", "key": f"BO{n}", "issuer": issuer, "issuer_lei": make_lei("BOI%09d" % issuer_no),
                "country": country, "ccy": "EUR", "isin": make_isin(isin_cc, "B%04d" % n),
                "sector": sector, "rating": rating, "coupon_type": kind, "coupon": coupon, "maturity": maturity,
                "issue": date(maturity.year - years - rng.randrange(1, 6), maturity.month, maturity.day),
                "price": price, "spread_bps": D(rng.randrange(35, 160)) if kind == "float" else None,
                "name": "", "frequency": "QURT" if kind == "float" else "YEAR",
            })
    for b in bonds:
        tag = {"fix": f"{b['coupon'].normalize():f}%", "float": "FRN", "zero": "Zero"}[b["coupon_type"]]
        b["name"] = f"{b['issuer']} {tag} {b['maturity']:%d.%m.%Y}"
    return equities, bonds


EQUITIES, BONDS = build_universe()
INDICES = {
    "WORLD": ("Example World Equity Index", make_isin("EU", "I0001"), D("4386.27")),
    "EURO50": ("Example Euro 50 Index", make_isin("EU", "I0002"), D("5612.40")),
    "US500": ("Example US 500 Index", make_isin("US", "I0003"), D("6731.85")),
    "EUROAGG": ("Example Euro Aggregate Bond Index", make_isin("EU", "I0004"), D("238.914")),
    "BUND": ("Example Euro-Bund 10Y Notional", make_isin("DE", "I0005"), D("128.47")),
}


# ---------------------------------------------------------------------------------------------
# document model
# ---------------------------------------------------------------------------------------------

class Doc:
    def __init__(self, seed):
        self.rng = random.Random(seed)
        self.assets = {}          # key -> asset dict (insertion order = AssetMasterData order)
        self.positions = []
        self.transactions = []
        self.earnings = []
        self.uid_seq = 0

    def asset(self, a):
        if a["key"] not in self.assets:
            self.uid_seq += 1
            a = dict(a)
            a["uid"] = "ID_%04d" % self.uid_seq
            self.assets[a["key"]] = a
        return self.assets[a["key"]]

    def position(self, asset, value_eur, block, ccy=None, exposures=(), risk=(), underlyings=(), fx=None):
        self.positions.append({
            "asset": asset, "value": q(value_eur), "block": block, "ccy": ccy or asset["ccy"],
            "exposures": list(exposures), "risk": list(risk), "underlyings": list(underlyings), "fx": fx,
        })

    @property
    def tna(self):
        return sum(p["value"] for p in self.positions)


def accrued_interest(bond, nominal, on=AS_OF):
    """ACT/ACT accrued interest of `nominal` at date `on` and the last coupon date."""
    if bond["coupon_type"] == "zero":
        return D("0"), None, 0
    months = 12 if bond["frequency"] == "YEAR" else 3
    m = bond["maturity"]
    last = date(on.year, m.month, min(m.day, 28))
    while last > on:
        last = shift_months(last, -months)
    while shift_months(last, months) <= on:
        last = shift_months(last, months)
    nxt = shift_months(last, months)
    days, period = (on - last).days, (nxt - last).days
    rate = bond["coupon"] if bond["coupon_type"] == "fix" else bond["coupon"] + bond["spread_bps"] / 100
    return q(nominal * rate / 100 * months / 12 * days / period), last, days


def shift_months(d, months):
    y, mth = divmod(d.month - 1 + months, 12)
    return date(d.year + y, mth + 1, min(d.day, 28))


def bond_analytics(bond):
    years = D((bond["maturity"] - AS_OF).days) / D(365)
    coupon = bond["coupon"] if bond["coupon_type"] != "float" else D("0")
    ytm = q((coupon + (D(100) - bond["price"]) / max(years, D("0.25"))) / (1 + (D(100) + bond["price"]) / 200 / 100), "0.001")
    mod_dur = q(years / (1 + max(ytm, D("0.1")) / 100) * (D("0.92") if coupon > 2 else D("0.98")), "0.01") \
        if bond["coupon_type"] != "float" else q(D("0.21"), "0.01")
    return ytm, mod_dur


# ---------------------------------------------------------------------------------------------
# share classes, prices, flows
# ---------------------------------------------------------------------------------------------

def nav_history(rng, nav_end, vol_bp):
    """NAV per share for PREV_MONTH_END and every October business day, ending at nav_end."""
    navs = [nav_end]
    for _ in OCTOBER:
        r = D(rng.randrange(-vol_bp, vol_bp + 1)) / 10000
        navs.append(q(navs[-1] / (1 + r), "0.01"))
    navs.reverse()
    return list(zip([PREV_MONTH_END] + OCTOBER, navs))


def build_share_classes(doc, fund, specs):
    """Split the fund's net assets over share classes; derive shares, NAV history and flows."""
    tna = doc.tna
    classes, allocated = [], D("0")
    for i, spec in enumerate(specs):
        eur_tna = tna - allocated if i == len(specs) - 1 else q(tna * spec["weight"])
        allocated += eur_tna
        ccy = spec["ccy"]
        ccy_tna = eur_tna if ccy == "EUR" else q(eur_tna * FX[ccy])
        shares = q(ccy_tna / spec["nav_hint"], "0.001")
        nav = q(ccy_tna / shares)
        history = nav_history(doc.rng, nav, spec.get("vol_bp", 85))
        distribution = None
        if spec.get("distribution"):
            ex = date(2025, 10, 15)
            per_share = spec["distribution"]
            # NAV drops by the distribution on the ex date: lift the earlier NAVs
            history = [(d, n + per_share if d < ex else n) for d, n in history]
            distribution = {"ex": ex, "pay": date(2025, 10, 20), "record": date(2025, 10, 16),
                            "per_share": per_share, "shares": shares, "ccy": ccy}
        flows, net_units = [], D("0")
        flow_days = sorted(doc.rng.sample(OCTOBER[:-2], spec.get("flows", 6)))
        nav_on = dict(history)
        for k, d in enumerate(flow_days):
            sub = doc.rng.random() < spec.get("sub_ratio", 0.55)
            units = q(D(doc.rng.randrange(150, 9000)) * spec.get("flow_size", 1), "0.001")
            value = q(units * nav_on[d])
            flows.append({"id": f"{spec['code']}-FLW-{k + 1:03d}", "date": d, "type": "SUB" if sub else "RED",
                          "units": units, "value": value, "ccy": ccy})
            net_units += units if sub else -units
        assert shares - net_units > 0, "redemptions exceed the shares outstanding"
        start, end = history[0][1] + (distribution["per_share"] if distribution else 0), history[-1][1]
        perf_1m = q(((end + (distribution["per_share"] if distribution else 0)) / history[0][1] - 1) * 100, "0.01") \
            if distribution else q((end / start - 1) * 100, "0.01")
        classes.append({**spec, "eur_tna": eur_tna, "ccy_tna": ccy_tna, "shares": shares, "nav": nav,
                        "history": history, "distribution": distribution, "flows": flows,
                        "perf_1m": perf_1m, "isin": make_isin(fund["country"], spec["isin_code"])})
    assert sum(c["eur_tna"] for c in classes) == tna
    for c in classes:
        assert abs(q(c["ccy_tna"] / c["shares"]) - c["nav"]) < D("0.01")
        for f in c["flows"]:  # each flow is paid in cash
            doc.transactions.append({
                "kind": "CASH", "id": f["id"].replace("FLW", "CSH"), "date": f["date"],
                "valuta": add_business_days(f["date"], 2) if add_business_days(f["date"], 2) <= AS_OF else f["date"],
                "units": f["value"], "ccy": f["ccy"], "eur": eur(f["value"], f["ccy"]) * (1 if f["type"] == "SUB" else -1),
                "text": ("Subscription" if f["type"] == "SUB" else "Redemption") + f" {c['name_suffix']} ({f['units']} units)",
            })
    return classes


# ---------------------------------------------------------------------------------------------
# portfolio building blocks
# ---------------------------------------------------------------------------------------------

def add_equities(doc, count, invested_eur, cap, pool=None, countries=None):
    rng = doc.rng
    pool = [e for e in (pool or EQUITIES) if countries is None or e["country"] in countries]
    picks = rng.sample(pool, count)
    weights = [D(rng.randrange(15, 100)) ** 2 for _ in picks]
    total = sum(weights)
    weights = [min(w / total, cap) for w in weights]
    scale = sum(weights)
    held = []
    for e, w in zip(picks, weights):
        a = doc.asset(e)
        target = invested_eur * w / scale
        units = max(D(1), (target * FX[e["ccy"]] / e["price"]).to_integral_value())
        if e["key"] == picks[0]["key"]:
            units = (units // 4) * 4  # the stock split below needs a multiple of 4
        local = units * e["price"]
        doc.position(a, eur(local, e["ccy"]), {"type": "Equity", "units": units, "price": e["price"], "local": q(local)},
                     exposures=[("Market value", eur(local, e["ccy"]))])
        held.append((a, units))
    return held


def add_bonds(doc, count, invested_eur, pool=None, lot=D("100000"), sectors=None):
    rng = doc.rng
    pool = [b for b in (pool or BONDS) if b["maturity"] > date(2025, 12, 31) and (sectors is None or b["sector"] in sectors)]
    picks = rng.sample(pool, count)
    weights = [D(rng.randrange(30, 100)) for _ in picks]
    total = sum(weights)
    held = []
    for b, w in zip(picks, weights):
        a = doc.asset(b)
        target = invested_eur * w / total
        nominal = max(lot, (target / (b["price"] / 100) / lot).to_integral_value() * lot)
        clean = q(nominal * b["price"] / 100)
        accrued, last_coupon, days = accrued_interest(b, nominal)
        ytm, mod_dur = bond_analytics(b)
        dirty_price = q(b["price"] + accrued / nominal * 100, "0.001")
        doc.position(a, clean + accrued, {"type": "Bond", "nominal": nominal, "price": b["price"], "dirty": dirty_price,
                                          "clean": clean, "accrued": accrued, "days": days, "last_coupon": last_coupon},
                     exposures=[("Market value", clean + accrued)],
                     risk=[("MODIFIED DURATION", mod_dur), ("YIELD", ytm)])
        held.append((a, nominal))
    return held


def counterparty_asset(kind, key, name, ccy, country, details):
    return {"kind": kind, "key": key, "name": name, "ccy": ccy, "country": country, "details": details}


def add_accounts(doc, balances, bank=DEPOSITARY):
    for ccy, amount in balances:
        a = doc.asset(counterparty_asset("AC", f"AC-{ccy}-{bank['lei']}", f"Current account {ccy} at {bank['name']}", ccy,
                                         bank["country"], {"bank": bank, "credit": D("1.85") if ccy == "EUR" else D("0.75")}))
        doc.position(a, eur(amount, ccy), {"type": "Account", "local": q(amount)}, exposures=[("Market value", eur(amount, ccy))])


def add_fee_accrual(doc, ocf_pct, days=30):
    a = doc.asset(counterparty_asset("FE", "FE-MGMT", "Accrued management and depositary fees", "EUR", "AT", {"bank": MANCO}))
    value = -q(doc.tna * ocf_pct / 100 * days / 365)
    doc.position(a, value, {"type": "Fee"})


def add_index_futures(doc, specs):
    """specs: (index key, contracts, multiplier, maturity, variation margin EUR)."""
    for idx, contracts, mult, maturity, vm in specs:
        name, isin, level = INDICES[idx]
        ccy = "USD" if idx == "US500" else "EUR"
        a = doc.asset(counterparty_asset("FU", f"FU-{idx}-{maturity}", f"{name} Future {maturity:%b %Y}", ccy, "DE", {
            "ftype": "IF", "size": mult, "maturity": maturity, "underlying": ("Index", name, isin), "mic": "XEUR" if ccy == "EUR" else "XCME"}))
        exposure = eur(D(contracts) * level * mult, ccy)
        doc.position(a, D(vm), {"type": "Future", "contracts": D(contracts), "price": level, "vm": D(vm)},
                     exposures=[("Commitment", exposure)], risk=[("DELTA", D(1))])


def add_fx_hedges(doc, ccy, notional_ccy, legs, counterparty_pool=OTC_COUNTERPARTIES):
    """Forwards buying `ccy` against EUR (share-class hedge); MTM from a forward premium."""
    remaining = notional_ccy
    for k, (maturity, points) in enumerate(legs):
        part = remaining if k == len(legs) - 1 else q(notional_ccy / len(legs), "1")
        remaining -= part
        fwd = FX[ccy] + D(points) / 10000
        sell_eur = q(part / fwd)
        mtm = q(part / FX[ccy] - sell_eur)
        cpty = counterparty_pool[k % len(counterparty_pool)]
        a = doc.asset(counterparty_asset("FX", f"FX-{ccy}-{maturity}-{k}", f"FX forward buy {ccy} / sell EUR {maturity:%d.%m.%Y}",
                                         "EUR", cpty["country"], {
                                             "buy": (ccy, part), "sell": ("EUR", sell_eur), "rate": fwd, "maturity": maturity,
                                             "start": date(2025, 10, 1), "cpty": cpty}))
        doc.position(a, mtm, {"type": "FXForward", "rate": q(FX[ccy], "0.0001"), "hedge": D("100")},
                     exposures=[("Notional", sell_eur)])


# ---------------------------------------------------------------------------------------------
# trades and income
# ---------------------------------------------------------------------------------------------

def trade_days(rng, n):
    days = [d for d in OCTOBER if add_business_days(d, 2) <= AS_OF]
    return sorted(rng.choice(days) for _ in range(n))


def equity_trades(doc, held, n, exits=2):
    rng = doc.rng
    sold_out = [e for e in EQUITIES if e["key"] not in doc.assets][:exits]
    for d, k in zip(trade_days(rng, n), range(n)):
        if k < exits:
            e = sold_out[k]
            a = doc.asset(e)
            units = D(rng.randrange(800, 12000))
            side = "SELL"
        else:
            a, units_end = rng.choice(held)
            side = "BUY" if rng.random() < 0.55 else "SELL"
            units = max(D(1), (units_end * D(rng.randrange(5, 30)) / 100).to_integral_value())
        price = q(a["price"] * (1 + D(rng.randrange(-250, 251)) / 10000), "1" if a["ccy"] == "JPY" else "0.01")
        local = q(units * price)
        mv = eur(local, a["ccy"])
        cost = max(q(mv * D("0.0005")), D("15.00"))
        doc.transactions.append({
            "kind": side, "id": "", "date": d, "valuta": add_business_days(d, 2), "asset": a, "units": units,
            "price": price, "local": local, "eur": mv, "expenses": cost,
            "settle": mv + cost if side == "BUY" else mv - cost, "broker": rng.choice(BROKERS), "mic": a["mic"],
            "order": rng.choice(["Market", "Limit", "MarketOnClose"]),
            "text": f"{'Purchase' if side == 'BUY' else 'Sale'} {a['name']}",
        })
    # one stock split on the first holding (held units are a multiple of 4)
    a, units_end = held[0]
    doc.transactions.append({"kind": "CORP_ACTION", "id": "", "date": date(2025, 10, 14), "valuta": date(2025, 10, 14),
                             "asset": a, "units": units_end - units_end / 4, "text": f"Stock split 1:4 {a['name']}"})


def bond_trades(doc, held, n):
    rng = doc.rng
    for d in trade_days(rng, n):
        a, nominal_end = rng.choice(held)
        side = "BUY" if rng.random() < 0.6 else "SELL"
        nominal = max(D(100000), (nominal_end * D(rng.randrange(10, 40)) / 100 / 100000).to_integral_value() * 100000)
        price = q(a["price"] * (1 + D(rng.randrange(-60, 61)) / 10000), "0.001")
        valuta = add_business_days(d, 2)
        accrued, _, days = accrued_interest(a, nominal, valuta)
        clean = q(nominal * price / 100)
        cost = max(q(clean * D("0.0001")), D("25.00"))
        doc.transactions.append({
            "kind": side, "id": "", "date": d, "valuta": valuta, "asset": a, "units": nominal, "price": price,
            "local": clean, "eur": clean, "expenses": cost, "accrued": accrued, "accrued_days": days,
            "settle": clean + accrued + cost if side == "BUY" else clean + accrued - cost, "broker": rng.choice(BROKERS),
            "mic": None, "order": "OTC", "text": f"{'Purchase' if side == 'BUY' else 'Sale'} {a['name']}",
        })


WITHHOLDING = {"US": D("15"), "CH": D("35"), "DE": D("26.375"), "FR": D("25"), "JP": D("15.315"), "GB": D("0"),
               "NL": D("15"), "IT": D("26"), "ES": D("19"), "AT": D("27.5"), "FI": D("30"), "SE": D("30"),
               "DK": D("27"), "CA": D("25")}


def dividends(doc, held, count):
    rng = doc.rng
    payers = [(a, u) for a, u in held if a.get("dividend")][:count]
    for k, (a, units) in enumerate(payers):
        ex = rng.choice(OCTOBER[:-4])
        pay = add_business_days(ex, rng.choice([2, 3, 5]))
        dps = q(a["price"] * D(rng.randrange(40, 160)) / 10000, "1" if a["ccy"] == "JPY" else "0.0001")
        gross = q(units * dps)
        wht = q(gross * WITHHOLDING[a["country"]] / 100)
        doc.earnings.append({"kind": "Dividend", "asset": a, "ex": ex, "pay": pay, "ccy": a["ccy"], "units": units,
                             "dps": dps, "gross": gross, "wht": wht, "net": gross - wht,
                             "text": f"Dividend {a['name']}"})


def coupons(doc, held):
    for a, nominal in held:
        if a["coupon_type"] != "fix":
            continue
        m = a["maturity"]
        if m.month == 10:
            d = date(2025, 10, min(m.day, 28))
            while d.weekday() >= 5:
                d += timedelta(days=1)
            gross = q(nominal * a["coupon"] / 100)
            doc.earnings.append({"kind": "Coupon", "asset": a, "ex": d, "pay": d, "ccy": "EUR", "units": nominal,
                                 "gross": gross, "net": gross, "wht": D(0), "unit": q(a["coupon"], "0.0001"),
                                 "text": f"Coupon {a['name']}"})


def account_interest(doc):
    for p in doc.positions:
        a = p["asset"]
        if a["kind"] == "AC" and p["block"]["local"] > 0:
            interest = q(p["block"]["local"] * a["details"]["credit"] / 100 * 31 / 360)
            if interest > 0:
                doc.earnings.append({"kind": "Interest deposit/giro", "asset": a, "ex": AS_OF, "pay": AS_OF, "ccy": a["ccy"],
                                     "units": None, "gross": interest, "net": interest, "wht": D(0),
                                     "text": f"Credit interest October 2025 {a['name']}"})


# ---------------------------------------------------------------------------------------------
# XML emission (element order as in FundsXML 4.2.9)
# ---------------------------------------------------------------------------------------------

def emit_company(w, tag, p):
    w.open(tag)
    w.open("Identifiers")
    w.leaf("LEI", p["lei"])
    w.close("Identifiers")
    w.leaf("Name", p["name"])
    w.leaf("LegalForm", p.get("legal_form"))
    w.open("Address")
    w.leaf("CityName", p["city"])
    w.leaf("Country", p["country"])
    w.close("Address")
    w.close(tag)


def emit_control(w, doc_id):
    w.open("ControlData")
    w.leaf("UniqueDocumentID", doc_id)
    w.leaf("DocumentGenerated", GENERATED)
    w.leaf("Version", "4.2.9")
    w.leaf("ContentDate", AS_OF.isoformat())
    w.open("DataSupplier")
    w.leaf("SystemCountry", "AT")
    w.leaf("Short", "EXAMPLE-AM")
    w.leaf("Name", MANCO["name"])
    w.leaf("Type", "Asset Manager")
    w.close("DataSupplier")
    w.leaf("DataOperation", "INITIAL")
    w.leaf("Language", "en")
    w.close("ControlData")


def emit_fund(w, doc, fund, classes, breakdowns, risk_codes, benchmark):
    tna = doc.tna
    w.open("Fund")
    w.open("Identifiers")
    w.leaf("LEI", fund["lei"])
    w.close("Identifiers")
    w.open("Names")
    w.leaf("OfficialName", fund["name"])
    w.leaf("ShortName", fund["short"])
    w.close("Names")
    w.leaf("Currency", "EUR")
    w.leaf("SingleFundFlag", True)
    # --- static data
    w.open("FundStaticData")
    w.leaf("DomicileCountry", fund["country"])
    w.leaf("ListedLegalStructure", "UCITS")
    w.leaf("InceptionDate", fund["inception"].isoformat())
    w.open("StartOfFiscalYear")
    w.leaf("Day", 1)
    w.leaf("Month", 1)
    w.close("StartOfFiscalYear")
    w.open("EndOfFiscalYear")
    w.leaf("Day", 31)
    w.leaf("Month", 12)
    w.close("EndOfFiscalYear")
    w.leaf("OpenClosedEnded", "OPEN")
    emit_company(w, "Administrator", ADMINISTRATOR)
    emit_company(w, "Auditor", AUDITOR)
    emit_company(w, "Custodian", DEPOSITARY)
    emit_company(w, "InvestmentCompany", MANCO)
    w.open("Companies")
    for role, p in (("Management Company", MANCO), ("Paying Agent", PAYING_AGENT)):
        w.open("Company")
        w.leaf("ListedRole", role)
        w.leaf("RoleStart", fund["inception"].isoformat())
        emit_company(w, "Details", p)
        w.close("Company")
    w.close("Companies")
    w.open("PortfolioManagers")
    for name, start, role in fund["managers"]:
        w.open("PortfolioManager")
        w.leaf("Name", name)
        w.leaf("StartDate", start)
        w.leaf("Role", role)
        w.close("PortfolioManager")
    w.close("PortfolioManagers")
    if benchmark:
        w.open("Benchmarks")
        w.open("Benchmark")
        w.leaf("BenchmarkID", "BM1")
        w.leaf("Name", benchmark["name"])
        w.leaf("Currency", "EUR")
        w.leaf("BenchmarkType", "Market Index")
        w.close("Benchmark")
        w.close("Benchmarks")
    w.open("OngoingCosts")
    for cost_type, pct in fund["costs"]:
        w.open("OngoingCost")
        w.leaf("CostType", cost_type)
        w.leaf("PublicationDate", "2025-02-14")
        w.leaf("ValidFrom", "2025-01-01")
        w.leaf("Percentage", pct)
        w.close("OngoingCost")
    w.close("OngoingCosts")
    w.leaf("SFDRProductType", fund["sfdr"])
    w.close("FundStaticData")
    # --- dynamic data
    w.open("FundDynamicData")
    w.open("TotalAssetValues")
    w.open("TotalAssetValue")
    w.leaf("NavDate", AS_OF.isoformat())
    w.leaf("TotalAssetNature", "OFFICIAL")
    w.amounts("TotalNetAssetValue", (tna, "EUR"))
    gross = sum(p["value"] for p in doc.positions if p["value"] > 0)
    w.amounts("TotalGrossAssetValue", (gross, "EUR"))
    w.close("TotalAssetValue")
    w.close("TotalAssetValues")
    w.open("Portfolios")
    w.open("Portfolio")
    w.leaf("NavDate", AS_OF.isoformat())
    emit_positions(w, doc, "Positions", doc.positions, tna)
    emit_transactions(w, doc)
    emit_earnings(w, doc)
    if fund.get("lookthrough"):
        w.open("PositionsDecomposed")
        w.leaf("LookThroughLevels", 1)
        emit_positions(w, doc, "Positions", fund["lookthrough"], tna)
        w.close("PositionsDecomposed")
    emit_breakdowns(w, breakdowns)
    w.open("RiskCodes")
    for code, value, annualized, desc in risk_codes:
        w.open("RiskCode")
        w.leaf("ListedCode", code)
        w.leaf("Value", value)
        w.leaf("Frequency", "DAIL")
        w.leaf("DateFrom", "2024-10-31")
        w.leaf("DateTo", AS_OF.isoformat())
        w.leaf("Annualization", annualized)
        w.leaf("Description", desc)
        w.close("RiskCode")
    w.close("RiskCodes")
    w.close("Portfolio")
    w.close("Portfolios")
    if benchmark:
        w.open("Benchmarks")
        w.open("Benchmark")
        w.leaf("BenchmarkID", "BM1")
        w.open("Values")
        for d, level in benchmark["history"]:
            w.open("Value")
            w.leaf("Date", d.isoformat())
            w.leaf("ValueType", "Total Return")
            w.amounts("Value", (level, "EUR"))
            w.close("Value")
        w.close("Values")
        w.close("Benchmark")
        w.close("Benchmarks")
    w.close("FundDynamicData")
    # --- single fund
    w.open("SingleFund")
    w.open("SingleFundStaticData")
    w.open("Managers")
    emit_company(w, "Manager", MANCO)
    w.close("Managers")
    w.open("Policies")
    w.leaf("Policy", fund["policy"])
    w.close("Policies")
    w.leaf("FundOfFundFlag", bool(fund.get("fof")))
    w.leaf("SocialResponsibleFlag", fund["sfdr"] in ("8", "9"))
    w.leaf("ManagementType", "ACTIVE")
    w.leaf("PricePublishedFlag", True)
    w.close("SingleFundStaticData")
    w.open("ShareClasses")
    for c in classes:
        emit_share_class(w, c, fund)
    w.close("ShareClasses")
    w.close("SingleFund")
    w.close("Fund")


def emit_positions(w, doc, tag, positions, tna):
    pcts = largest_remainder([p["value"] for p in positions], tna)
    w.open(tag)
    for p, pct in zip(positions, pcts):
        a, b = p["asset"], p["block"]
        w.open("Position")
        w.leaf("UniqueID", a["uid"])
        if a.get("isin"):
            w.open("Identifiers")
            w.leaf("ISIN", a["isin"])
            w.close("Identifiers")
        w.leaf("Currency", p["ccy"])
        w.amounts("TotalValue", (p["value"], "EUR"))
        w.leaf("TotalPercentage", pct)
        if p["exposures"]:
            w.open("Exposures")
            for t, v in p["exposures"]:
                w.open("Exposure")
                w.leaf("Type", t)
                w.amounts("Value", (v, "EUR"))
                w.close("Exposure")
            w.close("Exposures")
        if p["ccy"] != "EUR":
            w.open("FXRates")
            w.leaf("FXRate", FX[p["ccy"]], fromCcy="EUR", toCcy=p["ccy"], mulDiv="M")
            w.close("FXRates")
        w.leaf("PriceDate", AS_OF.isoformat())
        t = b["type"]
        w.open(t)
        if t == "Equity":
            w.leaf("Units", b["units"])
            w.amounts("Price", (b["price"], a["ccy"]))
            w.amounts("MarketValue", (b["local"], a["ccy"]), (p["value"], "EUR"))
        elif t == "Bond":
            w.leaf("Nominal", b["nominal"])
            w.amounts("Price", (b["price"], a["ccy"]))
            w.amounts("DirtyPrice", (b["dirty"], a["ccy"]))
            w.amounts("MarketValue", (b["clean"], a["ccy"]))
            w.amounts("InterestClaimGross", (b["accrued"], a["ccy"]))
            w.leaf("AccruedInterestDays", b["days"])
            if b["last_coupon"]:
                w.leaf("DateLastCouponPayment", b["last_coupon"].isoformat())
        elif t == "ShareClass":
            w.leaf("Shares", b["units"])
            w.amounts("Price", (b["price"], a["ccy"]))
        elif t in ("Warrant", "Certificate"):
            w.leaf("Units", b["units"])
            w.amounts("Price", (b["price"], a["ccy"]))
        elif t == "Option":
            w.leaf("Contracts", b["contracts"])
            w.amounts("Price", (b["price"], a["ccy"]))
        elif t == "Future":
            w.leaf("Contracts", b["contracts"])
            w.amounts("Price", (b["price"], a["ccy"]))
            w.amounts("VariationMarginOverall", (b["vm"], "EUR"))
        elif t == "FXForward":
            w.leaf("HedgeRatio", b["hedge"])
            w.leaf("FxRateForEvaluation", b["rate"])
        elif t == "Swap":
            w.open("LegValues")
            for leg_type, v in b["legs"]:
                w.open("LegValue")
                w.leaf("Type", leg_type)
                w.amounts("Value", (v, "EUR"))
                w.close("LegValue")
            w.close("LegValues")
        elif t in ("Account", "CallMoney"):
            w.amounts("MarketValue", (b["local"], a["ccy"]), (p["value"], "EUR"))
        if t == "Fee":  # an empty element in the schema
            w.depth -= 1
            w.lines[-1] = "   " * w.depth + "<Fee/>"
        else:
            w.close(t)
        if p["risk"]:
            w.open("RiskCodes")
            for code, value in p["risk"]:
                w.open("RiskCode")
                w.leaf("ListedCode", code)
                w.leaf("Value", value)
                w.leaf("Annualization", code in ("YIELD",))
                w.close("RiskCode")
            w.close("RiskCodes")
        if p["underlyings"]:
            w.open("Underlyings")
            for isin, delta in p["underlyings"]:
                w.open("Underlying")
                w.open("Identifiers")
                w.leaf("ISIN", isin)
                w.close("Identifiers")
                w.leaf("Delta", delta)
                w.close("Underlying")
            w.close("Underlyings")
        w.close("Position")
    w.close(tag)


def emit_transactions(w, doc):
    if not doc.transactions:
        return
    w.open("Transactions", **{"from": "2025-10-01", "to": AS_OF.isoformat()})
    for t in doc.transactions:
        w.open("Transaction")
        w.leaf("TransactionID", t["id"])
        a = t.get("asset")
        if a:
            w.leaf("AssetUniqueID", a["uid"])
            if a.get("isin"):
                w.open("Identifiers")
                w.leaf("ISIN", a["isin"])
                w.close("Identifiers")
            w.leaf("Currency", a["ccy"])
        else:
            w.leaf("Currency", t["ccy"])
        w.leaf("TransactionKind", t["kind"])
        w.leaf("SettlementCurrency", "EUR" if t["kind"] != "CASH" else t["ccy"])
        w.leaf("EntryDate", t["date"].isoformat())
        w.leaf("ValutaDate", t["valuta"].isoformat())
        w.leaf("ClosingDate", t["date"].isoformat())
        w.leaf("NominalOrUnitsOrContracts", t["units"])
        if t["kind"] in ("BUY", "SELL"):
            if "accrued" in t:
                w.amounts("CleanPrice", (t["price"], a["ccy"]))
            w.amounts("AgreedPrice", (t["price"], a["ccy"]))
            w.amounts("MarketValue", (t["local"], a["ccy"]), (t["eur"], "EUR"))
            if "accrued" in t:
                w.amounts("InterestClaimGross", (t["accrued"], "EUR"))
            w.amounts("SettlementAmount", (q(t["settle"]), "EUR"))
            if a["ccy"] != "EUR":
                w.open("FXRates")
                w.leaf("FXRate", FX[a["ccy"]], fromCcy="EUR", toCcy=a["ccy"], mulDiv="M")
                w.close("FXRates")
            w.amounts("Expenses", (t["expenses"], "EUR"))
        elif t["kind"] == "CASH":
            w.amounts("MarketValue", (t["units"], t["ccy"]))
        w.leaf("PostingText", t["text"])
        if t["kind"] in ("BUY", "SELL"):
            emit_company(w, "Counterparty", t["broker"])
            w.leaf("Exchange", t["mic"])
        w.leaf("FinallySettled", True)
        if t["kind"] in ("BUY", "SELL") and "accrued" in t:
            w.open("Bonds")
            w.amounts("UnitInterests", (t["accrued"], "EUR"))
            w.leaf("UnitInterestsDays", t["accrued_days"])
            w.close("Bonds")
        elif t["kind"] in ("BUY", "SELL") and a["kind"] in ("OP", "FU"):
            w.open("Derivatives")
            w.leaf("HedgingFlag", a["kind"] == "FU")
            w.leaf("OpenCloseCash", "OPEN" if t["kind"] == "BUY" else "CLOSE")
            w.close("Derivatives")
        if t["kind"] in ("BUY", "SELL"):
            w.leaf("OrderExecutionType", t["order"])
        w.close("Transaction")
    w.close("Transactions")


def emit_earnings(w, doc):
    if not doc.earnings:
        return
    w.open("Earnings", **{"from": "2025-10-01", "to": AS_OF.isoformat()})
    for k, e in enumerate(doc.earnings, start=1):
        a = e["asset"]
        w.open("Earning")
        w.leaf("EarningID", f"ERN-2025-10-{k:04d}")
        w.leaf("AssetUniqueID", a["uid"])
        if a.get("isin"):
            w.open("Identifiers")
            w.leaf("ISIN", a["isin"])
            w.close("Identifiers")
        w.leaf("EarningKind", e["kind"])
        w.leaf("EntryDate", e["pay"].isoformat())
        w.leaf("ValutaDate", e["pay"].isoformat())
        w.leaf("EntryCurrency", e["ccy"])
        w.amounts("EntryValue", (e["net"], e["ccy"]), (eur(e["net"], e["ccy"]), "EUR"))
        if e["ccy"] != "EUR":
            w.open("FXRates")
            w.leaf("FXRate", FX[e["ccy"]], fromCcy="EUR", toCcy=e["ccy"], mulDiv="M")
            w.close("FXRates")
        w.leaf("NominalValueOrUnits", e["units"])
        w.leaf("PostingText", e["text"])
        w.leaf("FinallySettled", True)
        if e["kind"] == "Dividend":
            w.open("Dividend")
            w.amounts("DividendPerUnitValue", (e["dps"], e["ccy"]))
            w.amounts("DividendGrossValue", (e["gross"], e["ccy"]))
            w.amounts("DividendNetValue", (e["net"], e["ccy"]))
            w.amounts("WithholdingTaxValue", (e["wht"], e["ccy"]))
            w.leaf("ExDay", e["ex"].isoformat())
            w.leaf("PayDay", e["pay"].isoformat())
            w.leaf("WithholdingTaxQuota", WITHHOLDING[a["country"]])
            w.close("Dividend")
        elif e["kind"] == "Coupon":
            w.open("Coupon")
            w.amounts("UnitInterestsGrossValue", (e["unit"], "EUR"))
            w.close("Coupon")
        w.close("Earning")
    w.close("Earnings")


def emit_breakdowns(w, breakdowns):
    w.open("BreakDowns")
    for dimension, rows in breakdowns:
        w.open("BreakDown")
        w.open("Dimensions")
        w.leaf("Dimension", dimension)
        w.close("Dimensions")
        w.leaf("CalculationMethod", "Market value incl. accrued interest, % of net assets")
        w.open("Values")
        for label, pct in rows:
            w.open("Value")
            w.open("DimValues")
            w.leaf("DimValue", label, dim=dimension)
            w.close("DimValues")
            w.leaf("Percentage", pct)
            w.close("Value")
        w.close("Values")
        w.close("BreakDown")
    w.close("BreakDowns")


def emit_share_class(w, c, fund):
    w.open("ShareClass")
    w.open("Identifiers")
    w.leaf("ISIN", c["isin"])
    w.close("Identifiers")
    w.open("Names")
    w.leaf("OfficialName", f"{fund['name']} {c['name_suffix']}")
    w.close("Names")
    w.leaf("Currency", c["ccy"])
    w.open("ShareClassType")
    w.leaf("Code", c["code"])
    w.leaf("EarningUse", "D" if c.get("distribution") else "R")
    w.leaf("Name", c["type_name"])
    w.close("ShareClassType")
    w.leaf("InceptionDate", c["inception"].isoformat())
    w.open("RegistrationCountries")
    for cc in c["registered"]:
        w.open("RegistrationCountry")
        w.leaf("CountryCode", cc)
        w.close("RegistrationCountry")
    w.close("RegistrationCountries")
    w.amounts("MinimumInvestment", (c["minimum"], c["ccy"]))
    w.leaf("OpenToNewInvestorsFlag", True)
    w.leaf("CurrencyHedgedFlag", bool(c.get("hedged")))
    w.open("FundHedgingStrategy")
    w.leaf("HedgingStrategy", "Full NAV hedge" if c.get("hedged") else "No hedge")
    w.close("FundHedgingStrategy")
    w.leaf("IsPublicFlag", True)
    w.open("Prices")
    for d, nav in c["history"]:
        w.open("Price")
        w.leaf("ActionCode", "C")
        w.leaf("NavDate", d.isoformat())
        w.leaf("PriceCurrency", c["ccy"])
        w.leaf("PriceNature", "OFFICIAL")
        w.leaf("NavPrice", nav)
        if c.get("front_load"):
            w.leaf("SubscriptionPrice", q(nav * (1 + c["front_load"] / 100)))
        w.leaf("RedemptionPrice", nav)
        w.close("Price")
    w.close("Prices")
    w.open("TotalAssetValues")
    w.open("TotalAssetValue")
    w.leaf("NavDate", AS_OF.isoformat())
    w.leaf("TotalAssetNature", "OFFICIAL")
    w.amounts("TotalNetAssetValue", (c["ccy_tna"], c["ccy"]), (c["eur_tna"], "EUR"))
    w.leaf("SharesOutstanding", c["shares"])
    w.close("TotalAssetValue")
    w.close("TotalAssetValues")
    dist = c["distribution"]
    if dist:
        net = q(dist["per_share"] * D("0.725"), "0.0001")
        w.open("Distributions")
        w.open("Distribution")
        w.leaf("ActionCode", "C")
        w.leaf("DividendStatus", "OFFICIAL")
        w.leaf("AnnouncementDate", "2025-10-01")
        w.leaf("RecordDate", dist["record"].isoformat())
        w.leaf("ExDate", dist["ex"].isoformat())
        w.leaf("PaymentDate", dist["pay"].isoformat())
        w.leaf("PaymentCurrency", c["ccy"])
        w.open("GrossDividendAmount")
        w.amounts("PerShare", (dist["per_share"], c["ccy"]))
        w.close("GrossDividendAmount")
        w.open("NetDividendAmount")
        w.amounts("PerShare", (net, c["ccy"]))
        w.close("NetDividendAmount")
        w.leaf("DistributionFlag", True)
        w.close("Distribution")
        w.close("Distributions")
    w.open("Fees")
    w.open("Fee")
    w.leaf("Type", "Management fee")
    w.leaf("PayReceive", "P")
    w.leaf("Maximum", c["max_fee"])
    w.leaf("CalculationMethod", "Accrued daily on the net assets of the share class, paid monthly")
    w.open("DataByPeriods")
    w.open("DataByPeriod")
    w.leaf("BeginDate", "2025-10-01")
    w.leaf("EndDate", AS_OF.isoformat())
    w.open("Values")
    w.amounts("TNA", (c["ccy_tna"], c["ccy"]))
    w.leaf("FeeAsPercentageOfTNA", c["fee"])
    w.amounts("ActualFeeAmount", (q(c["ccy_tna"] * c["fee"] / 100 * 31 / 365), c["ccy"]))
    w.close("Values")
    w.close("DataByPeriod")
    w.close("DataByPeriods")
    w.close("Fee")
    w.close("Fees")
    if c["flows"]:
        w.open("Flows", **{"from": "2025-10-01", "to": AS_OF.isoformat()})
        for f in c["flows"]:
            w.open("Flow")
            w.leaf("ActionCode", "C")
            w.leaf("TransactionID", f["id"])
            w.leaf("TradeDate", f["date"].isoformat())
            w.leaf("AccountingDate", f["date"].isoformat())
            w.leaf("SettlementDate", add_business_days(f["date"], 2).isoformat())
            w.leaf("TransactionType", f["type"])
            w.leaf("Units", f["units"])
            w.amounts("TotalValue", (f["value"], f["ccy"]))
            w.close("Flow")
        w.close("Flows")
    w.open("PerformanceFigures")
    w.leaf("ActionCode", "C")
    w.open("Performances")
    perf_rows = [("1 Month", c["perf_1m"], False, PREV_MONTH_END)] + [
        (period, value, period in ("3 Years",), None) for period, value in c["perf_other"]]
    for period, value, annualized, start in perf_rows:
        w.open("Performance")
        w.leaf("ValidityDate", AS_OF.isoformat())
        w.leaf("CalculationPeriod", period)
        w.leaf("PercentageValue", value)
        w.leaf("AnnualizedFlag", annualized)
        w.leaf("CalculationMethod", "BVI method (distributions reinvested)")
        if start:
            w.leaf("StartCalculationDate", start.isoformat())
            w.leaf("DateInterval", "Daily")
            w.open("DataSeries")
            for d, nav in c["history"]:
                w.open("DataPoint")
                w.leaf("Date", d.isoformat())
                w.leaf("Value", nav)
                w.close("DataPoint")
            w.close("DataSeries")
        w.close("Performance")
    w.close("Performances")
    w.close("PerformanceFigures")
    w.close("ShareClass")


def emit_assets(w, doc):
    w.open("AssetMasterData")
    for a in doc.assets.values():
        w.open("Asset")
        w.leaf("UniqueID", a["uid"])
        if a.get("isin"):
            w.open("Identifiers")
            w.leaf("ISIN", a["isin"])
            w.close("Identifiers")
        w.leaf("Currency", a["ccy"])
        w.leaf("Country", a["country"])
        w.leaf("Name", a["name"])
        w.leaf("AssetType", a["kind"])
        w.open("AssetDetails")
        emit_asset_details(w, a)
        w.close("AssetDetails")
        if a["kind"] == "BO":
            w.open("Ratings")
            w.open("Rating")
            w.leaf("RatingCompany", RATING_AGENCY)
            w.open("Rating")
            w.leaf("Date", "2025-09-15")
            w.leaf("Value", a["rating"])
            w.close("Rating")
            w.close("Rating")
            w.close("Ratings")
        w.close("Asset")
    w.close("AssetMasterData")


def issuer(a):
    return {"lei": a["issuer_lei"], "name": a["issuer"], "country": a["country"] if a["country"] != "XS" else "DE",
            "city": None}


def emit_issuer(w, tag, a):
    w.open(tag)
    w.open("Identifiers")
    w.leaf("LEI", a["issuer_lei"])
    w.close("Identifiers")
    w.leaf("Name", a["issuer"])
    w.close(tag)


def emit_asset_details(w, a):
    k, det = a["kind"], a.get("details", {})
    if k == "EQ":
        w.open("Equity")
        w.leaf("StockMarket", a["mic"])
        emit_issuer(w, "Issuer", a)
        w.open("MarketCapitalization")
        w.leaf("Date", AS_OF.isoformat())
        w.leaf("Value", a["market_cap"])
        w.close("MarketCapitalization")
        w.open("Industries")
        w.open("IndustryCode")
        w.leaf("Name", "NACE Rev. 2")
        w.leaf("Date", "2025-01-01")
        w.leaf("Value", a["nace"])
        w.close("IndustryCode")
        w.close("Industries")
        w.close("Equity")
    elif k == "BO":
        ytm, mod_dur = bond_analytics(a)
        w.open("Bond")
        w.leaf("ConvertibleFlag", False)
        emit_issuer(w, "Issuer", a)
        w.leaf("IssueDate", a["issue"].isoformat())
        w.leaf("MaturityDate", a["maturity"].isoformat())
        w.open("Coupon")
        w.leaf("Type", a["coupon_type"])
        if a["coupon_type"] != "zero":
            w.leaf("PaymentFrequency", a["frequency"])
            w.leaf("InterestRate", a["coupon"] if a["coupon_type"] == "fix" else a["coupon"] + a["spread_bps"] / 100)
        if a["coupon_type"] == "float":
            w.leaf("OffsetBPS", a["spread_bps"])
        w.close("Coupon")
        w.leaf("RedemptionRate", 100)
        w.open("Yields")
        w.open("Yield")
        w.leaf("Method", "Yield to maturity")
        w.leaf("Date", AS_OF.isoformat())
        w.leaf("Value", ytm)
        w.close("Yield")
        w.close("Yields")
        w.open("Durations")
        w.open("Duration")
        w.leaf("Name", "Modified duration")
        w.leaf("Date", AS_OF.isoformat())
        w.leaf("Value", mod_dur)
        w.close("Duration")
        w.close("Durations")
        w.close("Bond")
    elif k == "SC":
        w.open("ShareClass")
        emit_company(w, "Issuer", det["manager"])
        if det.get("mic"):
            w.leaf("StockMarket", det["mic"])
        w.leaf("ExchangeTradedFundFlag", bool(det.get("etf")))
        w.close("ShareClass")
    elif k in ("WA", "OP"):
        tag = "Warrant" if k == "WA" else "Option"
        w.open(tag)
        if k == "OP":
            w.leaf("Type", det["otype"])
            w.leaf("StockMarket", det["mic"])
        else:
            emit_company(w, "Issuer", det["issuer"])
        if k == "OP":
            w.leaf("ExecutionStyle", "Europe")
        w.leaf("ContractSize", det["size"])
        w.leaf("MaturityDate", det["maturity"].isoformat())
        w.leaf("CallPutIndicator", det["cp"])
        w.amounts("StrikePrice", (det["strike"], det["strike_ccy"]))
        emit_underlyings(w, det["underlying"])
        w.close(tag)
    elif k == "CE":
        w.open("Certificate")
        w.leaf("Type", det["ctype"])
        emit_underlyings(w, det["underlying"])
        w.leaf("StockMarket", det["mic"])
        emit_company(w, "Issuer", det["issuer"])
        w.leaf("MaturityDate", det["maturity"].isoformat())
        w.close("Certificate")
    elif k == "FU":
        w.open("Future")
        w.leaf("Type", det["ftype"])
        w.leaf("ContractSize", det["size"])
        w.leaf("MaturityDate", det["maturity"].isoformat())
        emit_company(w, "Counterparty", CLEARING_HOUSE)
        w.leaf("LastTradeDate", (det["maturity"] - timedelta(days=2)).isoformat())
        w.leaf("StockMarket", det["mic"])
        emit_underlyings(w, det["underlying"])
        w.close("Future")
    elif k == "FX":
        w.open("FXForward")
        w.leaf("CurrencyBuy", det["buy"][0])
        w.leaf("AmountBuy", det["buy"][1])
        w.leaf("CurrencySell", det["sell"][0])
        w.leaf("AmountSell", det["sell"][1])
        w.leaf("AgreedFxRate", det["rate"])
        w.leaf("StartDate", det["start"].isoformat())
        w.leaf("MaturityDate", det["maturity"].isoformat())
        emit_company(w, "Counterparty", det["cpty"])
        w.leaf("Deliverable", True)
        w.close("FXForward")
    elif k == "SW":
        w.open("Swap")
        w.leaf("Type", det["stype"])
        w.leaf("StartDate", det["start"].isoformat())
        w.leaf("MaturityDate", det["maturity"].isoformat())
        emit_company(w, "Counterparty", det["cpty"])
        w.open("Legs")
        for leg in det["legs"]:
            w.open("Leg")
            w.leaf("Type", leg["type"])
            w.leaf("Currency", leg["ccy"])
            w.leaf("Notional", leg["notional"])
            w.leaf("YieldType", leg.get("yield"))
            w.leaf("Spread", leg.get("spread"))
            w.leaf("FixedRate", leg.get("fixed"))
            w.leaf("RecoveryRate", leg.get("recovery"))
            w.leaf("PayFrequency", leg.get("freq"))
            w.leaf("YieldDayConvention", leg.get("daycount"))
            if leg.get("underlying"):
                w.open("Underlying")
                w.leaf("ISIN", leg["underlying"])
                w.close("Underlying")
            w.close("Leg")
        w.close("Legs")
        w.close("Swap")
    elif k == "CM":
        w.open("CallMoney")
        w.leaf("StartDate", det["start"].isoformat())
        w.leaf("MaturityDate", det["maturity"].isoformat())
        w.leaf("InterestRate", det["rate"])
        emit_company(w, "Counterparty", det["bank"])
        w.close("CallMoney")
    elif k == "AC":
        w.open("Account")
        w.leaf("IndicatorCreditDebit", "Credit")
        w.leaf("InterestRateCredit", det["credit"])
        emit_company(w, "Counterparty", det["bank"])
        w.close("Account")
    elif k == "FE":
        w.open("Fee")
        w.leaf("Type", "Management and depositary fees")
        emit_company(w, "Counterparty", det["bank"])
        w.close("Fee")


def emit_underlyings(w, underlying):
    utype, name, isin = underlying
    w.open("Underlyings")
    w.open("Underlying")
    w.leaf("Type", utype)
    w.leaf("Name", name)
    w.open("Identifiers")
    w.leaf("ISIN", isin)
    w.close("Identifiers")
    w.close("Underlying")
    w.close("Underlyings")


# ---------------------------------------------------------------------------------------------
# breakdowns
# ---------------------------------------------------------------------------------------------

def breakdown(doc, positions, label_of):
    groups = {}
    for p in positions:
        label = label_of(p)
        groups[label] = groups.get(label, D(0)) + p["value"]
    labels = sorted(groups, key=lambda k: (-groups[k], k))
    pcts = largest_remainder([groups[k] for k in labels], doc.tna, "0.01")
    return list(zip(labels, pcts))


def asset_class(p):
    return {"EQ": "Equities", "BO": "Bonds", "SC": "Investment funds", "WA": "Warrants", "CE": "Certificates",
            "OP": "Options", "FU": "Futures", "FX": "FX forwards", "SW": "Swaps", "CM": "Cash and deposits",
            "AC": "Cash and deposits", "FE": "Accrued fees"}[p["asset"]["kind"]]


def maturity_bucket(p):
    a = p["asset"]
    if a["kind"] != "BO":
        return "Other"
    years = (a["maturity"] - AS_OF).days / 365.25
    for limit, label in ((1, "0-1 years"), (3, "1-3 years"), (5, "3-5 years"), (7, "5-7 years"), (10, "7-10 years")):
        if years < limit:
            return label
    return "10+ years"


# ---------------------------------------------------------------------------------------------
# the four funds
# ---------------------------------------------------------------------------------------------

def fund_record(code, name, short, inception, policy, costs, sfdr, managers):
    return {"lei": make_lei(code), "name": name, "short": short, "country": "AT", "inception": inception,
            "policy": policy, "costs": costs, "sfdr": sfdr, "managers": managers}


def perf_other(rng):
    return [("YTD", q(D(rng.randrange(-300, 1400)) / 100)), ("1 Year", q(D(rng.randrange(-200, 1800)) / 100)),
            ("3 Years", q(D(rng.randrange(150, 1100)) / 100)), ("Since launch", q(D(rng.randrange(2000, 9000)) / 100))]


def benchmark_history(rng, key, vol_bp=80):
    level = INDICES[key][2]
    hist = nav_history(rng, level, vol_bp)
    return {"name": INDICES[key][0] + " (Net Total Return, EUR)", "history": hist}


def global_equity():
    doc = Doc(1001)
    fund = fund_record("FNDGLOBEQ001", "Example Global Equity Fund", "EX Global Equity", date(2014, 3, 3),
                       "Invests worldwide in large and mid cap equities; currency risk of the USD class is hedged.",
                       [("Ongoing Charges", D("1.42")), ("Transaction Costs", D("0.11"))], "8",
                       [("Anna Example", "2019-07-01", "Lead Portfolio Manager"), ("Lukas Sample", "2022-01-10", "Co-Manager")])
    target = D("612438000")
    held = add_equities(doc, 112, target * D("0.958"), D("0.045"))
    add_accounts(doc, [("EUR", q(target * D("0.0183"))), ("USD", D("3874211.56")), ("GBP", D("412907.13")),
                       ("JPY", D("88340211")), ("CHF", D("218774.40"))])
    add_index_futures(doc, [("EURO50", 96, D(10), date(2025, 12, 19), "-18432.00"),
                            ("US500", 18, D(50), date(2025, 12, 19), "27615.40")])
    hedge_usd = q(target * D("0.13") * FX["USD"], "1")
    add_fx_hedges(doc, "USD", hedge_usd, [(date(2025, 11, 28), "12.4"), (date(2025, 12, 19), "31.7"), (date(2026, 1, 30), "52.9")])
    add_fee_accrual(doc, D("1.31"))
    equity_trades(doc, held, 46)
    dividends(doc, held, 31)
    account_interest(doc)
    classes = build_share_classes(doc, fund, [
        {"code": "R", "name_suffix": "EUR R (acc)", "type_name": "Retail, accumulating", "ccy": "EUR", "weight": D("0.46"),
         "nav_hint": D("187.35"), "isin_code": "F0101", "inception": date(2014, 3, 3), "registered": ["AT", "DE", "IT"],
         "minimum": D("100"), "fee": D("1.50"), "max_fee": D("2.00"), "front_load": D("5"), "flows": 9, "flow_size": 1,
         "perf_other": perf_other(doc.rng)},
        {"code": "I", "name_suffix": "EUR I (dist)", "type_name": "Institutional, distributing", "ccy": "EUR",
         "weight": D("0.41"), "nav_hint": D("1342.18"), "isin_code": "F0102", "inception": date(2016, 9, 1),
         "registered": ["AT", "DE"], "minimum": D("500000"), "fee": D("0.65"), "max_fee": D("1.00"),
         "distribution": D("18.40"), "flows": 5, "flow_size": D("0.4"), "perf_other": perf_other(doc.rng)},
        {"code": "RH", "name_suffix": "USD R (acc, hedged)", "type_name": "Retail, accumulating, USD hedged", "ccy": "USD",
         "weight": D("0.13"), "nav_hint": D("143.92"), "isin_code": "F0103", "inception": date(2019, 5, 6),
         "registered": ["AT", "DE", "CH"], "minimum": D("100"), "fee": D("1.50"), "max_fee": D("2.00"),
         "hedged": True, "flows": 6, "perf_other": perf_other(doc.rng)},
    ])
    equities = [p for p in doc.positions if p["asset"]["kind"] == "EQ"]
    breakdowns = [
        ("Asset class", breakdown(doc, doc.positions, asset_class)),
        ("Country", breakdown(doc, doc.positions, lambda p: p["asset"]["country"] if p["asset"]["kind"] == "EQ" else "Cash and other")),
        ("Currency", breakdown(doc, doc.positions, lambda p: p["ccy"])),
        ("Sector (NACE)", breakdown(doc, doc.positions, lambda p: p["asset"]["section"] if p["asset"]["kind"] == "EQ" else "Cash and other")),
    ]
    assert len(equities) == 112
    risk = [("BETA FACTOR", D("1.03"), False, "Beta against the benchmark, 1 year daily returns"),
            ("TRACKING ERROR", D("2.87"), True, "Ex-post tracking error, %"),
            ("VOLATILITY OF RETURNS", D("13.42"), True, "Annualised volatility of daily returns, %"),
            ("ACTIVE SHARE", D("61.30"), False, "Active share against the benchmark, %"),
            ("VAR ABSOLUTE UCITS", D("6.94"), False, "Relative VaR 99%/20 days in % of NAV"),
            ("LEVERAGE GROSS", D("118.70"), False, "Gross method leverage, % of NAV"),
            ("LIQUIDATED WITHIN ONE DAY", D("94.10"), False, "Share of the portfolio that can be sold within 1 day, %")]
    return doc, fund, classes, breakdowns, risk, benchmark_history(doc.rng, "WORLD")


def euro_bond():
    doc = Doc(2002)
    fund = fund_record("FNDEUROBO001", "Example Euro Bond Fund", "EX Euro Bond", date(2009, 6, 15),
                       "Invests in investment grade EUR bonds of governments, agencies, covered and corporate issuers.",
                       [("Ongoing Charges", D("0.68")), ("Transaction Costs", D("0.04"))], "6",
                       [("Clara Example", "2017-04-01", "Lead Portfolio Manager")])
    target = D("843217000")
    held = add_bonds(doc, 200, target * D("0.962"), lot=D("100000"))
    add_accounts(doc, [("EUR", q(target * D("0.021")))])
    _, _, bund_level = INDICES["BUND"]
    for k, (contracts, maturity, vm) in enumerate([(-85, date(2025, 12, 8), "41820.00"), (-40, date(2026, 3, 9), "8730.00"),
                                                    (30, date(2025, 12, 8), "-6240.00"), (-25, date(2025, 12, 8), "11870.00")]):
        name = ["Example Euro-Bund", "Example Euro-Bund", "Example Euro-Schatz", "Example Euro-Bobl"][k]
        a = doc.asset(counterparty_asset("FU", f"FU-IRF-{k}", f"{name} Future {maturity:%b %Y}", "EUR", "DE", {
            "ftype": "IRF", "size": D("100000"), "maturity": maturity, "mic": "XEUR",
            "underlying": ("Future", "Example Euro-Bund 10Y Notional", INDICES["BUND"][1])}))
        exposure = q(D(contracts) * bund_level / 100 * D("100000"))
        doc.position(a, D(vm), {"type": "Future", "contracts": D(contracts), "price": bund_level, "vm": D(vm)},
                     exposures=[("Commitment", exposure)], risk=[("MODIFIED DURATION", D("7.94"))])
    cpty = OTC_COUNTERPARTIES[0]
    a = doc.asset(counterparty_asset("SW", "SW-IRS-1", "Interest rate swap pay 2.315% / receive 6M Euribor 2035", "EUR", "DE", {
        "stype": "Interestrateswap", "start": date(2025, 3, 12), "maturity": date(2035, 3, 12), "cpty": cpty, "legs": [
            {"type": "SELL", "ccy": "EUR", "notional": D("50000000"), "yield": "Fixed Rate", "fixed": D("2.315"), "freq": "YEAR",
             "daycount": "30/360"},
            {"type": "BUY", "ccy": "EUR", "notional": D("50000000"), "yield": "Variable Rate", "spread": D("0"), "freq": "SEMI",
             "daycount": "ACT/360"}]}))
    doc.position(a, D("-284611.25"), {"type": "Swap", "legs": [("BUY", D("50213904.11")), ("SELL", D("-50498515.36"))]},
                 exposures=[("Notional", D("50000000"))], risk=[("MODIFIED DURATION", D("-8.42"))])
    add_fee_accrual(doc, D("0.61"))
    bond_trades(doc, held, 44)
    coupons(doc, held)
    account_interest(doc)
    classes = build_share_classes(doc, fund, [
        {"code": "R", "name_suffix": "EUR R (acc)", "type_name": "Retail, accumulating", "ccy": "EUR", "weight": D("0.38"),
         "nav_hint": D("112.84"), "isin_code": "F0201", "inception": date(2009, 6, 15), "registered": ["AT", "DE"],
         "minimum": D("50"), "fee": D("0.60"), "max_fee": D("1.00"), "front_load": D("3"), "flows": 8, "vol_bp": 25,
         "perf_other": perf_other(doc.rng)},
        {"code": "I", "name_suffix": "EUR I (dist)", "type_name": "Institutional, distributing", "ccy": "EUR",
         "weight": D("0.62"), "nav_hint": D("1018.67"), "isin_code": "F0202", "inception": date(2012, 1, 16),
         "registered": ["AT", "DE", "LU"], "minimum": D("1000000"), "fee": D("0.30"), "max_fee": D("0.60"),
         "distribution": D("21.75"), "flows": 4, "flow_size": D("0.6"), "vol_bp": 25, "perf_other": perf_other(doc.rng)},
    ])
    breakdowns = [
        ("Asset class", breakdown(doc, doc.positions, asset_class)),
        ("Issuer type", breakdown(doc, doc.positions, lambda p: p["asset"].get("sector", "Cash and other"))),
        ("Rating", breakdown(doc, doc.positions, lambda p: p["asset"].get("rating", "Cash and other"))),
        ("Maturity", breakdown(doc, doc.positions, maturity_bucket)),
    ]
    bonds = [p for p in doc.positions if p["asset"]["kind"] == "BO"]
    invested = sum(p["value"] for p in bonds)
    dur = q(sum(p["value"] * p["risk"][0][1] for p in bonds) / invested, "0.01")
    ytm = q(sum(p["value"] * p["risk"][1][1] for p in bonds) / invested, "0.01")
    risk = [("MODIFIED DURATION", dur, False, "Modified duration of the bond portfolio (before futures and swaps)"),
            ("YIELD", ytm, True, "Average yield to maturity of the bonds, %"),
            ("VOLATILITY OF RETURNS", D("4.18"), True, "Annualised volatility of daily returns, %"),
            ("VAR ABSOLUTE UCITS", D("3.12"), False, "Relative VaR 99%/20 days in % of NAV"),
            ("LEVERAGE GROSS", D("134.20"), False, "Gross method leverage, % of NAV")]
    return doc, fund, classes, breakdowns, risk, benchmark_history(doc.rng, "EUROAGG", 25)


def multi_asset():
    doc = Doc(3003)
    rng = doc.rng
    fund = fund_record("FNDMULTI0001", "Example Multi Asset Opportunities Fund", "EX Multi Asset", date(2018, 11, 5),
                       "Flexible multi-asset fund; uses listed and OTC derivatives for hedging and efficient portfolio management.",
                       [("Ongoing Charges", D("1.58")), ("Performance Fee", D("0.21")), ("Transaction Costs", D("0.19"))], "6",
                       [("Martin Example", "2018-11-05", "Lead Portfolio Manager"), ("Sofia Sample", "2021-03-01", "Derivatives")])
    target = D("287905000")
    held = add_equities(doc, 25, target * D("0.36"), D("0.035"))
    bonds = add_bonds(doc, 20, target * D("0.33"), lot=D("100000"))
    # target funds (ETFs and share classes of fictional third-party funds)
    third_party = party("TPMANAGER001", "Sample Index Funds plc", "IE", "Dublin", "plc")
    for k in range(6):
        price = q(D(rng.randrange(4500, 21000)) / 100)
        a = doc.asset({"kind": "SC", "key": f"SC-ETF-{k}", "name": f"Sample {['Emerging Markets', 'Gold', 'Japan', 'Global REIT', 'EUR High Yield', 'US Tech'][k]} UCITS ETF",
                       "ccy": "EUR" if k != 5 else "USD", "country": "IE", "isin": make_isin("IE", "S%04d" % (k + 1)),
                       "details": {"manager": third_party, "mic": "XETR", "etf": True}, "price": price})
        units = (target * D("0.012") * (k % 3 + 1) / price).to_integral_value()
        local = units * price
        doc.position(a, eur(local, a["ccy"]), {"type": "ShareClass", "units": units, "price": price},
                     exposures=[("Market value", eur(local, a["ccy"]))])
    issuer_bank = OTC_COUNTERPARTIES[1]
    for k in range(3):
        e = held[k][0]
        price = q(D(rng.randrange(120, 1900)) / 100)
        a = doc.asset({"kind": "WA", "key": f"WA-{k}", "name": f"Call warrant on {e['name']} {date(2026, 6, 19):%m/%Y}",
                       "ccy": "EUR", "country": "DE", "isin": make_isin("DE", "W%04d" % (k + 1)), "price": price,
                       "details": {"issuer": issuer_bank, "size": D("0.1"), "maturity": date(2026, 6, 19), "cp": "CALL",
                                   "strike": q(e["price"] * D("1.08")), "strike_ccy": e["ccy"],
                                   "underlying": ("Security", e["name"], e["isin"])}})
        units = D(rng.randrange(20, 80)) * 1000
        doc.position(a, q(units * price), {"type": "Warrant", "units": units, "price": price},
                     exposures=[("Delta-adjusted", q(units * D("0.1") * eur(e["price"], e["ccy"]) * D("0.55")))],
                     underlyings=[(e["isin"], D("0.55"))])
    for k, (ctype, name, idx) in enumerate([("Index", "Discount certificate", "EURO50"), ("Commodity", "Gold tracker certificate", None),
                                             ("Index", "Bonus certificate", "US500")]):
        price = q(D(rng.randrange(8000, 24000)) / 100)
        under = ("Index", INDICES[idx][0], INDICES[idx][1]) if idx else ("Other", "Gold spot (troy ounce)", make_isin("XS", "G0001"))
        a = doc.asset({"kind": "CE", "key": f"CE-{k}", "name": f"{name} on {under[1]} 2026", "ccy": "EUR", "country": "DE",
                       "isin": make_isin("DE", "C%04d" % (k + 1)), "price": price,
                       "details": {"ctype": ctype, "underlying": under, "mic": "XSTU", "issuer": issuer_bank,
                                   "maturity": date(2026, 12, 18)}})
        units = D(rng.randrange(15, 60)) * 1000
        doc.position(a, q(units * price), {"type": "Certificate", "units": units, "price": price},
                     exposures=[("Market value", q(units * price))])
    for k in range(6):  # listed index and equity options
        idx = ["EURO50", "US500"][k % 2]
        name, isin, level = INDICES[idx]
        cp = "PUT" if k < 4 else "CALL"
        strike = q(level * (D("0.94") if cp == "PUT" else D("1.05")), "1")
        ccy = "USD" if idx == "US500" else "EUR"
        maturity = [date(2025, 12, 19), date(2026, 3, 20), date(2026, 6, 19)][k % 3]
        premium = q(D(rng.randrange(2400, 14000)) / 100)
        contracts = D(rng.randrange(40, 160))
        mult = D(10) if ccy == "EUR" else D(100)
        a = doc.asset({"kind": "OP", "key": f"OP-{k}", "name": f"{name} {cp.title()} {strike} {maturity:%b %Y}", "ccy": ccy,
                       "country": "DE" if ccy == "EUR" else "US",
                       "details": {"otype": "IO", "mic": "XEUR" if ccy == "EUR" else "XCBO", "size": mult, "maturity": maturity,
                                   "cp": cp, "strike": strike, "strike_ccy": ccy, "underlying": ("Index", name, isin)}})
        delta = D("-0.31") if cp == "PUT" else D("0.42")
        value = eur(contracts * premium * mult, ccy)
        doc.position(a, value, {"type": "Option", "contracts": contracts, "price": premium},
                     exposures=[("Delta-adjusted", eur(contracts * mult * level * delta, ccy))], risk=[("DELTA", delta)],
                     underlyings=[(isin, delta)])
    add_index_futures(doc, [("EURO50", -45, D(10), date(2025, 12, 19), "9314.50"), ("US500", 12, D(50), date(2025, 12, 19), "-4127.80")])
    for k, (contracts, vm) in enumerate([(-60, "21480.00"), (35, "-7215.00"), (-20, "3260.00")]):
        maturity = [date(2025, 12, 8), date(2025, 12, 8), date(2026, 3, 9)][k]
        a = doc.asset(counterparty_asset("FU", f"FU-IRF-{k}", f"Example Euro-Bund Future {maturity:%b %Y} ({k + 1})", "EUR", "DE", {
            "ftype": "IRF", "size": D("100000"), "maturity": maturity, "mic": "XEUR",
            "underlying": ("Future", INDICES["BUND"][0], INDICES["BUND"][1])}))
        doc.position(a, D(vm), {"type": "Future", "contracts": D(contracts), "price": INDICES["BUND"][2], "vm": D(vm)},
                     exposures=[("Commitment", q(D(contracts) * INDICES["BUND"][2] * 1000))])
    add_fx_hedges(doc, "USD", D("41850000"), [(date(2025, 12, 19), "28.3"), (date(2026, 1, 30), "51.2")])
    add_fx_hedges(doc, "CHF", D("18230000"), [(date(2025, 12, 19), "-21.4")])
    add_fx_hedges(doc, "GBP", D("6120000"), [(date(2025, 11, 28), "7.9")])
    swaps = [
        ("Interestrateswap", "Interest rate swap receive 2.10% / pay 6M Euribor 2030", D("-91245.60"), [
            {"type": "BUY", "ccy": "EUR", "notional": D("20000000"), "yield": "Fixed Rate", "fixed": D("2.10"), "freq": "YEAR", "daycount": "30/360"},
            {"type": "SELL", "ccy": "EUR", "notional": D("20000000"), "yield": "Variable Rate", "spread": D("0"), "freq": "SEMI", "daycount": "ACT/360"}]),
        ("Crosscurrencyswap", "Cross currency swap EUR/USD 2028", D("212480.35"), [
            {"type": "BUY", "ccy": "USD", "notional": D("15000000"), "yield": "Variable Rate", "spread": D("0.1450"), "freq": "QURT", "daycount": "ACT/360"},
            {"type": "SELL", "ccy": "EUR", "notional": D("13000000"), "yield": "Variable Rate", "spread": D("0"), "freq": "QURT", "daycount": "ACT/360"}]),
        ("Creditdefaultswap", f"CDS protection bought on {BONDS[150]['issuer']} 5Y", D("-38914.20"), [
            {"type": "SELL", "ccy": "EUR", "notional": D("10000000"), "yield": "Fixed Rate", "fixed": D("1.00"), "freq": "QURT", "daycount": "ACT/360",
             "recovery": D("40"), "underlying": BONDS[150]["isin"]},
            {"type": "BUY", "ccy": "EUR", "notional": D("10000000")}]),
        ("Totalreturnswap", f"Total return swap on {INDICES['EURO50'][0]}", D("146093.70"), [
            {"type": "BUY", "ccy": "EUR", "notional": D("12000000"), "underlying": INDICES["EURO50"][1]},
            {"type": "SELL", "ccy": "EUR", "notional": D("12000000"), "yield": "Variable Rate", "spread": D("0.35"), "freq": "QURT", "daycount": "ACT/360"}]),
    ]
    for k, (stype, name, mtm, legs) in enumerate(swaps):
        cpty = OTC_COUNTERPARTIES[k % 3]
        a = doc.asset(counterparty_asset("SW", f"SW-{k}", name, "EUR", cpty["country"], {
            "stype": stype, "start": date(2025, 2, 3 + k), "maturity": date(2028 + k, 2, 3 + k), "cpty": cpty, "legs": legs}))
        notional = eur(legs[0]["notional"], legs[0]["ccy"])
        doc.position(a, mtm, {"type": "Swap", "legs": [("BUY", q(notional + mtm / 2)), ("SELL", q(-notional + mtm / 2))]},
                     exposures=[("Notional", notional)])
    a = doc.asset(counterparty_asset("CM", "CM-1", "Call money EUR at Example Depositary Bank AG", "EUR", "AT", {
        "start": date(2025, 10, 20), "maturity": date(2025, 11, 3), "rate": D("1.93"), "bank": DEPOSITARY}))
    doc.position(a, D("8500000.00"), {"type": "CallMoney", "local": D("8500000.00")}, exposures=[("Market value", D("8500000.00"))])
    add_accounts(doc, [("EUR", D("6218403.92")), ("USD", D("1342877.10")), ("CHF", D("402118.65"))])
    add_fee_accrual(doc, D("1.52"))
    equity_trades(doc, held, 24, exits=1)
    bond_trades(doc, bonds, 12)
    dividends(doc, held, 9)
    coupons(doc, bonds)
    account_interest(doc)
    classes = build_share_classes(doc, fund, [
        {"code": "R", "name_suffix": "EUR R (acc)", "type_name": "Retail, accumulating", "ccy": "EUR", "weight": D("0.52"),
         "nav_hint": D("128.41"), "isin_code": "F0301", "inception": date(2018, 11, 5), "registered": ["AT", "DE"],
         "minimum": D("100"), "fee": D("1.60"), "max_fee": D("2.00"), "front_load": D("4"), "flows": 7, "vol_bp": 55,
         "perf_other": perf_other(rng)},
        {"code": "I", "name_suffix": "EUR I (acc)", "type_name": "Institutional, accumulating", "ccy": "EUR", "weight": D("0.22"),
         "nav_hint": D("1186.05"), "isin_code": "F0302", "inception": date(2019, 2, 1), "registered": ["AT", "DE"],
         "minimum": D("250000"), "fee": D("0.80"), "max_fee": D("1.20"), "flows": 3, "flow_size": D("0.3"), "vol_bp": 55,
         "perf_other": perf_other(rng)},
        {"code": "RH-CHF", "name_suffix": "CHF R (acc, hedged)", "type_name": "Retail, accumulating, CHF hedged", "ccy": "CHF",
         "weight": D("0.07"), "nav_hint": D("104.77"), "isin_code": "F0303", "inception": date(2021, 4, 12),
         "registered": ["AT", "CH"], "minimum": D("100"), "fee": D("1.60"), "max_fee": D("2.00"), "hedged": True, "flows": 4,
         "vol_bp": 55, "perf_other": perf_other(rng)},
        {"code": "RH-USD", "name_suffix": "USD R (acc, hedged)", "type_name": "Retail, accumulating, USD hedged", "ccy": "USD",
         "weight": D("0.19"), "nav_hint": D("131.66"), "isin_code": "F0304", "inception": date(2020, 6, 2),
         "registered": ["AT", "DE", "CH"], "minimum": D("100"), "fee": D("1.60"), "max_fee": D("2.00"), "hedged": True, "flows": 5,
         "vol_bp": 55, "perf_other": perf_other(rng)},
    ])
    breakdowns = [("Asset class", breakdown(doc, doc.positions, asset_class)),
                  ("Currency", breakdown(doc, doc.positions, lambda p: p["ccy"]))]
    risk = [("NET EQUITY DELTA", D("38.40"), False, "Net equity exposure incl. derivatives, % of NAV"),
            ("MODIFIED DURATION", D("3.86"), False, "Portfolio modified duration incl. futures and swaps"),
            ("VOLATILITY OF RETURNS", D("7.95"), True, "Annualised volatility of daily returns, %"),
            ("VAR ABSOLUTE UCITS", D("8.71"), False, "Absolute VaR 99%/20 days in % of NAV"),
            ("LEVERAGE GROSS", D("187.30"), False, "Gross method leverage, % of NAV"),
            ("LEVERAGE USAGE", D("41.20"), False, "Commitment method leverage, % of NAV")]
    return doc, fund, classes, breakdowns, risk, None


def fund_of_funds():
    doc = Doc(4004)
    rng = doc.rng
    fund = fund_record("FNDFOFBAL001", "Example Balanced Fund of Funds", "EX Balanced FoF", date(2011, 10, 3),
                       "Fund of funds investing in equity, bond and money market funds of several managers.",
                       [("Ongoing Charges", D("1.96")), ("Transaction Costs", D("0.06"))], "8",
                       [("Thomas Example", "2015-01-01", "Lead Portfolio Manager")])
    fund["fof"] = True
    target = D("156382000")
    managers = [party("TPMANAGER%03d" % k, name, cc, city, lf) for k, (name, cc, city, lf) in enumerate([
        ("Sample Index Funds plc", "IE", "Dublin", "plc"), ("Sample Capital Management S.A.", "LU", "Luxembourg", "S.A."),
        ("Sample Kapitalanlagegesellschaft mbH", "DE", "Frankfurt am Main", "mbH"),
        ("Sample Investment Managers Ltd", "GB", "London", "Ltd"), ("Example Asset Management GmbH", "AT", "Vienna", "GmbH")], start=1)]
    styles = ["Global Equity", "European Equity", "US Equity", "Emerging Markets Equity", "Japan Equity", "Global Small Cap",
              "Euro Government Bond", "Euro Corporate Bond", "Global Aggregate Bond", "EUR High Yield", "Emerging Markets Debt",
              "Euro Money Market", "Inflation Linked Bond", "Global Infrastructure", "Global Real Estate"]
    weights = [D(rng.randrange(40, 100)) for _ in range(35)]
    total = sum(weights)
    lookthrough = {}
    for k in range(35):
        style = styles[k % len(styles)]
        mgr = managers[k % len(managers)]
        country = mgr["country"]
        price = q(D(rng.randrange(4200, 32000)) / 100)
        etf = k % 4 == 0
        a = doc.asset({"kind": "SC", "key": f"SC-{k}", "name": f"{mgr['name'].split(' ')[0]} {style} Fund {'UCITS ETF' if etf else 'I EUR'} ({k + 1})",
                       "ccy": "EUR", "country": country, "isin": make_isin(country if country != "GB" else "IE", "T%04d" % (k + 1)),
                       "price": price, "details": {"manager": mgr, "mic": "XETR" if etf else None, "etf": etf}})
        units = (target * D("0.975") * weights[k] / total / price).quantize(D("0.001"))
        value = q(units * price)
        doc.position(a, value, {"type": "ShareClass", "units": units, "price": price}, exposures=[("Market value", value)])
        bucket = "equity" if "Equity" in style or "Small Cap" in style else ("bond" if "Bond" in style or "Debt" in style or "Yield" in style else "other")
        lookthrough[bucket] = lookthrough.get(bucket, D(0)) + value
    add_accounts(doc, [("EUR", D("3127944.18")), ("USD", D("288421.70"))])
    add_fee_accrual(doc, D("1.12"))
    # look-through (level 1): the target funds decomposed into the securities they hold (a sample of each bucket)
    lt_positions = []
    pools = {"equity": EQUITIES[:30], "bond": BONDS[:30], "other": BONDS[-10:]}
    for bucket, pool in pools.items():
        amount = lookthrough.get(bucket, D(0))
        for k, sec in enumerate(pool):
            a = doc.asset(sec)
            part = q(amount / len(pool)) if k < len(pool) - 1 else amount - q(amount / len(pool)) * (len(pool) - 1)
            if sec["kind"] == "EQ":
                units = (part * FX[sec["ccy"]] / sec["price"]).quantize(D("0.0001"))
                block = {"type": "Equity", "units": units, "price": sec["price"], "local": q(units * sec["price"])}
            else:
                nominal = (part / sec["price"] * 100).quantize(D("0.01"))
                block = {"type": "Bond", "nominal": nominal, "price": sec["price"], "dirty": sec["price"], "clean": part,
                         "accrued": D("0.00"), "days": 0, "last_coupon": None}
            lt_positions.append({"asset": a, "value": part, "block": block, "ccy": sec["ccy"], "exposures": [], "risk": [],
                                 "underlyings": [], "fx": None})
    cash_and_fees = sum(p["value"] for p in doc.positions if p["asset"]["kind"] in ("AC", "FE"))
    for p in doc.positions:
        if p["asset"]["kind"] in ("AC", "FE"):
            lt_positions.append(p)
    assert sum(p["value"] for p in lt_positions) == doc.tna, (sum(p["value"] for p in lt_positions), doc.tna, cash_and_fees)
    fund["lookthrough"] = lt_positions
    # fund distributions received from two distributing target funds
    for p in doc.positions[1:3]:
        a = p["asset"]
        per_unit = q(a["price"] * D("0.012"), "0.0001")
        gross = q(p["block"]["units"] * per_unit)
        doc.earnings.append({"kind": "Fund distribution", "asset": a, "ex": date(2025, 10, 8), "pay": date(2025, 10, 10),
                             "ccy": "EUR", "units": p["block"]["units"], "gross": gross, "net": gross, "wht": D(0),
                             "text": f"Distribution {a['name']}"})
    account_interest(doc)
    for d in trade_days(rng, 14):  # switches between target funds
        p = rng.choice(doc.positions[:35])
        a = p["asset"]
        side = "BUY" if rng.random() < 0.5 else "SELL"
        units = (p["block"]["units"] * D(rng.randrange(5, 25)) / 100).quantize(D("0.001"))
        local = q(units * a["price"])
        doc.transactions.append({"kind": side, "id": "", "date": d, "valuta": add_business_days(d, 2), "asset": a,
                                 "units": units, "price": a["price"], "local": local, "eur": local, "expenses": D("0.00"),
                                 "settle": local, "broker": BROKERS[2], "mic": a["details"].get("mic"), "order": "Market",
                                 "text": f"{'Subscription' if side == 'BUY' else 'Redemption'} {a['name']}"})
    classes = build_share_classes(doc, fund, [
        {"code": "T", "name_suffix": "EUR T (acc)", "type_name": "Retail, accumulating", "ccy": "EUR", "weight": D("0.71"),
         "nav_hint": D("163.28"), "isin_code": "F0401", "inception": date(2011, 10, 3), "registered": ["AT"],
         "minimum": D("50"), "fee": D("1.20"), "max_fee": D("1.50"), "front_load": D("4"), "flows": 10, "vol_bp": 45,
         "perf_other": perf_other(rng)},
        {"code": "A", "name_suffix": "EUR A (dist)", "type_name": "Retail, distributing", "ccy": "EUR", "weight": D("0.29"),
         "nav_hint": D("118.93"), "isin_code": "F0402", "inception": date(2011, 10, 3), "registered": ["AT", "DE"],
         "minimum": D("50"), "fee": D("1.20"), "max_fee": D("1.50"), "front_load": D("4"), "distribution": D("2.10"),
         "flows": 6, "vol_bp": 45, "perf_other": perf_other(rng)},
    ])
    breakdowns = [("Asset class", breakdown(doc, doc.positions, asset_class)),
                  ("Fund manager", breakdown(doc, doc.positions, lambda p: p["asset"]["details"]["manager"]["name"]
                                             if p["asset"]["kind"] == "SC" else "Cash and other"))]
    risk = [("VOLATILITY OF RETURNS", D("6.84"), True, "Annualised volatility of daily returns, %"),
            ("VAR ABSOLUTE UCITS", D("5.37"), False, "Absolute VaR 99%/20 days in % of NAV")]
    return doc, fund, classes, breakdowns, risk, None


FILES = {
    "Global-Equity-Fund_2025-10.xml": global_equity,
    "Euro-Bond-Fund_2025-10.xml": euro_bond,
    "Multi-Asset-Derivatives-Fund_2025-10.xml": multi_asset,
    "Fund-of-Funds_2025-10.xml": fund_of_funds,
}


def render(builder, doc_id):
    doc, fund, classes, breakdowns, risk, benchmark = builder()
    seq = 0
    for t in sorted(doc.transactions, key=lambda t: (t["date"], t["kind"] == "CASH")):
        if not t["id"] or t["kind"] != "CASH":
            seq += 1
            t["id"] = t["id"] or f"TRX-2025-10-{seq:04d}"
    doc.transactions.sort(key=lambda t: (t["date"], t["id"]))
    doc.earnings.sort(key=lambda e: (e["pay"], e["asset"]["uid"]))
    self_check(doc, classes)
    w = Writer()
    w.lines.append('<?xml version="1.0" encoding="UTF-8"?>')
    w.lines.append("<!-- Synthetic sample: fictional companies, funds and identifiers. Generated by make_realistic.py. -->")
    w.lines.append('<FundsXML4 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
                   f'xsi:noNamespaceSchemaLocation="{SCHEMA_URL}">')
    w.depth = 1
    emit_control(w, doc_id)
    w.open("Funds")
    emit_fund(w, doc, fund, classes, breakdowns, risk, benchmark)
    w.close("Funds")
    emit_assets(w, doc)
    w.depth = 0
    w.lines.append("</FundsXML4>")
    return w.text()


def self_check(doc, classes):
    tna = doc.tna
    assert tna > 0
    assert sum(largest_remainder([p["value"] for p in doc.positions], tna)) == D("100")
    assert sum(c["eur_tna"] for c in classes) == tna
    for c in classes:
        assert abs(q(c["ccy_tna"] / c["shares"]) - c["nav"]) < D("0.01")
        assert c["history"][-1][1] == c["nav"]
    for t in doc.transactions:
        assert t["valuta"] <= AS_OF and t["date"] <= t["valuta"]
    uids = [a["uid"] for a in doc.assets.values()]
    assert len(uids) == len(set(uids))
    ids = [t["id"] for t in doc.transactions]
    assert len(ids) == len(set(ids)), "transaction ids must be unique"
    for a in doc.assets.values():
        assert not a.get("isin") or isin_ok(a["isin"]), a


# ---------------------------------------------------------------------------------------------
# command line
# ---------------------------------------------------------------------------------------------

def lint(paths):
    problems, count = [], 0
    files = []
    for p in map(pathlib.Path, paths):
        files.extend(sorted(p.rglob("*.xml")) if p.is_dir() else [p])
    for f in files:
        text = f.read_text(encoding="utf-8")
        for tag, value in re.findall(r"<(ISIN|LEI)>([^<]*)</\1>", text):
            count += 1
            if not (isin_ok(value) if tag == "ISIN" else lei_ok(value)):
                problems.append(f"{f}: {tag} {value} has wrong check digits")
    for p in problems:
        print(p)
    print(f"{count} identifiers checked in {len(files)} files, {len(problems)} problem(s)")
    return 1 if problems else 0


def verify_online(folder):
    import json
    import urllib.parse
    import urllib.request
    isins, leis = set(), set()
    for f in sorted(folder.glob("*.xml")):
        text = f.read_text(encoding="utf-8")
        isins.update(v for v in re.findall(r"<ISIN>([^<]*)</ISIN>", text) if "XMPL" in v)
        leis.update(v for v in re.findall(r"<LEI>([^<]*)</LEI>", text) if v.startswith("XMPL"))
    headers = {"User-Agent": "fundsxml-examples-generator", "Accept": "application/json"}
    found = 0
    leis = sorted(leis)
    for i in range(0, len(leis), 100):
        url = "https://api.gleif.org/api/v1/lei-records?page[size]=200&filter[lei]=" + ",".join(leis[i:i + 100])
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as r:
            data = json.load(r)["data"]
        found += len(data)
        for rec in data:
            print("registered at GLEIF:", rec["id"])
    isins = sorted(isins)
    for i in range(0, len(isins), 100):
        query = "isin:(" + " OR ".join(isins[i:i + 100]) + ")"
        url = ("https://registers.esma.europa.eu/solr/esma_registers_firds/select?rows=100&wt=json&fl=isin&q="
               + urllib.parse.quote(query))
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as r:
            docs = json.load(r)["response"]["docs"]
        found += len(docs)
        for rec in docs:
            print("listed in ESMA FIRDS:", rec["isin"])
    print(f"{len(leis)} LEIs and {len(isins)} ISINs checked online, {found} registered")
    return 1 if found else 0


def main():
    here = pathlib.Path(__file__).resolve().parent
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", type=pathlib.Path, default=here)
    ap.add_argument("--only")
    ap.add_argument("--lint", nargs="+", metavar="PATH")
    ap.add_argument("--verify-online", action="store_true")
    args = ap.parse_args()
    if args.lint:
        return lint(args.lint)
    if args.verify_online:
        return verify_online(here)
    args.out.mkdir(parents=True, exist_ok=True)
    for name, builder in FILES.items():
        if args.only and args.only != name:
            continue
        doc_id = "EXAMPLE-" + name.replace(".xml", "").upper().replace("_", "-")
        with open(args.out / name, "w", encoding="utf-8", newline="\n") as f:
            f.write(render(builder, doc_id))
        print("wrote", args.out / name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
