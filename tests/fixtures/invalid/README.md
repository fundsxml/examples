# Negative Test Fixtures

Deliberately broken copies of `FundsXML_Files/4.2.9/positions/Mixed-Fund_Positions.xml`.
Used by the negative path of the per-stack examples and by CI. The committed
positive sample must always pass; these must always fail their respective check.

| File | Mutation | Fails | Still passes |
|------|----------|-------|--------------|
| `xsd-invalid_Positions.xml` | ID_001 `TotalValue/Amount` set to the non-numeric string `NINE-MILLION` | **XSD** (`xs:decimal` violation) | — |
| `schematron-invalid_Positions.xml` | ID_001 `TotalPercentage` `8.33` → `28.33`, so position percentages sum to 120% | **Schematron** (`percentage-validations` pattern, ERROR) | XSD (structurally valid) |

The Schematron fixture targets the percentage-sum rule, which is now in its own
`percentage-validations` pattern (previously dead code — see
`Schematron_DataQuality_Checks/Basic_Checks/README.md`).

Regenerate after the canonical sample changes:

```bash
sed 's#<Amount ccy="EUR">9375000</Amount>#<Amount ccy="EUR">NINE-MILLION</Amount>#' \
  FundsXML_Files/4.2.9/positions/Mixed-Fund_Positions.xml > tests/fixtures/invalid/xsd-invalid_Positions.xml
sed 's#<TotalPercentage>8.33</TotalPercentage>#<TotalPercentage>28.33</TotalPercentage>#' \
  FundsXML_Files/4.2.9/positions/Mixed-Fund_Positions.xml > tests/fixtures/invalid/schematron-invalid_Positions.xml
```
