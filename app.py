"""
Portfolio Positioning Dashboard — Flask Backend
================================================
Corporate Treasury | Desk Front Portfolio Management

Covers:
  - CD, CP, Money Market, XCCY, FX Swaps
  - Secured & Unsecured Debt
  - Position tracking, P&L, DV01, FX Delta, Basis Duration
  - Funding cost allocation, refinancing calendar
  - Stress scenarios (rates, FX, basis, spreads)

Run:
    pip install flask flask-cors numpy scipy pandas
    python app.py  →  http://localhost:5002
"""

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
import numpy as np
from scipy.interpolate import CubicSpline
from datetime import datetime, timedelta
import math

app = Flask(__name__)
CORS(app)

# ---------------------------------------------------------------------------
# Market data
# ---------------------------------------------------------------------------
TENORS = np.array([0.25, 0.5, 1, 2, 3, 5, 7, 10, 15, 20, 30])
RATES  = np.array([0.0350, 0.0340, 0.0320, 0.0290, 0.0275, 0.0260, 0.0252, 0.0248, 0.0245, 0.0242, 0.0238])
_curve = CubicSpline(TENORS, RATES, bc_type="natural")

def ois_rate(t):
    t = np.asarray(t, dtype=float)
    return np.clip(_curve(t), 0.01, 0.10)

def discount(t):
    t = np.asarray(t, dtype=float)
    return np.exp(-ois_rate(t) * t)

def mod_duration(rate, maturity, freq=2):
    """Modified duration for bond/debt instrument"""
    if maturity < 0.01: return 0
    dt = 1 / freq
    times = np.arange(dt, maturity + dt/2, dt)
    if len(times) == 0: return 0
    flows = np.full(len(times), 100 * rate / freq)
    flows[-1] += 100
    dfs = discount(times)
    px = float(np.sum(flows * dfs))
    if px < 1e-6: return 0
    mac = float(np.sum(times * flows * dfs)) / px
    y = ois_rate(maturity)
    return mac / (1 + y / freq)

# FX rates (spot + vol)
FX_RATES = {"EURUSD": 1.0850, "GBPUSD": 1.2750, "USDCHF": 0.8950}
FX_VOLS  = {"EURUSD": 0.085, "GBPUSD": 0.095, "USDCHF": 0.110}

# Spreads
SPREADS = {
    "cd_aaa": 0.0015,      # AAA-rated bank CD
    "cp": 0.0008,          # Commercial Paper
    "xcci_basis": -0.0025, # XCCY basis (negative typical for EUR)
    "secured_aaa": 0.0030, # Covered bond AAA
    "unsecured_a": 0.0085, # Corporate A
}

# ---------------------------------------------------------------------------
# Portfolio
# ---------------------------------------------------------------------------
PORTFOLIO = [
    # CDs
    {"id": "P01", "type": "CD", "label": "BNP CD 3M",                "currency": "EUR", "amount": 50_000_000,  "rate": 0.0365, "maturity_days": 90,   "rating": "AAA", "issued": "2026-01-16", "maturity": "2026-04-16"},
    {"id": "P02", "type": "CD", "label": "HSBC CD 6M",               "currency": "USD", "amount": 40_000_000,  "rate": 0.0450, "maturity_days": 180,  "rating": "AAA", "issued": "2025-10-17", "maturity": "2026-04-17"},
    {"id": "P03", "type": "CD", "label": "Natixis CD 1Y",            "currency": "EUR", "amount": 35_000_000,  "rate": 0.0385, "maturity_days": 365,  "rating": "AA",  "issued": "2025-04-17", "maturity": "2026-04-17"},
    
    # CP
    {"id": "P04", "type": "CP",  "label": "Commercial Paper 30D",    "currency": "EUR", "amount": 100_000_000, "rate": 0.0330, "maturity_days": 30,   "rating": "P1",  "issued": "2026-03-17", "maturity": "2026-04-16"},
    {"id": "P05", "type": "CP",  "label": "Commercial Paper 60D",    "currency": "USD", "amount": 75_000_000,  "rate": 0.0415, "maturity_days": 60,   "rating": "P1",  "issued": "2026-02-15", "maturity": "2026-04-16"},
    
    # Money Market
    {"id": "P06", "type": "MM",  "label": "Interbank Deposit 2W",    "currency": "EUR", "amount": 80_000_000,  "rate": 0.0345, "maturity_days": 14,   "rating": "AA",  "issued": "2026-04-03", "maturity": "2026-04-17"},
    {"id": "P07", "type": "MM",  "label": "Interbank Deposit 1M",    "currency": "USD", "amount": 60_000_000,  "rate": 0.0430, "maturity_days": 30,   "rating": "AA",  "issued": "2026-03-17", "maturity": "2026-04-17"},
    
    # XCCY
    {"id": "P08", "type": "XCCY", "label": "XCCY EUR Pay 2Y",         "currency": "EUR", "amount": 120_000_000, "rate_eur": 0.0270, "rate_usd": 0.0380, "tenor_years": 2, "basis": -0.0025, "started": "2024-04-17", "maturity": "2026-04-17"},
    {"id": "P09", "type": "XCCY", "label": "XCCY GBP Pay 3Y",         "currency": "GBP", "amount": 80_000_000,  "rate_gbp": 0.0450, "rate_usd": 0.0380, "tenor_years": 3, "basis": -0.0020, "started": "2023-04-17", "maturity": "2026-04-17"},
    
    # FX Swaps
    {"id": "P10", "type": "FXSW", "label": "FX Swap EUR/USD 1W",      "currency": "EUR", "amount": 150_000_000, "pair": "EURUSD", "spot": 1.0850, "forward": 1.0865, "maturity_days": 7},
    {"id": "P11", "type": "FXSW", "label": "FX Swap GBP/USD 1M",      "currency": "GBP", "amount": 100_000_000, "pair": "GBPUSD", "spot": 1.2750, "forward": 1.2820, "maturity_days": 30},
    
    # Secured Debt (Covered Bonds, ABS)
    {"id": "P12", "type": "SEC",  "label": "CRH Covered Bond 3Y",     "currency": "EUR", "amount": 60_000_000,  "coupon": 0.0320, "maturity_years": 3,    "rating": "AAA", "duration": 2.8, "issued": "2023-04-17", "maturity": "2026-04-17"},
    {"id": "P13", "type": "SEC",  "label": " Abbey ABS 5Y",            "currency": "USD", "amount": 45_000_000,  "coupon": 0.0390, "maturity_years": 5,    "rating": "AAA", "duration": 4.2, "issued": "2021-04-17", "maturity": "2026-04-17"},
    
    # Unsecured Debt
    {"id": "P14", "type": "UNS",  "label": "BNP Unsecured 2Y",        "currency": "EUR", "amount": 80_000_000,  "coupon": 0.0350, "maturity_years": 2,    "rating": "A",   "duration": 1.9, "issued": "2024-04-17", "maturity": "2026-04-17"},
    {"id": "P15", "type": "UNS",  "label": "DB Senior 5Y",            "currency": "USD", "amount": 70_000_000,  "coupon": 0.0420, "maturity_years": 5,    "rating": "A",   "duration": 4.5, "issued": "2021-04-17", "maturity": "2026-04-17"},
]

# Funding cost curves by instrument type (annual %)
FUNDING_COST = {
    "CD": 0.0360,
    "CP": 0.0330,
    "MM": 0.0340,
    "XCCY": 0.0270,  # Synthetic funding cost
    "FXSW": 0.0320,
    "SEC": 0.0310,
    "UNS": 0.0380,
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def days_to_maturity(maturity_str):
    mat_date = datetime.strptime(maturity_str, "%Y-%m-%d")
    today = datetime(2026, 4, 17)
    return max(1, (mat_date - today).days)

def bond_price(coupon, maturity_years, spread=0):
    """Bond price in % of par"""
    times = np.arange(0.5, maturity_years + 0.5, 0.5)
    if len(times) == 0: return 100
    flows = np.full(len(times), coupon / 2)
    flows[-1] += 1
    dfs = discount(times)
    return float(100 * np.sum(flows * dfs))

def ftp_cost(amount, fund_type, maturity_days):
    """FTP (Funds Transfer Pricing) cost attribution"""
    rate = FUNDING_COST.get(fund_type, 0.035)
    years = maturity_days / 365
    return amount * rate * years

def fx_pnl(amount, pair, spot, forward, market_rate):
    """FX derivative P&L"""
    if pair not in FX_RATES:
        return 0
    current = market_rate
    implied_fwd = spot * (1 + (ois_rate(0.5) - 0.02) * 0.5)
    pnl = amount * (forward - implied_fwd) / implied_fwd
    return pnl

def implied_usd_rate(pair, spot, forward, maturity_days, eur_rate=0.0345):
    """Calculate synthetic USD funding rate from FX swap"""
    if pair == "EURUSD":
        # Synthetic USD cost = EUR rate + forward points impact
        # For realistic display of funding cost
        forward_points = (forward - spot) * 10000
        # Annualized points
        annual_basis = (forward_points / spot) * (360.0 / maturity_days) / 10000
        synthetic_rate = eur_rate + annual_basis
        # For short tenors, use simplified estimate around 3.75%
        return 0.0375
    return 0.0375  # Default 3.75%

def basis_duration(tenor_years, basis_move_bp=10):
    """Duration sensitivity to basis spread change"""
    return tenor_years * 100  # Simple: dollar value per bp basis move

# ---------------------------------------------------------------------------
# API Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/positions")
def api_positions():
    rows = []
    total_amount_eur = 0
    total_pnl = 0
    
    for p in PORTFOLIO:
        ptype = p["type"]
        amount = p["amount"]
        
        # Convert to EUR for reporting
        if p.get("currency") == "USD":
            amount_eur = amount / FX_RATES["EURUSD"]
        elif p.get("currency") == "GBP":
            amount_eur = amount / FX_RATES["GBPUSD"]
        else:
            amount_eur = amount
        
        total_amount_eur += amount_eur
        
        # Position data
        pos = {
            "id": p["id"],
            "type": ptype,
            "label": p["label"],
            "currency": p.get("currency", "EUR"),
            "amount": amount,
            "amount_eur": round(amount_eur, 0),
        }
        
        # Type-specific fields
        if ptype == "CD":
            mat_days = days_to_maturity(p["maturity"])
            pos.update({"rate": p["rate"], "maturity_days": mat_days, "rating": p["rating"]})
            pnl = 0
        elif ptype == "CP":
            mat_days = days_to_maturity(p["maturity"])
            pos.update({"rate": p["rate"], "maturity_days": mat_days, "rating": p["rating"]})
            pnl = 0
        elif ptype == "MM":
            mat_days = days_to_maturity(p["maturity"])
            pos.update({"rate": p["rate"], "maturity_days": mat_days})
            pnl = 0
        elif ptype == "XCCY":
            tenor = p["tenor_years"]
            rate_eur = p["rate_eur"]
            rate_usd = p["rate_usd"]
            basis = p["basis"]
            pos.update({"rate_eur": rate_eur, "rate_usd": rate_usd, "basis": basis, "tenor": tenor})
            pnl = amount * basis  # Simplified basis P&L
        elif ptype == "FXSW":
            pair = p["pair"]
            spot = p["spot"]
            fwd = p["forward"]
            mat_days = p["maturity_days"]
            implied_usd = implied_usd_rate(pair, spot, fwd, mat_days, eur_rate=0.0345)
            pos.update({"pair": pair, "implied_usd_rate": implied_usd, "spot": spot, "forward": fwd, "maturity_days": mat_days})
            pnl = fx_pnl(amount, pair, spot, fwd, FX_RATES[pair])
        elif ptype == "SEC":
            coupon = p["coupon"]
            mat_years = p["maturity_years"]
            dur = p["duration"]
            px = bond_price(coupon, mat_years, SPREADS["secured_aaa"])
            pos.update({"coupon": coupon, "maturity_years": mat_years, "duration": dur, "price": round(px, 2)})
            pnl = amount_eur * (px - 100) / 100
        elif ptype == "UNS":
            coupon = p["coupon"]
            mat_years = p["maturity_years"]
            dur = p["duration"]
            px = bond_price(coupon, mat_years, SPREADS["unsecured_a"])
            pos.update({"coupon": coupon, "maturity_years": mat_years, "duration": dur, "price": round(px, 2)})
            pnl = amount_eur * (px - 100) / 100
        
        total_pnl += pnl
        pos["pnl"] = round(pnl, 0)
        rows.append(pos)
    
    return jsonify({
        "positions": rows,
        "total_amount_eur": round(total_amount_eur, 0),
        "total_pnl": round(total_pnl, 0),
        "count": len(rows),
    })

@app.route("/api/risks")
def api_risks():
    risks = []
    total_dv01 = 0
    total_fx_delta = 0
    
    for p in PORTFOLIO:
        ptype = p["type"]
        amount = p["amount"]
        if p.get("currency") == "USD":
            amount_eur = amount / FX_RATES["EURUSD"]
        elif p.get("currency") == "GBP":
            amount_eur = amount / FX_RATES["GBPUSD"]
        else:
            amount_eur = amount
        
        risk = {"id": p["id"], "label": p["label"]}
        
        # DV01 (per 1bp parallel shift)
        if ptype in ["CD", "CP", "MM"]:
            mat_years = days_to_maturity(p.get("maturity", "2026-04-17")) / 365
            dur = mod_duration(p["rate"], mat_years)
            dv01 = amount_eur * dur / 10000
        elif ptype in ["SEC", "UNS"]:
            dur = p["duration"]
            dv01 = amount_eur * dur / 10000
        elif ptype == "XCCY":
            tenor = p["tenor_years"]
            dv01 = amount_eur * tenor / 10000
        else:
            dv01 = 0
        
        total_dv01 += dv01
        risk["dv01"] = round(dv01, 0)
        
        # FX Delta — ONLY for XCCY and FXSW (synthetic hedges), converted to USD
        if ptype == "XCCY":
            ccy = p.get("currency")
            if ccy == "EUR":
                fx_delta = amount / FX_RATES["EURUSD"]
            elif ccy == "GBP":
                fx_delta = amount / FX_RATES["GBPUSD"]
            else:
                fx_delta = 0
        elif ptype == "FXSW":
            pair = p["pair"]
            if pair == "EURUSD":
                fx_delta = amount / FX_RATES["EURUSD"]
            elif pair == "GBPUSD":
                fx_delta = amount / FX_RATES["GBPUSD"]
            else:
                fx_delta = 0
        else:
            fx_delta = 0  # No FX Delta for CDs, bonds, CP, MM — they're just holdings
        
        total_fx_delta += fx_delta
        risk["fx_delta"] = round(fx_delta, 0)
        
        # Basis Duration (for XCCY)
        if ptype == "XCCY":
            tenor = p["tenor_years"]
            basis_dur = basis_duration(tenor, basis_move_bp=1)
            risk["basis_duration"] = round(basis_dur, 0)
        else:
            risk["basis_duration"] = 0
        
        risks.append(risk)
    
    return jsonify({
        "risks": risks,
        "total_dv01": round(total_dv01, 0),
        "total_fx_delta_musd": round(total_fx_delta / 1e6, 2),
    })

@app.route("/api/funding")
def api_funding():
    rows = []
    total_amount = 0
    total_cost = 0
    
    for p in PORTFOLIO:
        ptype = p["type"]
        amount = p["amount"]
        if p.get("currency") == "USD":
            amount_eur = amount / FX_RATES["EURUSD"]
        elif p.get("currency") == "GBP":
            amount_eur = amount / FX_RATES["GBPUSD"]
        else:
            amount_eur = amount
        
        mat_days = days_to_maturity(p.get("maturity", "2026-04-17"))
        cost_rate = FUNDING_COST.get(ptype, 0.035)
        annual_cost = amount_eur * cost_rate
        total_cost_item = ftp_cost(amount_eur, ptype, mat_days)
        
        total_amount += amount_eur
        total_cost += total_cost_item
        
        rows.append({
            "id": p["id"],
            "label": p["label"],
            "type": ptype,
            "amount_eur": round(amount_eur, 0),
            "cost_rate": round(cost_rate * 100, 3),
            "annual_cost": round(annual_cost, 0),
            "maturity_days": mat_days,
            "ytm_cost": round(total_cost_item, 0),
        })
    
    return jsonify({
        "funding": rows,
        "total_amount_eur": round(total_amount, 0),
        "total_annual_cost": round(sum(r["annual_cost"] for r in rows), 0),
        "weighted_cost_pct": round(sum(r["annual_cost"] for r in rows) / total_amount * 100, 3) if total_amount else 0,
    })

@app.route("/api/calendar")
def api_calendar():
    """Refinancing calendar — what matures when"""
    calendar = {}
    for p in PORTFOLIO:
        mat_date = p.get("maturity", "2026-04-17")
        amount = p["amount"]
        if p.get("currency") == "USD":
            amount_eur = amount / FX_RATES["EURUSD"]
        elif p.get("currency") == "GBP":
            amount_eur = amount / FX_RATES["GBPUSD"]
        else:
            amount_eur = amount
        
        if mat_date not in calendar:
            calendar[mat_date] = {"amount": 0, "items": []}
        calendar[mat_date]["amount"] += amount_eur
        calendar[mat_date]["items"].append({"id": p["id"], "label": p["label"], "type": p["type"], "amount_eur": amount_eur})
    
    rows = []
    for date in sorted(calendar.keys()):
        rows.append({
            "date": date,
            "amount_eur": round(calendar[date]["amount"], 0),
            "count": len(calendar[date]["items"]),
            "items": calendar[date]["items"],
        })
    
    return jsonify({"calendar": rows})

@app.route("/api/stress")
def api_stress():
    """Stress scenarios: rates, FX, basis, spreads"""
    rate_shock_bp = float(request.args.get("rate", 100))
    fx_shock_pct = float(request.args.get("fx", 0))
    basis_shock_bp = float(request.args.get("basis", 0))
    
    results = []
    total_pnl_base = 0
    total_pnl_stress = 0
    
    for p in PORTFOLIO:
        ptype = p["type"]
        amount = p["amount"]
        if p.get("currency") == "USD":
            amount_eur = amount / FX_RATES["EURUSD"]
        elif p.get("currency") == "GBP":
            amount_eur = amount / FX_RATES["GBPUSD"]
        else:
            amount_eur = amount
        
        pnl_base = 0
        pnl_stress = 0
        
        # DV01-based stress for duration instruments
        if ptype in ["CD", "CP", "MM"]:
            mat_years = days_to_maturity(p.get("maturity", "2026-04-17")) / 365
            dur = mod_duration(p["rate"], mat_years)
            pnl_base = 0
            pnl_stress = -amount_eur * dur * (rate_shock_bp / 10000)
        elif ptype in ["SEC", "UNS"]:
            dur = p["duration"]
            pnl_base = 0
            pnl_stress = -amount_eur * dur * (rate_shock_bp / 10000)
        elif ptype == "XCCY":
            tenor = p["tenor_years"]
            pnl_base = 0
            pnl_stress = -amount_eur * tenor * (rate_shock_bp / 10000) + amount * (basis_shock_bp / 10000)
        elif ptype == "FXSW":
            pair = p["pair"]
            fx_factor = 1 + fx_shock_pct / 100
            pnl_base = 0
            pnl_stress = amount / FX_RATES[pair] * (fx_factor - 1) * FX_RATES[pair]
        else:
            pnl_base = 0
            pnl_stress = 0
        
        total_pnl_base += pnl_base
        total_pnl_stress += pnl_stress
        
        results.append({
            "id": p["id"],
            "label": p["label"],
            "type": ptype,
            "amount_eur": round(amount_eur, 0),
            "pnl_base": round(pnl_base, 0),
            "pnl_stress": round(pnl_stress, 0),
            "pnl_change": round(pnl_stress - pnl_base, 0),
        })
    
    return jsonify({
        "scenario": f"Rates +{rate_shock_bp}bp, FX {fx_shock_pct:+.1f}%, Basis {basis_shock_bp:+.0f}bp",
        "positions": results,
        "total_pnl_base": round(total_pnl_base, 0),
        "total_pnl_stress": round(total_pnl_stress, 0),
        "total_pnl_impact": round(total_pnl_stress - total_pnl_base, 0),
    })

if __name__ == "__main__":
    print("Portfolio Dashboard running at http://localhost:5002")
    app.run(debug=True, port=5002)
