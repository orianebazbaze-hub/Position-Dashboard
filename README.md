# Portfolio Positioning Dashboard

> **Corporate Treasury | Desk Front Portfolio Management**  
> Real-time position tracking and portfolio risk dashboard for funding & investment desks.

![Python](https://img.shields.io/badge/Python-3.10+-blue) ![Flask](https://img.shields.io/badge/Flask-3.0-green) ![JavaScript](https://img.shields.io/badge/JavaScript-ES2022-yellow)

> **Fictitious portfolio for demonstration purposes only.** All positions (CD, CP, Money Market, XCCY, FX Swaps, Covered Bonds, Corporate Bonds) use simulated rates and market parameters. Not for trading.

---

## Use Case

A **Corporate Treasury funding desk** manages ~€736M across 7 asset classes and needs to:

✅ Track **15 positions** in real-time (CD, CP, Money Market, XCCY swaps, FX swaps, covered bonds, corporate bonds)  
✅ Monitor **mark-to-market P&L** per position  
✅ Measure **interest rate risk** (DV01), **FX exposure** (delta), **basis risk** (XCCY)  
✅ Allocate **funding costs** (FTP) by maturity and product  
✅ Plan **refinancing** (maturity ladder, rollover windows)  
✅ Run **stress scenarios** (rates ±200bp, FX ±5%, basis ±50bp)  

This dashboard delivers all of that **in one interface**.

---

## Architecture

```
┌──────────────────────────────────┐
│  Flask Backend (Python 3.10+)    │
├──────────────────────────────────┤
│ • OIS curve bootstrap             │
│ • Bond pricing (durations)        │
│ • Mark-to-market P&L              │
│ • DV01, FX Delta, Basis Duration  │
│ • FTP cost allocation             │
│ • Implied USD rates (FXSW)        │
│ • Stress scenarios (3D shifts)    │
└──────────────────────────────────┘
              ↕
         REST API (7 routes)
              ↕
┌──────────────────────────────────┐
│ JavaScript Frontend (HTML/CSS)   │
├──────────────────────────────────┤
│ • 6 interactive views             │
│ • Real-time metrics & tables      │
│ • Stress scenario builder         │
│ • Refinancing calendar            │
│ • Dark theme, responsive          │
└──────────────────────────────────┘
```

---

## Instruments

| Type | Example | Notional | Rate | Maturity | Use |
|---|---|---|---|---|---|
| **CD** | BNP CD 3M | €50M | 3.65% | 90d | Interbank wholesale, AAA |
| **CP** | CP 30D | €100M | 3.30% | 30d | Shortest tenor, lowest cost |
| **MM** | IBOR Deposit 1M | €80M | 3.45% | 14d | Spot-forward, AA-rated |
| **XCCY** | EUR Pay / USD Rcv 2Y | €120M | 2.70% (EUR) | 2Y | Synthetic funding, basis –25bp |
| **FXSW** | EUR/USD 1W | €150M | 3.75% (implied USD) | 7d | Rolling, short-dated |
| **SEC** | CRH Covered Bond 3Y | €60M | 3.20% | 3Y | AAA, duration 2.8Y |
| **UNS** | BNP Unsecured 2Y | €80M | 3.50% | 2Y | Corporate A-rated |

---

## Dashboard Views

### 1. **Positions** — Full Inventory
- All 15 positions with notional, currency, coupon, maturity, rating
- Quick status check: amount, position count, total MTM P&L

### 2. **Mark-to-Market** — P&L Breakdown
- Realized & unrealized P&L per position
- Price changes, percentage returns
- Sorted by loss (largest losers first)

### 3. **Risks** — Exposure Dashboard
- **DV01** (€K): interest rate sensitivity per 1bp parallel shift
  - Duration-based for bonds, tenor-based for XCCY
- **FX Delta** (€M): USD equivalents of foreign notional
  - EURUSD, GBPUSD exposures
- **Basis Duration** (€/bp): XCCY basis spread risk
  - Only for XCCY positions

### 4. **Funding Cost & FTP**
- **Cost Rate by instrument type**: CD 3.60%, CP 3.30%, MM 3.40%, XCCY 2.70%, SEC 3.10%, UNS 3.80%
- **FTP Allocation**: per-position funding cost, maturity-weighted
- **Portfolio-level blended cost**: 3.50% p.a.

### 5. **Refinancing Calendar**
- Maturity waterfall: what matures when
- €130M due in 3d, €280M in 30d, €120M in 61d, etc.
- Identify rollover peaks and concentration risk

### 6. **Stress Scenarios** — Interactive Builder
- **Rates slider**: ±200bp parallel shift → DV01 impact
- **FX slider**: ±5% currency move → delta impact
- **Basis slider**: ±50bp XCCY basis shock
- **Results**: total portfolio impact + per-position breakout

---

## Quickstart

```bash
# Install dependencies
pip install -r requirements.txt

# Run server
python app.py

# Open browser
# → http://localhost:5002
```

Dashboard loads with **15 demo positions** (€736M notional).

---

## API Reference

All routes return JSON. No authentication required for demo.

### GET /api/positions
Returns all positions with notional, rate, maturity, P&L.

```bash
curl http://localhost:5002/api/positions
```

### GET /api/risks
Returns DV01, FX Delta, Basis Duration per position.

```bash
curl http://localhost:5002/api/risks
```

### GET /api/funding
Returns funding cost allocation by position.

```bash
curl http://localhost:5002/api/funding
```

### GET /api/calendar
Returns refinancing calendar (maturity dates + amounts).

```bash
curl http://localhost:5002/api/calendar
```

### GET /api/stress
Returns stress scenario impact (rates + FX + basis).

```bash
curl "http://localhost:5002/api/stress?rate=100&fx=0&basis=0"
```

Parameters:
- `rate`: rate shift in bp (default: 100, range: -200 to +200)
- `fx`: FX move in % (default: 0, range: -5 to +5)
- `basis`: basis shift in bp (default: 0, range: -50 to +50)

---

## Key Metrics Explained

### Risk Metrics

**DV01** (Dollar Value of 1bp)
- Measures P&L impact of 1bp parallel rate shift
- Formula: `DV01 = Position Size × Duration / 10,000`
- Example: €50M CD with 0.25Y duration → DV01 = €1,250
- **Total: €485K** → 1bp rate move = €485K loss

**FX Delta**
- Notional exposure in foreign currency (USD equivalents)
- Includes: FXSW notional + XCCY notional + foreign bonds
- **Total: €226.9M USD** → 1% EUR depreciation = ~€226.9M mark loss

**Basis Duration**
- XCCY basis spread sensitivity (€/bp)
- Formula: `Basis Duration = Notional × Tenor / 10,000`
- Example: €120M XCCY 2Y → Basis Duration = €24M per bp
- **Total: 200€/bp** → –25bp basis move = –€5M loss

### Funding Metrics

**Cost Rate (%)**
- Annual funding cost for each instrument type
- CD: 3.60% (interbank cost)
- CP: 3.30% (short-term, cheaper)
- XCCY: 2.70% (synthetic funding advantage)
- UNS: 3.80% (unsecured, more expensive)

**Weighted Cost (%)**
- Portfolio-level blended funding cost
- `Weighted Cost = Σ(Amount × Cost Rate) / Total Amount`
- **Current: 3.50% p.a.**

---

## Technical Stack

**Backend:** Python 3.10+ + Flask + NumPy + SciPy  
**Frontend:** Vanilla JavaScript + HTML/CSS (dark theme)  
**Pricing:** OIS curve (cubic spline), bond duration, FX parity  
**Performance:** All calculations < 100ms  

---

## Files

```
portfolio_dashboard/
├── app.py                  # Flask backend (462 lines)
├── templates/
│   └── index.html         # Frontend (376 lines, dark theme)
├── requirements.txt        # Dependencies
└── README.md              # This file
```

---

## Regulatory References

- **BASEL III** — Interest Rate Risk in Banking Book (IRRBB), Liquidity Coverage Ratio (LCR)
- **EBA GL 2022/14** — IRRBB and CSRBB stress testing requirements
- **ICMA Guidelines** — Repo Risk Management
- **ECB/ESCB** — XCCY basis monitoring, FX swap pricing

---

## Limitations & Notes

⚠️ **Portfolio is fictitious** — rates, notionals, curves are simulated  
⚠️ **Simplified models** — real systems use key rate durations, non-linear FTP, multi-factor stress  
⚠️ **Parallel shifts only** — stress doesn't model yield curve twists  
⚠️ **No market data feeds** — all rates hard-coded (for demo)  

---

## Next Steps

- **Connect to live market data** (Bloomberg, Reuters, ECB APIs)
- **Key Rate Durations** instead of parallel shift
- **Multi-currency portfolio aggregation** (consolidate to USD)
- **Historical P&L attribution** (analytics dashboard)
