# Financial Analysis and Key Metrics

> When to read this file: When you need to analyze financial statements, calculate owner earnings, assess ROIC/ROE quality, or understand the concept of look-through earnings.

## Core Principle: See Through Accounting to Economic Reality

GAAP financial statements are the starting point, not the destination. Buffett always asks: **How much does this business truly earn?**

---

## Owner Earnings

Buffett introduced this concept in his 1986 shareholder letter as the best tool for measuring a business's true earning power.

```
Owner Earnings =
  Net Income
  + Depreciation, Depletion, and Amortization (D&A)
  − Maintenance CapEx required to maintain competitive position
  − Any required net increases in working capital
```

**Key Distinction — Two Types of Capital Expenditure:**

| Type | Nature | Treatment |
|-----|-----|---------|
| Maintenance CapEx | Must be spent or competitive position deteriorates | Must be deducted from owner earnings |
| Growth CapEx | Optional, used to expand new capacity | Not deducted (this portion generates future returns) |

**Why It Is More Reliable Than EBITDA:**
EBITDA adds back depreciation, implicitly assuming assets do not wear out. But assets do age, and maintaining operations requires real cash outlays.

**Methods for Estimating Maintenance CapEx:**
- Management sometimes discloses it
- Approximation: Depreciation × industry rule-of-thumb multiplier (close to 1:1 for asset-light businesses, potentially higher for capital-intensive ones)
- Compare against industry peers

---

## Key Financial Metrics

### Profitability

**ROE (Return on Equity)**
```
ROE = Net Income / Average Shareholders' Equity
```
- Buffett's standard: 10-year average >15%, with no excessive leverage
- Must decompose the source: margin expansion / asset turnover improvement / financial leverage increase
- ROE inflated by leverage is a trap, not an advantage

**ROIC (Return on Invested Capital)**
```
ROIC = NOPAT (Net Operating Profit After Tax) / Invested Capital (Equity + Interest-Bearing Debt − Cash)
```
- More honest than ROE; removes the distortion of capital structure
- Sustained >15% is excellent; >20% is exceptional
- **Value creation condition: ROIC > WACC (Weighted Average Cost of Capital)**

### Cash Flow Quality

**Cash Conversion Ratio**
```
Cash Conversion Ratio = Operating Cash Flow / Net Income
```
- Sustained >90%: High earnings quality, not reliant on accounting techniques
- Persistently <70%: Requires deep investigation (may indicate inflated receivables or aggressive revenue recognition)

**Free Cash Flow (FCF)**
```
FCF = Operating Cash Flow − Capital Expenditures (total)
```
Note: This includes growth CapEx, making it more appropriate for asset-light companies.
For high-CapEx companies in growth phases, the owner earnings lens is fairer.

### Balance Sheet Health

**Debt Safety:**
- Debt / EBITDA < 2x: Comfortable range
- Interest Coverage Ratio (EBIT / Interest Expense) > 5x: Sufficient buffer

**Worst-Case Scenario Test (mandatory):**
Assume revenue falls 30% — can the company:
1. Repay maturing debt?
2. Sustain core business operations?
3. Avoid dilutive financing?

### Earnings Quality Signals

**Red Flag Checklist (investigate further if any appear):**
- [ ] Accounts receivable growth persistently exceeds revenue growth
- [ ] Inventory growth persistently exceeds revenue growth
- [ ] Operating cash flow persistently below net income
- [ ] Frequent use of "adjusted earnings" with large divergences from GAAP
- [ ] Large goodwill balances from high-premium acquisitions with mediocre returns
- [ ] Frequent related-party transactions with non-transparent terms
- [ ] Auditor changes, or audit opinions with qualifications
- [ ] Management selling large amounts of shares

---

## Look-Through Earnings

Applicable to: **analyzing holding companies, investment holding companies, or businesses with substantial equity stakes not consolidated on the balance sheet**

An original concept Buffett first proposed in 1989 and first systematically calculated in 1990, addressing a major deficiency in GAAP's ability to reflect the true earning power of investee companies.

**Complete Calculation Formula:**
```
Look-Through Earnings =
  Berkshire's reported operating earnings (excluding capital gains and non-recurring items)
  + Berkshire's proportionate share of retained earnings from major investees
  − Estimated income taxes that would be owed if those retained earnings were distributed to Berkshire as dividends
```

**Actual Calculation Example from 1990 (Buffett's own words):**
> "Take $250 million, which is approximately our share of the 1990 retained operating earnings of our investees; subtract $30 million, for the incremental taxes we would have owed had that $250 million been paid to us as dividends; and add the remainder, $220 million, to our reported operating earnings of $371 million. Thus, our 1990 'look-through earnings' were about $590 million." — 1990 Buffett Letter to Shareholders

**Why It Matters:**
GAAP only allows recognition of dividends received when ownership is below 20%, causing retained earnings to disappear from the books. The Cap Cities/ABC example: in 1990, Berkshire's proportionate earnings exceeded $82 million, but only about $530,000 appeared on the GAAP books (dividends net of taxes). GAAP severely understates true earning power.

**The Link Between Look-Through Earnings and Intrinsic Value Growth:**
> "For Berkshire's intrinsic value to grow at an average of 15% per year, our look-through earnings must also grow at approximately the same rate." — 1989 Buffett Letter to Shareholders

**Why Retained Earnings Are Sometimes More Valuable Than Dividends:**
> "You must judge whether these undistributed earnings are as valuable to you as those already reported. We believe they are — and, in fact, may even be more valuable. The reason for this 'bird-in-the-bush-may-be-worth-two-in-the-hand' conclusion is that our investees are employing their retained earnings under the direction of managers who are talented and shareholder-oriented, and who sometimes find uses for capital within their own businesses that are superior to anything we could find for it." — 1989 Buffett Letter to Shareholders

**The Flaw of GAAP's "20% Threshold":**
Buffett criticized this arbitrary threshold as early as 1982: "The value of retained earnings to all shareholders depends on the efficiency with which they are deployed, not on the size of your ownership stake."

**Practical History:** Calculated and publicly reported for 8 consecutive years from 1990 to 1997; suspended in 1998 following the General Re acquisition; since 2018, replaced by a disclosure comparing investee dividends received versus retained earnings, carrying on the same spirit.

> "While no single figure captures everything perfectly, we believe look-through earnings more accurately reflect Berkshire's true earning power than the GAAP number." — 1992 Buffett Letter to Shareholders

**This framework must be used when analyzing Berkshire, and should be considered when analyzing any company that holds substantial non-controlling equity interests.**
