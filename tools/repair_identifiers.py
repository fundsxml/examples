#!/usr/bin/env python3
"""Replace invalid or misattributed ISINs and LEIs in the sample files with synthetic ones.

Usage:  python tools/repair_identifiers.py [--check]

The small samples under FundsXML_Files/ used identifiers with wrong check digits
(e.g. XS2123456789) and real identifiers of unrelated parties (the fund LEI
529900T8BM49AURSDO55 belongs to Ubisecure Oy, AT0000A2QM66 is a silver
certificate). Each is replaced, in every text file of the repository, by a
synthetic identifier of the same length:

* ISIN: country prefix + "XMPL" + 5 characters + Luhn check digit. National
  numbering agencies of these countries start with a digit, so these were never
  issued (verified against ESMA FIRDS on 2026-11-16).
* LEI:  "XMPL00" + 12 characters + ISO 7064 MOD 97-10 check digits (not
  registered at GLEIF, verified on 2026-11-16).

Real identifiers of correctly named public securities and companies (Apple,
ASML, SAP ...) stay as reference data. Numbers are not touched, so CI checks on
values keep working. --check only reports what would change (exit 1 if any).
"""
import pathlib
import sys

ISINS = {
    "AT0000A2QM74": "ATXMPLS00015",  # share class, not in FIRDS
    "AT0000A2QM66": "ATXMPLS00023",  # share class; real ISIN of a silver certificate
    "IE00B5BMR087": "IEXMPLS00036",  # labelled Vanguard; real iShares Core S&P 500
    "DE0001102424": "DEXMPLS00045",  # labelled Bund 1.70% 2032; real Bund 0.5% 2027
    "XS2444622110": "XSXMPLS00050",  # wrong check digit
    "IE00B11XZB12": "IEXMPLS00069",  # wrong check digit
    "DE000PN738Q3": "DEXMPLS00078",  # wrong check digit
    "DE000SQ962F7": "DEXMPLS00086",  # wrong check digit
    "DE000XM03HC3": "DEXMPLS00094",  # wrong check digit
    "DE000DFM0XG2": "DEXMPLS00102",  # wrong check digit
    "DE000C0B6XV0": "DEXMPLS00110",  # wrong check digit
    "DE000C0B6YC8": "DEXMPLS00128",  # wrong check digit
    "DE000C0B6ZR4": "DEXMPLS00136",  # wrong check digit
    "XS2123456789": "XSXMPLS00142",  # wrong check digit (placeholder)
}

LEIS = {
    "529900T8BM49AURSDO55": "XMPL00SAMPLE00000127",  # fund LEI; real LEI of Ubisecure Oy
    "529900T8BM49AURSDO66": "XMPL00SAMPLE00000224",  # wrong check digits
    "724500Y6P2B0MRLY2T56": "XMPL00SAMPLE00000321",  # wrong check digits
    "529900T24R02QROQ3G03": "XMPL00SAMPLE00000418",  # wrong check digits
    "549300KL4K15T62YKV69": "XMPL00SAMPLE00000515",  # wrong check digits
    "635400MD3E0L5P9ZC956": "XMPL00SAMPLE00000612",  # wrong check digits
    "2138006E5Q6H983A2A43": "XMPL00SAMPLE00000709",  # wrong check digits
    "R0MI4MICVL8SP8AU2V54": "XMPL00SAMPLE00000806",  # wrong check digits
    "7LTWFZYKSA4V22TE2Y10": "XMPL00SAMPLE00000903",  # wrong check digits
    "G5GSEF7VJP5I7OUK5573": "XMPL00SAMPLE00001097",  # labelled HSBC; real LEI of Barclays Bank PLC
    "549300V65Q6MY42G2B26": "XMPL00SAMPLE00001194",  # wrong check digits
    "BFM8T61CT2L1QCEMIK50": "XMPL00SAMPLE00001291",  # labelled UBS Europe SE; real LEI of UBS AG
    "851WYGNLU20A61V15G44": "XMPL00SAMPLE00001388",  # wrong check digits
    "894500CK24P2281L1O36": "XMPL00SAMPLE00001485",  # wrong check digits
}

TEXT_SUFFIXES = {".xml", ".md", ".py", ".java", ".cs", ".mjs", ".js", ".xq", ".xsl", ".xslt", ".sch",
                 ".ps1", ".sh", ".json", ".yml", ".csv", ".txt", ".sql", ".html"}
SKIP_DIRS = {".git", ".venv", "node_modules", "target", "bin", "obj"}


def luhn_ok(isin: str) -> bool:
    digits = "".join(str(int(c, 36)) for c in isin[:11])
    total = 0
    for i, ch in enumerate(reversed(digits)):
        n = int(ch) * (2 if i % 2 == 0 else 1)
        total += n - 9 if n > 9 else n
    return (10 - total % 10) % 10 == int(isin[11])


def lei_ok(lei: str) -> bool:
    return int("".join(str(int(c, 36)) for c in lei)) % 97 == 1


def main() -> int:
    check_only = "--check" in sys.argv[1:]
    for old, new in ISINS.items():
        assert len(old) == len(new) == 12 and luhn_ok(new), (old, new)
    for old, new in LEIS.items():
        assert len(old) == len(new) == 20 and lei_ok(new), (old, new)
    mapping = {**ISINS, **LEIS}
    root = pathlib.Path(__file__).resolve().parent.parent
    changed = 0
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if SKIP_DIRS.intersection(path.relative_to(root).parts) or path.name == "repair_identifiers.py":
            continue
        with open(path, encoding="utf-8", newline="") as f:  # keep CRLF files as they are
            text = f.read()
        new_text = text
        for old, new in mapping.items():
            new_text = new_text.replace(old, new)
        if new_text != text:
            changed += 1
            print(path.relative_to(root))
            if not check_only:
                path.write_bytes(new_text.encode("utf-8"))
    print(f"{changed} file(s) {'to change' if check_only else 'changed'}")
    return 1 if check_only and changed else 0


if __name__ == "__main__":
    sys.exit(main())
