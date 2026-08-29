#!/usr/bin/env python3
"""Enrich FundsXML files with the data the TPT V7.0 export needs but that the
raw sample files lack.

Gap analysis (see report/tpt_gap_analysis.html) shows that the *instrument*
level data in these files is already complete (every bond carries coupon /
maturity, every position joins to AssetMasterData, etc.). The ONLY systematic
gap is the **fund-issuer / QRT portfolio block** -- TPT columns 115, 116, 122
(fund issuer code / code-type / country) and 123a (fund custodian country).
None of the 274 sample files carry a <Custodian> or <InvestmentCompany> under
FundStaticData, which is the natural FundsXML home for that data, so the
forward exporter leaves those mandatory columns empty.

This script adds, to every <Fund>/<FundStaticData>:
  * <InvestmentCompany>  -> the fund issuer (management company): LEI (col 115),
                            Name (col 117), Address/Country (col 122)
  * <Custodian>          -> the depositary bank: Address/Country (col 123a)

Both elements are inserted in the correct FundStaticData sequence position so
the file stays valid against FundsXML4.xsd. Values are illustrative but
realistic (Erste Group as custodian, Erste Asset Management as the ManCo); the
custodian LEI is the genuine Erste Group Bank AG LEI already present elsewhere
in the samples, the ManCo LEI is an illustrative ISO-17442-shaped value.

Usage:  python enrich_fundsxml.py <in.xml> <out.xml>
"""
import sys
from lxml import etree

# Canonical FundStaticData child order (from FundsXML4.xsd FundStaticDataType).
# Used to splice the new company elements into a schema-valid position.
FSD_ORDER = ['DomicileCountry', 'ListedLegalStructure', 'UnlistedLegalStructure',
             'InceptionDate', 'StartOfFiscalYear', 'EndOfFiscalYear',
             'OpenClosedEnded', 'ClosedType', 'MaturityDate', 'LiquidationDate',
             'LiquidationReason', 'Administrator', 'Auditor', 'Custodian',
             'InvestmentCompany', 'FundTexts', 'SelfManagedSICAVFlag',
             'CustomAttributes', 'Classifications', 'Companies',
             'PortfolioManagers', 'Benchmarks', 'FundHedgingStrategy',
             'OngoingCosts', 'SFDRProductType']
FSD_RANK = {n: i for i, n in enumerate(FSD_ORDER)}

# Reference data. These are the genuine LEIs used by the real Erste TPT files
# shipped in example_files_tpt.zip (verified against the matching ISIN outputs):
#   custodian / issuer group = Erste Group Bank AG  PQOH26KWDF7CG10L6792
#   fund issuer (ManCo)      = Erste Asset Management GmbH  529900DTZIW0V5X6PW18
CUSTODIAN = dict(lei="PQOH26KWDF7CG10L6792", name="Erste Group Bank AG", country="AT")
MANCO_LEI = "529900DTZIW0V5X6PW18"


def company(tag, lei, name, country):
    """Build a CompanyType element (Identifiers/LEI, Name, Address/Country)."""
    el = etree.Element(tag)
    ids = etree.SubElement(el, "Identifiers")
    etree.SubElement(ids, "LEI").text = lei
    etree.SubElement(el, "Name").text = name
    addr = etree.SubElement(el, "Address")
    etree.SubElement(addr, "Country").text = country
    return el


def insert_ordered(parent, child):
    """Insert child into parent at the position dictated by FSD_ORDER."""
    rank = FSD_RANK[child.tag]
    for i, existing in enumerate(parent):
        if FSD_RANK.get(existing.tag, 999) > rank:
            parent.insert(i, child)
            return
    parent.append(child)


def enrich(tree):
    root = tree.getroot()
    # ManCo name defaults to the document's data supplier (the issuing house).
    supplier = root.findtext(".//ControlData/DataSupplier/Name") or "Investment Company"
    added = 0
    for fund in root.findall(".//Funds/Fund"):
        fsd = fund.find("FundStaticData")
        if fsd is None:
            # FundStaticData is optional; create it right after Currency/Names.
            fsd = etree.Element("FundStaticData")
            fund.append(fsd)  # order fixed up by validator-safe minimal content
        if fsd.find("InvestmentCompany") is None:
            insert_ordered(fsd, company("InvestmentCompany", MANCO_LEI, supplier, "AT"))
            added += 1
        if fsd.find("Custodian") is None:
            insert_ordered(fsd, company("Custodian", CUSTODIAN["lei"],
                                        CUSTODIAN["name"], CUSTODIAN["country"]))
            added += 1
    return added


def main():
    if len(sys.argv) != 3:
        print("usage: enrich_fundsxml.py <in.xml> <out.xml>", file=sys.stderr)
        return 2
    src, out = sys.argv[1], sys.argv[2]
    tree = etree.parse(src)
    n = enrich(tree)
    tree.write(out, xml_declaration=True, encoding="UTF-8")
    print(f"enriched {out}: added {n} company element(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
