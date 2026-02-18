#!/usr/bin/env python3
"""
CSP (Cash-Secured Put) Screener v2.2
Screens for optimal cash-secured put, put credit spread, and broken wing butterfly opportunities.
Full Greeks, fundamental filtering, AI/tech focus, and quality scoring.
"""

import argparse
import sys
import warnings
from datetime import datetime, timedelta

import numpy as np
import yfinance as yf
from scipy.stats import norm
from tabulate import tabulate

warnings.filterwarnings("ignore")

# ── Watchlists ────────────────────────────────────────────────────────────────

DEFAULT_TICKERS = [
    "SPY", "QQQ", "AAPL", "MSFT", "AMZN", "GOOGL", "NVDA", "AMD",
    "META", "TSLA", "KO", "PEP", "JNJ", "JPM", "BAC"
]

AI_TECH_TICKERS = [
    # AI Chips & Semiconductors
    "NVDA", "AMD", "TSM", "AVGO", "MRVL", "ARM", "MU", "INTC", "QCOM", "SMCI",
    # AI Software & Cloud
    "MSFT", "GOOGL", "META", "AMZN", "PLTR", "CRM", "SNOW", "AI", "ORCL", "NOW",
    # Datacenter Infrastructure
    "EQIX", "DLR", "VRT", "ANET",
    # High-vol AI plays
    "TSLA",
    # Cybersecurity
    "CRWD", "ZS",
    # Growth / Coach Mak picks
    "RKLB", "NBIS", "GTLB", "UBER",
]

# Coach Mak's income strategy tickers (high-premium, liquid AI/mega-cap)
INCOME_TICKERS = [
    "NVDA", "AMZN", "TSLA", "GOOGL", "AMD", "META",
    "MSFT", "AAPL", "AVGO", "MU", "SMCI", "PLTR",
]

# ── Black-Scholes Greeks ─────────────────────────────────────────────────────

def bs_d1_d2(S, K, T, r, sigma):
    """Return (d1, d2) for Black-Scholes."""
    if T <= 0 or sigma <= 0:
        return None, None
    sqrt_T = np.sqrt(T)
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * sqrt_T)
    d2 = d1 - sigma * sqrt_T
    return d1, d2


def bs_put_greeks(S, K, T, r, sigma):
    """
    Calculate ALL Greeks for a European put via Black-Scholes.
    Returns dict with delta, gamma, theta, vega, rho.
    Theta is returned in $/day per contract (×100 shares).
    """
    d1, d2 = bs_d1_d2(S, K, T, r, sigma)
    if d1 is None:
        return {"delta": 0, "gamma": 0, "theta": 0, "vega": 0, "rho": 0}

    sqrt_T = np.sqrt(T)
    n_d1 = norm.pdf(d1)       # standard normal PDF at d1
    N_neg_d1 = norm.cdf(-d1)  # CDF at -d1
    N_neg_d2 = norm.cdf(-d2)  # CDF at -d2

    # Delta (put): N(d1) - 1 = -N(-d1)
    delta = -N_neg_d1

    # Gamma (same for put and call): n(d1) / (S * sigma * sqrt(T))
    gamma = n_d1 / (S * sigma * sqrt_T) if (S * sigma * sqrt_T) > 0 else 0

    # Theta (put): per-year value, then convert to $/day per contract
    # θ = -[S·n(d1)·σ / (2√T)] + r·K·e^(-rT)·N(-d2)
    theta_annual = (
        -(S * n_d1 * sigma) / (2 * sqrt_T)
        + r * K * np.exp(-r * T) * N_neg_d2
    )
    theta_per_day = theta_annual / 365.0  # per-share per-day
    theta_contract = theta_per_day * 100   # per-contract (100 shares)

    # Vega: S·n(d1)·√T  (per 1.0 change in sigma; we report per 1% = /100)
    vega_raw = S * n_d1 * sqrt_T
    vega_pct = vega_raw / 100.0  # $ change per 1% IV move, per share

    # Rho (put): -K·T·e^(-rT)·N(-d2) / 100 (per 1% rate change)
    rho = -K * T * np.exp(-r * T) * N_neg_d2 / 100.0

    return {
        "delta": round(delta, 4),
        "gamma": round(gamma, 6),
        "theta": round(theta_contract, 2),   # $/day per contract
        "vega": round(vega_pct, 4),           # $/share per 1% IV
        "rho": round(rho, 4),
    }


# ── IV Rank estimation ───────────────────────────────────────────────────────

def estimate_iv_rank(ticker_obj):
    """
    Estimate IV Rank by comparing current implied vol to 52-week range
    of historical realized volatility as a proxy.
    """
    try:
        hist = ticker_obj.history(period="1y")
        if hist.empty or len(hist) < 30:
            return None
        returns = np.log(hist["Close"] / hist["Close"].shift(1)).dropna()
        if len(returns) < 30:
            return None
        rolling_vol = returns.rolling(window=30).std() * np.sqrt(252)
        rolling_vol = rolling_vol.dropna()
        if len(rolling_vol) < 10:
            return None
        current_vol = rolling_vol.iloc[-1]
        vol_min = rolling_vol.min()
        vol_max = rolling_vol.max()
        if vol_max == vol_min:
            return 50.0
        iv_rank = ((current_vol - vol_min) / (vol_max - vol_min)) * 100
        return round(max(0, min(100, iv_rank)), 1)
    except Exception:
        return None


# ── Earnings date ─────────────────────────────────────────────────────────────

def get_earnings_date(ticker_obj):
    """Get next earnings date if available."""
    try:
        cal = ticker_obj.calendar
        if cal is not None:
            if isinstance(cal, dict) and "Earnings Date" in cal:
                dates = cal["Earnings Date"]
                if dates:
                    return dates[0] if isinstance(dates, list) else dates
            elif hasattr(cal, "loc"):
                if "Earnings Date" in cal.index:
                    return cal.loc["Earnings Date"].iloc[0]
        return None
    except Exception:
        return None


# ── Fundamentals ──────────────────────────────────────────────────────────────

def get_fundamentals(ticker_obj, ticker_symbol):
    """
    Fetch fundamental data for quality screening.
    Returns dict of metrics or None on failure.
    """
    try:
        info = ticker_obj.info or {}

        market_cap = info.get("marketCap")
        pe_ratio = info.get("trailingPE") or info.get("forwardPE")
        gross_margin = info.get("grossMargins")     # decimal (0.55 = 55%)
        op_margin = info.get("operatingMargins")
        net_margin = info.get("profitMargins")
        fcf = info.get("freeCashflow")
        revenue = info.get("totalRevenue")
        revenue_growth = info.get("revenueGrowth")  # decimal YoY
        sector = info.get("sector", "")

        # FCF yield = FCF / Market Cap
        fcf_yield = None
        if fcf and market_cap and market_cap > 0:
            fcf_yield = (fcf / market_cap) * 100  # as percentage

        return {
            "ticker": ticker_symbol,
            "market_cap": market_cap,
            "pe_ratio": round(pe_ratio, 1) if pe_ratio else None,
            "gross_margin": round(gross_margin * 100, 1) if gross_margin else None,
            "op_margin": round(op_margin * 100, 1) if op_margin else None,
            "net_margin": round(net_margin * 100, 1) if net_margin else None,
            "fcf": fcf,
            "fcf_yield": round(fcf_yield, 2) if fcf_yield else None,
            "revenue": revenue,
            "revenue_growth": round(revenue_growth * 100, 1) if revenue_growth else None,
            "sector": sector,
        }
    except Exception as e:
        print(f"  ⚠️  Fundamentals error for {ticker_symbol}: {e}", file=sys.stderr)
        return None


def format_large_num(n):
    """Format large numbers for display (1.5T, 230B, 4.2M)."""
    if n is None:
        return "N/A"
    abs_n = abs(n)
    sign = "-" if n < 0 else ""
    if abs_n >= 1e12:
        return f"{sign}${abs_n/1e12:.1f}T"
    elif abs_n >= 1e9:
        return f"{sign}${abs_n/1e9:.1f}B"
    elif abs_n >= 1e6:
        return f"{sign}${abs_n/1e6:.1f}M"
    else:
        return f"{sign}${abs_n:,.0f}"


def compute_quality_score(fund):
    """
    Compute a 0-100 quality score from fundamentals.
    Higher = better company quality.
    """
    if fund is None:
        return 50  # neutral default

    score = 50  # start neutral

    # Gross margin: >60% excellent, >40% good, <20% poor
    gm = fund.get("gross_margin")
    if gm is not None:
        if gm >= 60:
            score += 12
        elif gm >= 40:
            score += 6
        elif gm < 20:
            score -= 8

    # Operating margin: >25% excellent, >15% good, <0% bad
    om = fund.get("op_margin")
    if om is not None:
        if om >= 25:
            score += 10
        elif om >= 15:
            score += 5
        elif om < 0:
            score -= 10

    # FCF yield: >5% great, >2% good, negative bad
    fy = fund.get("fcf_yield")
    if fy is not None:
        if fy >= 5:
            score += 10
        elif fy >= 2:
            score += 5
        elif fy < 0:
            score -= 8

    # Revenue growth: >20% strong, >10% good, <0% shrinking
    rg = fund.get("revenue_growth")
    if rg is not None:
        if rg >= 20:
            score += 10
        elif rg >= 10:
            score += 5
        elif rg < 0:
            score -= 8

    # P/E: reasonable range preferred
    pe = fund.get("pe_ratio")
    if pe is not None:
        if 0 < pe <= 25:
            score += 8
        elif 25 < pe <= 50:
            score += 2
        elif pe > 100 or pe < 0:
            score -= 5

    return max(0, min(100, score))


# ── Main screening ────────────────────────────────────────────────────────────

def screen_ticker(ticker_symbol, args, risk_free_rate=0.045, fundamentals_cache=None):
    """Screen a single ticker for CSP opportunities."""
    results = []

    try:
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info or {}

        # Get current price
        price = info.get("regularMarketPrice") or info.get("currentPrice")
        if not price:
            hist = ticker.history(period="5d")
            if hist.empty:
                return results, None
            price = hist["Close"].iloc[-1]

        # Fundamentals (fetch once per ticker)
        fund = None
        if fundamentals_cache is not None and ticker_symbol in fundamentals_cache:
            fund = fundamentals_cache[ticker_symbol]
        else:
            fund = get_fundamentals(ticker, ticker_symbol)
            if fundamentals_cache is not None:
                fundamentals_cache[ticker_symbol] = fund

        # Apply fundamental filters
        if fund:
            if args.min_margin is not None:
                gm = fund.get("gross_margin")
                if gm is not None and gm < args.min_margin:
                    return results, fund
            if args.min_fcf_yield is not None:
                fy = fund.get("fcf_yield")
                if fy is not None and fy < args.min_fcf_yield:
                    return results, fund
            if args.min_revenue_growth is not None:
                rg = fund.get("revenue_growth")
                if rg is not None and rg < args.min_revenue_growth:
                    return results, fund

        quality_score = compute_quality_score(fund)

        # IV Rank
        iv_rank = estimate_iv_rank(ticker)

        # Earnings date
        earnings_date = get_earnings_date(ticker)

        # Option expirations
        try:
            expirations = ticker.options
        except Exception:
            return results, fund
        if not expirations:
            return results, fund

        today = datetime.now().date()

        for exp_str in expirations:
            exp_date = datetime.strptime(exp_str, "%Y-%m-%d").date()
            dte = (exp_date - today).days
            if dte < args.min_dte or dte > args.max_dte:
                continue
            T = dte / 365.0

            # Earnings risk
            earnings_before_exp = False
            if earnings_date:
                try:
                    ed = earnings_date.date() if hasattr(earnings_date, "date") else earnings_date
                    earnings_before_exp = today <= ed <= exp_date
                except Exception:
                    pass

            try:
                chain = ticker.option_chain(exp_str)
                puts = chain.puts
            except Exception:
                continue
            if puts.empty:
                continue

            for _, row in puts.iterrows():
                strike = row.get("strike", 0)
                bid = row.get("bid", 0)
                ask = row.get("ask", 0)
                volume = row.get("volume", 0) or 0
                open_interest = row.get("openInterest", 0) or 0
                implied_vol = row.get("impliedVolatility", 0) or 0

                # Skip ITM puts
                if strike >= price:
                    continue
                if bid <= 0:
                    continue

                mid = (bid + ask) / 2
                spread = ask - bid
                if mid > 0 and (spread / mid) > 0.15:
                    continue

                sigma = implied_vol if implied_vol > 0 else 0.3

                # ── Full Greeks ──
                greeks = bs_put_greeks(price, strike, T, risk_free_rate, sigma)
                delta = greeks["delta"]

                abs_delta = abs(delta)
                if abs_delta < args.min_delta or abs_delta > args.max_delta:
                    continue

                # Returns
                premium = mid
                capital_required = strike * 100
                premium_total = premium * 100
                monthly_return = (premium / strike) * (30 / dte) * 100 if dte > 0 else 0

                if monthly_return < args.min_return:
                    continue

                otm_pct = ((price - strike) / price) * 100

                # ── Enhanced composite score ──
                ivr_score = (iv_rank / 100) if iv_rank else 0.5

                # Theta contribution: higher daily decay = more income (good)
                theta_score = min(abs(greeks["theta"]) / 10.0, 5.0)  # cap at 5

                # Gamma penalty: high gamma = delta moves fast = assignment risk
                gamma_penalty = min(greeks["gamma"] * 10000, 5.0)  # cap at 5

                # Quality from fundamentals (0-100 scaled to 0-10)
                qual_contribution = (quality_score / 100) * 10

                score = (
                    monthly_return * 0.40          # return is king
                    + ivr_score * 15               # high IV rank = better premiums
                    + otm_pct * 0.25               # safety cushion
                    + theta_score * 1.5            # theta decay income
                    + qual_contribution * 0.8      # fundamental quality
                    - gamma_penalty * 0.5          # assignment risk
                )

                results.append({
                    "ticker": ticker_symbol,
                    "price": round(price, 2),
                    "strike": strike,
                    "exp": exp_str,
                    "dte": dte,
                    "bid": bid,
                    "ask": ask,
                    "mid": round(mid, 2),
                    "delta": round(delta, 3),
                    "gamma": round(greeks["gamma"], 5),
                    "theta": round(greeks["theta"], 2),
                    "vega": round(greeks["vega"], 3),
                    "rho": round(greeks["rho"], 4),
                    "iv": round(implied_vol * 100, 1),
                    "iv_rank": iv_rank,
                    "otm_pct": round(otm_pct, 1),
                    "monthly_ret": round(monthly_return, 2),
                    "capital": round(capital_required, 0),
                    "premium": round(premium_total, 0),
                    "volume": int(volume),
                    "oi": int(open_interest),
                    "earnings": "⚠️" if earnings_before_exp else "",
                    "quality": quality_score,
                    "score": round(score, 2),
                })

    except Exception as e:
        print(f"  ⚠️  Error processing {ticker_symbol}: {e}", file=sys.stderr)

    return results, fund if 'fund' in dir() else (results, None)


# ── Credit Spread Screening ──────────────────────────────────────────────────

def screen_spread(ticker_symbol, args, risk_free_rate=0.045, fundamentals_cache=None):
    """
    Screen a single ticker for put credit spread opportunities.
    
    Put Credit Spread = Sell OTM put + Buy further OTM put
    - Defined risk: max loss = spread width - net credit
    - Requires less capital than CSP
    """
    results = []

    try:
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info or {}

        # Get current price
        price = info.get("regularMarketPrice") or info.get("currentPrice")
        if not price:
            hist = ticker.history(period="5d")
            if hist.empty:
                return results, None
            price = hist["Close"].iloc[-1]

        # Fundamentals (fetch once per ticker)
        fund = None
        if fundamentals_cache is not None and ticker_symbol in fundamentals_cache:
            fund = fundamentals_cache[ticker_symbol]
        else:
            fund = get_fundamentals(ticker, ticker_symbol)
            if fundamentals_cache is not None:
                fundamentals_cache[ticker_symbol] = fund

        # Apply fundamental filters (same as CSP)
        if fund:
            if args.min_margin is not None:
                gm = fund.get("gross_margin")
                if gm is not None and gm < args.min_margin:
                    return results, fund
            if args.min_fcf_yield is not None:
                fy = fund.get("fcf_yield")
                if fy is not None and fy < args.min_fcf_yield:
                    return results, fund
            if args.min_revenue_growth is not None:
                rg = fund.get("revenue_growth")
                if rg is not None and rg < args.min_revenue_growth:
                    return results, fund

        quality_score = compute_quality_score(fund)
        iv_rank = estimate_iv_rank(ticker)
        earnings_date = get_earnings_date(ticker)

        # Option expirations
        try:
            expirations = ticker.options
        except Exception:
            return results, fund
        if not expirations:
            return results, fund

        today = datetime.now().date()

        for exp_str in expirations:
            exp_date = datetime.strptime(exp_str, "%Y-%m-%d").date()
            dte = (exp_date - today).days
            if dte < args.min_dte or dte > args.max_dte:
                continue
            T = dte / 365.0

            # Earnings risk
            earnings_before_exp = False
            if earnings_date:
                try:
                    ed = earnings_date.date() if hasattr(earnings_date, "date") else earnings_date
                    earnings_before_exp = today <= ed <= exp_date
                except Exception:
                    pass

            try:
                chain = ticker.option_chain(exp_str)
                puts = chain.puts
            except Exception:
                continue
            if puts.empty:
                continue

            # Sort by strike descending for easier pairing
            puts_sorted = puts.sort_values("strike", ascending=False)
            
            # Find short leg candidates (OTM puts in delta range)
            for _, short_row in puts_sorted.iterrows():
                short_strike = short_row.get("strike", 0)
                short_bid = short_row.get("bid", 0) or 0
                short_ask = short_row.get("ask", 0) or 0
                short_last = short_row.get("lastPrice", 0) or 0
                short_iv = short_row.get("impliedVolatility", 0) or 0
                short_volume = short_row.get("volume", 0) or 0
                short_oi = short_row.get("openInterest", 0) or 0

                # Skip ITM puts
                if short_strike >= price:
                    continue
                
                # Use lastPrice as fallback if bid is 0 (market closed)
                if short_bid <= 0:
                    if short_last > 0:
                        short_bid = short_last * 0.95  # Conservative estimate
                        short_ask = short_last * 1.05
                    else:
                        continue

                short_mid = (short_bid + short_ask) / 2
                short_spread = short_ask - short_bid
                if short_mid > 0 and (short_spread / short_mid) > 0.20:
                    continue

                # IV sanity check: if IV is unrealistically low, estimate from price
                # Typical IV should be at least 15-20% for most stocks
                sigma = short_iv if short_iv >= 0.15 else 0.35  # Default 35% if IV seems wrong
                greeks = bs_put_greeks(price, short_strike, T, risk_free_rate, sigma)
                short_delta = greeks["delta"]

                abs_delta = abs(short_delta)
                if abs_delta < args.min_delta or abs_delta > args.max_delta:
                    continue

                # Find long leg candidates (5-10% below short strike, or next available)
                target_long_strike_min = short_strike * 0.90  # 10% below
                target_long_strike_max = short_strike * 0.95  # 5% below
                
                # Get all puts below short strike
                long_candidates = puts_sorted[puts_sorted["strike"] < short_strike]
                
                if long_candidates.empty:
                    continue

                # Find best long leg in target range, or nearest strike below
                best_long = None
                best_long_ask = 0
                for _, long_row in long_candidates.iterrows():
                    long_strike_candidate = long_row.get("strike", 0)
                    long_bid_candidate = long_row.get("bid", 0) or 0
                    long_ask_candidate = long_row.get("ask", 0) or 0
                    long_last_candidate = long_row.get("lastPrice", 0) or 0
                    
                    # Use lastPrice as fallback if ask is 0 (market closed)
                    if long_ask_candidate <= 0:
                        if long_last_candidate > 0:
                            long_bid_candidate = long_last_candidate * 0.95
                            long_ask_candidate = long_last_candidate * 1.05
                        else:
                            continue
                    
                    # Prefer strikes in the 5-10% range
                    if target_long_strike_min <= long_strike_candidate <= target_long_strike_max:
                        best_long = long_row
                        best_long_ask = long_ask_candidate
                        break
                    
                    # Otherwise take first valid strike below
                    if best_long is None and long_strike_candidate < short_strike:
                        best_long = long_row
                        best_long_ask = long_ask_candidate
                        # Keep looking for better match in range
                        if long_strike_candidate < target_long_strike_min:
                            break

                if best_long is None:
                    continue

                long_strike = best_long.get("strike", 0)
                long_bid = best_long.get("bid", 0) or 0
                long_ask = best_long.get("ask", 0) or 0
                long_last = best_long.get("lastPrice", 0) or 0
                long_iv = best_long.get("impliedVolatility", 0) or 0
                
                # Use fallback pricing if needed
                if long_ask <= 0 and long_last > 0:
                    long_bid = long_last * 0.95
                    long_ask = long_last * 1.05
                
                long_mid = (long_bid + long_ask) / 2

                # Calculate spread metrics
                spread_width = short_strike - long_strike
                if spread_width <= 0:
                    continue

                # Net credit = premium received - premium paid
                # Conservative: use bid for short (what we get) and ask for long (what we pay)
                net_credit = short_bid - long_ask
                if net_credit <= 0:
                    continue  # Debit spread, not credit

                # Also calculate mid-based credit for reference
                net_credit_mid = short_mid - long_mid

                # Max loss = spread width - net credit (per share)
                max_loss = spread_width - net_credit
                if max_loss <= 0:
                    continue  # Impossible spread

                # Max profit = net credit (per share)
                max_profit = net_credit

                # Capital required = max loss per contract
                capital_required = max_loss * 100

                # Return on risk = net credit / max loss
                return_on_risk = (net_credit / max_loss) * 100

                # Breakeven = short strike - net credit
                breakeven = short_strike - net_credit

                # OTM percentage (safety cushion from current price to breakeven)
                otm_pct = ((price - breakeven) / price) * 100

                # Probability of profit (rough estimate based on short delta)
                # If delta is -0.20, roughly 80% chance of staying OTM
                pop_estimate = (1 - abs(short_delta)) * 100

                # Credit efficiency = net credit / spread width
                credit_efficiency = (net_credit / spread_width) * 100

                # Monthly return (normalized to 30 days)
                monthly_return = return_on_risk * (30 / dte) if dte > 0 else 0

                if monthly_return < args.min_return:
                    continue

                # ══ NEW: Coach Mak Enhanced Metrics ══
                
                # Annualized return (compounded monthly)
                annualized_return = ((1 + return_on_risk / 100) ** (365 / dte) - 1) * 100 if dte > 0 else 0
                
                # Credit per dollar of collateral (capital efficiency)
                # Coach Mak's NVDA spread: $71 credit on $500 = 14.2% 
                credit_per_dollar = (net_credit * 100) / capital_required * 100 if capital_required > 0 else 0
                
                # 50% profit target (what to pay to close at 50% profit)
                target_50pct = net_credit * 0.50
                
                # Days to target (estimate based on theta decay - rough)
                # Spreads decay ~50% of value at ~1/3 of time to expiration
                days_to_50pct = int(dte * 0.33) if dte > 0 else 0
                
                # Coach Mak optimal delta range bonus (0.15-0.25 is sweet spot)
                delta_bonus = 0
                if 0.15 <= abs_delta <= 0.25:
                    delta_bonus = 10  # In the sweet spot
                elif 0.12 <= abs_delta < 0.15 or 0.25 < abs_delta <= 0.30:
                    delta_bonus = 5   # Close to sweet spot
                
                # Width efficiency: narrower spreads = less capital, but less credit
                # Coach Mak uses $5-$20 wide spreads typically
                width_score = 0
                if 5 <= spread_width <= 10:
                    width_score = 8  # Optimal width
                elif 10 < spread_width <= 20:
                    width_score = 5  # Good width
                elif spread_width < 5:
                    width_score = 3  # Too narrow, low credit
                else:
                    width_score = 2  # Very wide, more capital
                
                # ── Spread composite score ──
                ivr_score = (iv_rank / 100) if iv_rank else 0.5
                qual_contribution = (quality_score / 100) * 10

                # ══ NEW: Coach Mak Style Scoring ══
                # Emphasizes capital efficiency and optimal delta range
                score = (
                    return_on_risk * 0.25          # return on risk
                    + credit_per_dollar * 0.20    # capital efficiency (Coach Mak key metric)
                    + pop_estimate * 0.15          # probability of profit
                    + ivr_score * 12               # IV rank bonus
                    + delta_bonus                  # optimal delta range bonus
                    + width_score                  # spread width optimization
                    + qual_contribution * 0.4     # fundamental quality
                    + otm_pct * 0.08              # safety cushion
                )

                results.append({
                    "ticker": ticker_symbol,
                    "price": round(price, 2),
                    "short_strike": short_strike,
                    "long_strike": long_strike,
                    "spread_width": spread_width,
                    "exp": exp_str,
                    "dte": dte,
                    "short_bid": short_bid,
                    "short_ask": short_ask,
                    "short_mid": round(short_mid, 2),
                    "long_bid": long_bid,
                    "long_ask": long_ask,
                    "long_mid": round(long_mid, 2),
                    "net_credit": round(net_credit, 2),
                    "net_credit_mid": round(net_credit_mid, 2),
                    "max_loss": round(max_loss, 2),
                    "max_profit": round(max_profit * 100, 0),  # per contract
                    "capital": round(capital_required, 0),
                    "return_on_risk": round(return_on_risk, 2),
                    "monthly_ret": round(monthly_return, 2),
                    "annualized_ret": round(min(annualized_return, 9999), 1),  # cap display
                    "breakeven": round(breakeven, 2),
                    "otm_pct": round(otm_pct, 1),
                    "pop": round(pop_estimate, 1),
                    "efficiency": round(credit_efficiency, 1),
                    "credit_per_dollar": round(credit_per_dollar, 2),
                    "target_50pct": round(target_50pct, 2),
                    "days_to_50pct": days_to_50pct,
                    "delta": round(short_delta, 3),
                    "iv": round(short_iv * 100, 1),
                    "iv_rank": iv_rank,
                    "volume": int(short_volume) if short_volume and not np.isnan(short_volume) else 0,
                    "oi": int(short_oi) if short_oi and not np.isnan(short_oi) else 0,
                    "earnings": "⚠️" if earnings_before_exp else "",
                    "quality": quality_score,
                    "score": round(score, 2),
                })

    except Exception as e:
        print(f"  ⚠️  Error processing spread for {ticker_symbol}: {e}", file=sys.stderr)

    return results, fund if 'fund' in dir() else (results, None)


# ── Broken Wing Butterfly Screening ──────────────────────────────────────────

def screen_butterfly(ticker_symbol, args, risk_free_rate=0.045, fundamentals_cache=None):
    """
    Screen a single ticker for put broken wing butterfly (BWB) opportunities.
    
    Put BWB Structure:
    - Buy 1 OTM put (upper wing)
    - Sell 2 ATM/OTM puts (body)
    - Buy 1 further OTM put (lower wing - BROKEN/wider)
    
    For a credit BWB:
    - Collect net credit on entry
    - Max profit at short strike (body)
    - No risk above upper wing
    - Risk only on broken wing side (downside)
    - Max loss = broken wing width - credit received
    """
    results = []

    try:
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info or {}

        # Get current price
        price = info.get("regularMarketPrice") or info.get("currentPrice")
        if not price:
            hist = ticker.history(period="5d")
            if hist.empty:
                return results, None
            price = hist["Close"].iloc[-1]

        # Fundamentals
        fund = None
        if fundamentals_cache is not None and ticker_symbol in fundamentals_cache:
            fund = fundamentals_cache[ticker_symbol]
        else:
            fund = get_fundamentals(ticker, ticker_symbol)
            if fundamentals_cache is not None:
                fundamentals_cache[ticker_symbol] = fund

        quality_score = compute_quality_score(fund)
        iv_rank = estimate_iv_rank(ticker)
        earnings_date = get_earnings_date(ticker)

        # Option expirations
        try:
            expirations = ticker.options
        except Exception:
            return results, fund
        if not expirations:
            return results, fund

        today = datetime.now().date()

        for exp_str in expirations:
            exp_date = datetime.strptime(exp_str, "%Y-%m-%d").date()
            dte = (exp_date - today).days
            if dte < args.min_dte or dte > args.max_dte:
                continue
            T = dte / 365.0

            # Earnings risk
            earnings_before_exp = False
            if earnings_date:
                try:
                    ed = earnings_date.date() if hasattr(earnings_date, "date") else earnings_date
                    earnings_before_exp = today <= ed <= exp_date
                except Exception:
                    pass

            try:
                chain = ticker.option_chain(exp_str)
                puts = chain.puts
            except Exception:
                continue
            if puts.empty or len(puts) < 4:
                continue

            # Sort by strike ascending for easier iteration
            puts_sorted = puts.sort_values("strike", ascending=True).reset_index(drop=True)
            strikes = puts_sorted["strike"].tolist()
            
            # Find butterfly candidates
            # We need: upper strike > short strike > lower strike
            # For broken wing: (upper - short) < (short - lower)
            
            for i, short_strike in enumerate(strikes):
                # Skip strikes too close to current price (want OTM butterflies)
                if short_strike >= price * 0.98:
                    continue
                if short_strike <= price * 0.70:  # Too far OTM
                    continue
                    
                short_row = puts_sorted[puts_sorted["strike"] == short_strike].iloc[0]
                short_bid = short_row.get("bid", 0)
                short_ask = short_row.get("ask", 0)
                short_last = short_row.get("lastPrice", 0)
                short_iv = short_row.get("impliedVolatility", 0)
                short_volume = short_row.get("volume", 0)
                short_oi = short_row.get("openInterest", 0)
                
                # Handle NaN values
                short_bid = 0 if (short_bid is None or (isinstance(short_bid, float) and np.isnan(short_bid))) else short_bid
                short_ask = 0 if (short_ask is None or (isinstance(short_ask, float) and np.isnan(short_ask))) else short_ask
                short_last = 0 if (short_last is None or (isinstance(short_last, float) and np.isnan(short_last))) else short_last
                short_iv = 0.35 if (short_iv is None or short_iv == 0 or (isinstance(short_iv, float) and np.isnan(short_iv))) else short_iv
                short_volume = 0 if (short_volume is None or (isinstance(short_volume, float) and np.isnan(short_volume))) else short_volume
                short_oi = 0 if (short_oi is None or (isinstance(short_oi, float) and np.isnan(short_oi))) else short_oi
                
                if short_bid <= 0:
                    if short_last > 0:
                        short_bid = short_last * 0.95
                        short_ask = short_last * 1.05
                    else:
                        continue
                
                short_mid = (short_bid + short_ask) / 2
                
                # Look for upper wing (1-2 strikes above short)
                upper_candidates = [s for s in strikes if short_strike < s <= short_strike * 1.10]
                if not upper_candidates:
                    continue
                    
                for upper_strike in upper_candidates:
                    upper_row = puts_sorted[puts_sorted["strike"] == upper_strike].iloc[0]
                    upper_bid = upper_row.get("bid", 0)
                    upper_ask = upper_row.get("ask", 0)
                    upper_last = upper_row.get("lastPrice", 0)
                    
                    # Handle NaN
                    upper_bid = 0 if (upper_bid is None or (isinstance(upper_bid, float) and np.isnan(upper_bid))) else upper_bid
                    upper_ask = 0 if (upper_ask is None or (isinstance(upper_ask, float) and np.isnan(upper_ask))) else upper_ask
                    upper_last = 0 if (upper_last is None or (isinstance(upper_last, float) and np.isnan(upper_last))) else upper_last
                    
                    if upper_ask <= 0:
                        if upper_last > 0:
                            upper_ask = upper_last * 1.05
                        else:
                            continue
                    
                    upper_mid = (upper_bid + upper_ask) / 2 if upper_bid > 0 else upper_ask
                    upper_width = upper_strike - short_strike
                    
                    # Look for lower wing (broken - wider than upper wing)
                    # Target: 1.5x to 3x the upper wing width
                    target_lower_min = short_strike - upper_width * 3
                    target_lower_max = short_strike - upper_width * 1.5
                    
                    lower_candidates = [s for s in strikes if target_lower_min <= s <= target_lower_max]
                    if not lower_candidates:
                        # Try wider range
                        lower_candidates = [s for s in strikes if s < short_strike - upper_width]
                        if lower_candidates:
                            lower_candidates = lower_candidates[-3:]  # Take closest 3
                    
                    if not lower_candidates:
                        continue
                    
                    for lower_strike in lower_candidates:
                        lower_row = puts_sorted[puts_sorted["strike"] == lower_strike].iloc[0]
                        lower_bid = lower_row.get("bid", 0)
                        lower_ask = lower_row.get("ask", 0)
                        lower_last = lower_row.get("lastPrice", 0)
                        
                        # Handle NaN
                        lower_bid = 0 if (lower_bid is None or (isinstance(lower_bid, float) and np.isnan(lower_bid))) else lower_bid
                        lower_ask = 0 if (lower_ask is None or (isinstance(lower_ask, float) and np.isnan(lower_ask))) else lower_ask
                        lower_last = 0 if (lower_last is None or (isinstance(lower_last, float) and np.isnan(lower_last))) else lower_last
                        
                        if lower_ask <= 0:
                            if lower_last > 0:
                                lower_ask = lower_last * 1.05
                            else:
                                continue
                        
                        lower_mid = (lower_bid + lower_ask) / 2 if lower_bid > 0 else lower_ask
                        lower_width = short_strike - lower_strike
                        
                        # Verify it's a broken wing (lower width > upper width)
                        if lower_width <= upper_width:
                            continue
                        
                        # Calculate net credit/debit
                        # Buy 1 upper + Buy 1 lower - Sell 2 short
                        # Credit = 2 * short_bid - upper_ask - lower_ask
                        net_credit = 2 * short_bid - upper_ask - lower_ask
                        net_credit_mid = 2 * short_mid - upper_mid - lower_mid
                        
                        # We want credit butterflies
                        if net_credit <= 0:
                            continue
                        
                        # Max profit = upper_width + net_credit (at short strike)
                        # This is because the upper spread is worth upper_width at expiry if price = short
                        max_profit = upper_width + net_credit
                        
                        # Max loss = lower_width - upper_width - net_credit (on broken wing side)
                        # Only occurs if price drops below lower strike
                        max_loss = lower_width - upper_width - net_credit
                        if max_loss <= 0:
                            # Free money? Unlikely but check
                            max_loss = 0.01
                        
                        # Capital/collateral = max loss per contract
                        capital_required = max_loss * 100
                        
                        # Return on risk
                        return_on_risk = (net_credit / max_loss) * 100 if max_loss > 0 else 999
                        
                        # Breakevens
                        upper_breakeven = upper_strike - net_credit
                        lower_breakeven = lower_strike + (lower_width - upper_width - net_credit)
                        
                        # OTM percentage (price to short strike)
                        otm_pct = ((price - short_strike) / price) * 100
                        
                        # Probability of max profit (rough: based on landing at short strike)
                        # Use delta of short strike as proxy
                        sigma = short_iv if short_iv > 0.15 else 0.35
                        greeks = bs_put_greeks(price, short_strike, T, risk_free_rate, sigma)
                        short_delta = greeks["delta"]
                        
                        # PoP estimate: probability price stays between breakevens
                        # Rough: 1 - abs(delta) for upper side
                        pop_estimate = (1 - abs(short_delta)) * 100 * 0.8  # Conservative
                        
                        # Monthly return
                        monthly_return = return_on_risk * (30 / dte) if dte > 0 else 0
                        
                        if monthly_return < args.min_return:
                            continue
                        
                        # Score
                        ivr_score = (iv_rank / 100) if iv_rank else 0.5
                        qual_contribution = (quality_score / 100) * 10
                        
                        score = (
                            return_on_risk * 0.30
                            + pop_estimate * 0.25
                            + ivr_score * 15
                            + otm_pct * 0.15
                            + qual_contribution * 0.5
                            + (max_profit / max_loss) * 5  # Reward high profit/risk ratio
                        )
                        
                        results.append({
                            "ticker": ticker_symbol,
                            "price": round(price, 2),
                            "upper_strike": upper_strike,
                            "short_strike": short_strike,
                            "lower_strike": lower_strike,
                            "upper_width": upper_width,
                            "lower_width": lower_width,
                            "exp": exp_str,
                            "dte": dte,
                            "net_credit": round(net_credit, 2),
                            "net_credit_mid": round(net_credit_mid, 2),
                            "max_profit": round(max_profit * 100, 0),
                            "max_loss": round(max_loss, 2),
                            "capital": round(capital_required, 0),
                            "return_on_risk": round(return_on_risk, 2),
                            "monthly_ret": round(monthly_return, 2),
                            "upper_be": round(upper_breakeven, 2),
                            "lower_be": round(lower_breakeven, 2),
                            "otm_pct": round(otm_pct, 1),
                            "pop": round(pop_estimate, 1),
                            "delta": round(short_delta, 3),
                            "iv": round(short_iv * 100, 1),
                            "iv_rank": iv_rank,
                            "volume": int(short_volume) if not np.isnan(short_volume) else 0,
                            "oi": int(short_oi) if not np.isnan(short_oi) else 0,
                            "earnings": "⚠️" if earnings_before_exp else "",
                            "quality": quality_score,
                            "score": round(score, 2),
                        })

    except Exception as e:
        print(f"  ⚠️  Error processing butterfly for {ticker_symbol}: {e}", file=sys.stderr)

    return results, fund if 'fund' in dir() else (results, None)


# ── Output formatting ─────────────────────────────────────────────────────────

def star_rating(score, thresholds=(12, 16, 20)):
    """Return star indicator based on score thresholds."""
    if score >= thresholds[2]:
        return "★★★"
    elif score >= thresholds[1]:
        return "★★"
    elif score >= thresholds[0]:
        return "★"
    return ""


def print_fundamentals_table(fund_data):
    """Print a summary table of fundamentals for all tickers."""
    if not fund_data:
        return

    headers = [
        "Ticker", "Sector", "Mkt Cap", "P/E", "Gross%", "Oper%",
        "Net%", "FCF", "FCF Yld%", "Rev Grw%", "Quality"
    ]
    rows = []
    for f in fund_data.values():
        if f is None:
            continue
        qscore = compute_quality_score(f)
        rows.append([
            f["ticker"],
            (f.get("sector") or "")[:18],
            format_large_num(f.get("market_cap")),
            f"{f['pe_ratio']}" if f.get("pe_ratio") else "N/A",
            f"{f['gross_margin']}%" if f.get("gross_margin") is not None else "N/A",
            f"{f['op_margin']}%" if f.get("op_margin") is not None else "N/A",
            f"{f['net_margin']}%" if f.get("net_margin") is not None else "N/A",
            format_large_num(f.get("fcf")),
            f"{f['fcf_yield']}%" if f.get("fcf_yield") is not None else "N/A",
            f"{f['revenue_growth']}%" if f.get("revenue_growth") is not None else "N/A",
            f"{qscore}/100",
        ])

    if rows:
        # Sort by quality score descending
        rows.sort(key=lambda r: int(r[-1].split("/")[0]), reverse=True)
        print(f"\n{'─' * 100}")
        print("  📊 FUNDAMENTAL SUMMARY")
        print(f"{'─' * 100}")
        print(tabulate(rows, headers=headers, tablefmt="simple", numalign="right"))
        print()


def print_income_projection(results, top_n=10):
    """
    Print weekly/monthly income projection based on top opportunities.
    Inspired by Coach Mak's strategy: Delta 0.15-0.25, weekly $1000s cash flow.
    """
    if not results:
        return

    sorted_r = sorted(results, key=lambda x: x["score"], reverse=True)[:top_n]

    print(f"\n{'─' * 90}")
    print("  💵 INCOME PROJECTION (Coach Mak Strategy: Delta 0.15–0.25)")
    print(f"{'─' * 90}")

    total_weekly_theta = 0
    total_monthly_ret = 0
    total_capital = 0

    headers = ["Ticker", "Strike", "Exp", "DTE", "Delta", "Θ $/day", "$/week", "$/month", "Capital"]
    rows = []

    for r in sorted_r:
        daily_theta = abs(r["theta"])
        weekly = daily_theta * 7
        monthly = daily_theta * 30
        total_weekly_theta += weekly
        total_monthly_ret += monthly
        total_capital += r["capital"]

        rows.append([
            r["ticker"],
            f"${r['strike']}",
            r["exp"],
            r["dte"],
            f"{r['delta']:.2f}",
            f"${daily_theta:.2f}",
            f"${weekly:.0f}",
            f"${monthly:.0f}",
            f"${r['capital']:,.0f}",
        ])

    print(tabulate(rows, headers=headers, tablefmt="simple", numalign="right"))
    print(f"\n  📊 If you sold all {len(sorted_r)} positions:")
    print(f"     Weekly theta income:  ${total_weekly_theta:,.0f}")
    print(f"     Monthly theta income: ${total_monthly_ret:,.0f}")
    print(f"     Total capital needed: ${total_capital:,.0f}")
    if total_capital > 0:
        monthly_roi = (total_monthly_ret / total_capital) * 100
        print(f"     Monthly ROI:          {monthly_roi:.2f}%")
    print(f"  ⚠️  Theta ≠ guaranteed profit — it's the time decay working in your favor")
    print(f"     Actual P&L depends on stock movement, IV changes, and position management")
    print()


def print_spread_income_projection(results, top_n=10):
    """
    Print income projection for put credit spreads.
    Shows potential weekly/monthly income with defined risk.
    """
    if not results:
        return

    sorted_r = sorted(results, key=lambda x: x["score"], reverse=True)[:top_n]

    print(f"\n{'─' * 95}")
    print("  💵 SPREAD INCOME PROJECTION (Defined Risk Strategy)")
    print(f"{'─' * 95}")

    total_weekly = 0
    total_monthly = 0
    total_capital = 0
    total_max_profit = 0

    headers = ["Ticker", "Spread", "Exp", "DTE", "Credit", "Max Loss", "RoR%", "$/week", "$/month", "Capital"]
    rows = []

    for r in sorted_r:
        # If held to expiration and profitable, collect full credit
        # Estimate based on time decay - credit spread decays over time
        daily_decay = (r["net_credit"] * 100) / r["dte"] if r["dte"] > 0 else 0
        weekly = daily_decay * 7
        monthly = daily_decay * 30
        total_weekly += weekly
        total_monthly += monthly
        total_capital += r["capital"]
        total_max_profit += r["max_profit"]

        rows.append([
            r["ticker"],
            f"${r['short_strike']}/{r['long_strike']}",
            r["exp"],
            r["dte"],
            f"${r['net_credit']:.2f}",
            f"${r['max_loss']:.2f}",
            f"{r['return_on_risk']:.1f}%",
            f"${weekly:.0f}",
            f"${monthly:.0f}",
            f"${r['capital']:,.0f}",
        ])

    print(tabulate(rows, headers=headers, tablefmt="simple", numalign="right"))
    print(f"\n  📊 If you sold all {len(sorted_r)} spreads:")
    print(f"     Weekly decay income:    ${total_weekly:,.0f}")
    print(f"     Monthly decay income:   ${total_monthly:,.0f}")
    print(f"     Max profit (if all expire worthless): ${total_max_profit:,.0f}")
    print(f"     Total capital at risk:  ${total_capital:,.0f}")
    if total_capital > 0:
        max_roi = (total_max_profit / total_capital) * 100
        print(f"     Max ROI (at expiration): {max_roi:.2f}%")
    print(f"\n  💡 Spread Advantages:")
    print(f"     • Defined risk: You know max loss upfront")
    print(f"     • Less capital: ~${total_capital/len(sorted_r):,.0f}/spread vs. thousands for CSPs")
    print(f"     • Works in smaller accounts (no need for $10k+ per position)")
    print(f"  ⚠️  Close at 50-75% profit to lock in gains and reduce risk")
    print()


def print_spread_results(all_results, args, fund_data):
    """Print the spread results table and optional extras."""
    if not all_results:
        print("\n  No spread opportunities found matching your criteria.")
        print("  Try relaxing filters (lower --min-return or wider delta range)")
        return

    # Sort by score descending
    all_results.sort(key=lambda x: x["score"], reverse=True)
    top_results = all_results[:args.top]

    # ── Fundamentals table ──
    if args.fundamentals and fund_data:
        print_fundamentals_table(fund_data)

    # ── Main spread table (Coach Mak enhanced) ──
    if args.verbose:
        headers = [
            "Ticker", "Price", "Short", "Long", "Width", "Exp", "DTE",
            "S.Bid", "S.Ask", "L.Bid", "L.Ask", "Credit", "Max Loss",
            "RoR%", "Ann%", "Capital", "$/Cap%", "Exit@50%", "~Days",
            "B/E", "OTM%", "PoP%", "Δ", "IV%", "IVR", "Qlty", "Earn", "Score", "Rate"
        ]
    else:
        headers = [
            "Ticker", "Price", "Short/Long", "Width", "Exp", "DTE",
            "Credit", "Capital", "RoR%", "Ann%", "$/Cap%", "Exit50%",
            "PoP%", "Δ", "IVR", "Earn", "Score", "Rate"
        ]

    rows = []
    for r in top_results:
        rating = star_rating(r["score"], thresholds=(20, 28, 35))

        if args.verbose:
            rows.append([
                r["ticker"],
                f"${r['price']}",
                f"${r['short_strike']}",
                f"${r['long_strike']}",
                f"${r['spread_width']}",
                r["exp"],
                r["dte"],
                f"${r['short_bid']:.2f}",
                f"${r['short_ask']:.2f}",
                f"${r['long_bid']:.2f}",
                f"${r['long_ask']:.2f}",
                f"${r['net_credit']:.2f}",
                f"${r['max_loss']:.2f}",
                f"{r['return_on_risk']:.1f}%",
                f"{r['annualized_ret']:.0f}%",
                f"${r['capital']:,.0f}",
                f"{r['credit_per_dollar']:.1f}%",
                f"${r['target_50pct']:.2f}",
                r["days_to_50pct"],
                f"${r['breakeven']}",
                f"{r['otm_pct']}%",
                f"{r['pop']:.0f}%",
                f"{r['delta']:.2f}",
                f"{r['iv']:.0f}",
                f"{r['iv_rank']}%" if r["iv_rank"] else "N/A",
                r["quality"],
                r["earnings"],
                f"{r['score']:.1f}",
                rating,
            ])
        else:
            rows.append([
                r["ticker"],
                f"${r['price']}",
                f"${r['short_strike']}/{r['long_strike']}",
                f"${r['spread_width']}",
                r["exp"],
                r["dte"],
                f"${r['net_credit']:.2f}",
                f"${r['capital']:,.0f}",
                f"{r['return_on_risk']:.1f}%",
                f"{r['annualized_ret']:.0f}%",
                f"{r['credit_per_dollar']:.1f}%",
                f"${r['target_50pct']:.2f}",
                f"{r['pop']:.0f}%",
                f"{r['delta']:.2f}",
                f"{r['iv_rank']}%" if r["iv_rank"] else "N/A",
                r["earnings"],
                f"{r['score']:.1f}",
                rating,
            ])

    print(f"\n📋 Top {len(top_results)} PUT CREDIT SPREADS (of {len(all_results)} found):\n")
    print(tabulate(rows, headers=headers, tablefmt="simple", numalign="right"))

    # ── Coach Mak Exit Strategy ──
    print(f"\n{'─' * 95}")
    print("  🎯 COACH MAK EXIT TARGETS (Close at 50% profit)")
    print(f"{'─' * 95}")
    exit_rows = []
    for r in top_results[:10]:
        exit_rows.append([
            r["ticker"],
            f"${r['short_strike']}/{r['long_strike']}",
            r["exp"],
            f"${r['net_credit']:.2f}",
            f"${r['target_50pct']:.2f}",
            f"~{r['days_to_50pct']}d",
            f"${r['net_credit'] * 50:.0f}",  # profit per contract at 50%
        ])
    exit_headers = ["Ticker", "Spread", "Exp", "Credit", "Close@", "~Days", "Profit/Contract"]
    print(tabulate(exit_rows, headers=exit_headers, tablefmt="simple", numalign="right"))

    # ── Income projection ──
    if args.income:
        print_spread_income_projection(all_results, top_n=args.top)

    # ── Legend ──
    print(f"\n{'═' * 95}")
    print("  ★★★ = Top tier (Coach Mak style) | ★★ = Strong | ★ = Good")
    print("  Short/Long = Sell this put / Buy this put (protection)")
    print("  RoR%       = Return on Risk = Credit / Max Loss")
    print("  Ann%       = Annualized return (compounded)")
    print("  $/Cap%     = Credit per $ of capital (Coach Mak's key efficiency metric)")
    print("  Exit50%    = Price to close spread at 50% profit")
    print("  ~Days      = Estimated days to reach 50% profit (theta decay)")
    print("  PoP%       = Probability of Profit (from delta)")
    print("  Δ          = Delta of short strike (0.15-0.25 = Coach Mak sweet spot)")
    print("  ⚠️         = Earnings before expiration (binary risk)")
    print("  💡 Coach Mak strategy: Enter credit spreads, exit at 50-75% profit")
    print(f"{'═' * 95}\n")


def print_butterfly_results(all_results, args, fund_data):
    """Print the broken wing butterfly results table."""
    if not all_results:
        print("\n  No broken wing butterfly opportunities found matching your criteria.")
        print("  Try relaxing filters (lower --min-return or wider DTE range)")
        return

    # Sort by score descending
    all_results.sort(key=lambda x: x["score"], reverse=True)
    top_results = all_results[:args.top]

    # ── Fundamentals table ──
    if args.fundamentals and fund_data:
        print_fundamentals_table(fund_data)

    # ── Main butterfly table ──
    headers = [
        "Ticker", "Price", "Upper", "Short", "Lower", "Exp", "DTE",
        "Credit", "Max Profit", "Max Loss", "RoR%", "Mo.Ret%", "Capital",
        "OTM%", "PoP%", "IVR", "Qlty", "Earn", "Score", "Rate"
    ]

    rows = []
    for r in top_results:
        rating = star_rating(r["score"], thresholds=(20, 30, 40))

        rows.append([
            r["ticker"],
            f"${r['price']}",
            f"${r['upper_strike']}",
            f"${r['short_strike']}",
            f"${r['lower_strike']}",
            r["exp"],
            r["dte"],
            f"${r['net_credit']:.2f}",
            f"${r['max_profit']:,.0f}",
            f"${r['max_loss']:.2f}",
            f"{r['return_on_risk']:.1f}%",
            f"{r['monthly_ret']:.1f}%",
            f"${r['capital']:,.0f}",
            f"{r['otm_pct']:.1f}%",
            f"{r['pop']:.1f}%",
            f"{r['iv_rank']}%" if r["iv_rank"] else "N/A",
            r["quality"],
            r["earnings"],
            f"{r['score']:.1f}",
            rating,
        ])

    print(f"\n🦋 Top {len(top_results)} BROKEN WING BUTTERFLIES (of {len(all_results)} found):\n")
    print(tabulate(rows, headers=headers, tablefmt="simple", numalign="right"))

    # ── Income summary ──
    total_credit = sum(r["net_credit"] * 100 for r in top_results)
    total_max_profit = sum(r["max_profit"] for r in top_results)
    total_capital = sum(r["capital"] for r in top_results)
    
    print(f"\n{'─' * 95}")
    print("  🦋 BUTTERFLY INCOME SUMMARY")
    print(f"{'─' * 95}")
    print(f"  Total credit collected:  ${total_credit:,.0f}")
    print(f"  Total max profit:        ${total_max_profit:,.0f}")
    print(f"  Total capital at risk:   ${total_capital:,.0f}")
    if total_capital > 0:
        max_roi = (total_max_profit / total_capital) * 100
        print(f"  Max ROI (at expiration): {max_roi:.1f}%")
    
    print(f"\n  💡 Broken Wing Butterfly Advantages:")
    print(f"     • Credit entry: Collect premium upfront")
    print(f"     • Low capital: Only ~${total_capital/len(top_results):,.0f}/butterfly")
    print(f"     • High reward/risk: Max profit often > capital at risk")
    print(f"     • No upside risk: Price above upper strike = keep credit")
    print(f"  ⚠️  Max profit occurs ONLY if price pins at short strike at expiration")
    print(f"     Consider closing at 50% profit or managing early")
    print()

    # ── Legend ──
    print(f"{'═' * 95}")
    print("  ★★★ = Top tier | ★★ = Strong | ★ = Good")
    print("  Structure: Buy Upper Put → Sell 2× Short Put → Buy Lower Put (broken wing)")
    print("  Upper/Short/Lower = Strike prices of the butterfly")
    print("  Credit     = Net premium received per share (×100 for contract)")
    print("  Max Profit = Credit + Upper wing width (per contract, if price = short strike)")
    print("  Max Loss   = Broken wing width - Upper width - Credit (only if price < lower)")
    print("  RoR%       = Return on Risk = Credit / Max Loss")
    print("  ⚠️         = Earnings before expiration (avoid or size small)")
    print(f"{'═' * 95}\n")


def print_results(all_results, args, fund_data):
    """Print the main results table and optional extras."""
    if not all_results:
        print("\n  No opportunities found matching your criteria.")
        print("  Try relaxing filters (lower --min-return or wider delta range)")
        return

    # Sort by score descending
    all_results.sort(key=lambda x: x["score"], reverse=True)
    top_results = all_results[:args.top]

    # ── Fundamentals table ──
    if args.fundamentals and fund_data:
        print_fundamentals_table(fund_data)

    # ── Main table ──
    if args.verbose:
        headers = [
            "Ticker", "Price", "Strike", "Exp", "DTE",
            "Bid", "Ask", "Delta", "Γ Gamma", "Θ $/day", "Vega", "Rho",
            "IV%", "IVR", "OTM%", "Mo.Ret%", "Capital", "Premium",
            "Vol", "OI", "Qlty", "Earn", "Score", "Rating"
        ]
    else:
        headers = [
            "Ticker", "Price", "Strike", "Exp", "DTE",
            "Delta", "Θ $/day", "Gamma", "Vega",
            "IV%", "IVR", "OTM%", "Mo.Ret%", "Capital", "Premium",
            "Qlty", "Earn", "Score", "Rating"
        ]

    rows = []
    for r in top_results:
        rating = star_rating(r["score"])

        if args.verbose:
            rows.append([
                r["ticker"],
                f"${r['price']}",
                f"${r['strike']}",
                r["exp"],
                r["dte"],
                f"${r['bid']:.2f}",
                f"${r['ask']:.2f}",
                f"{r['delta']:.3f}",
                f"{r['gamma']:.5f}",
                f"${r['theta']:.2f}",
                f"{r['vega']:.3f}",
                f"{r['rho']:.4f}",
                f"{r['iv']}",
                f"{r['iv_rank']}%" if r["iv_rank"] else "N/A",
                f"{r['otm_pct']}%",
                f"{r['monthly_ret']}%",
                f"${r['capital']:,.0f}",
                f"${r['premium']:,.0f}",
                r["volume"],
                r["oi"],
                r["quality"],
                r["earnings"],
                r["score"],
                rating,
            ])
        else:
            rows.append([
                r["ticker"],
                f"${r['price']}",
                f"${r['strike']}",
                r["exp"],
                r["dte"],
                f"{r['delta']:.2f}",
                f"${r['theta']:.2f}",
                f"{r['gamma']:.5f}",
                f"{r['vega']:.3f}",
                f"{r['iv']}",
                f"{r['iv_rank']}%" if r["iv_rank"] else "N/A",
                f"{r['otm_pct']}%",
                f"{r['monthly_ret']}%",
                f"${r['capital']:,.0f}",
                f"${r['premium']:,.0f}",
                r["quality"],
                r["earnings"],
                r["score"],
                rating,
            ])

    print(f"\n📋 Top {len(top_results)} opportunities (of {len(all_results)} found):\n")
    print(tabulate(rows, headers=headers, tablefmt="simple", numalign="right"))

    # ── Income projection ──
    if args.income:
        print_income_projection(all_results, top_n=args.top)

    # ── Legend ──
    print(f"\n{'═' * 90}")
    print("  ★★★ = Top tier | ★★ = Strong | ★ = Good")
    print("  Θ $/day = Theta decay per day per contract (your income as time passes)")
    print("  Γ Gamma = Rate of delta change (high = assignment risk accelerates)")
    print("  Vega    = Premium change per 1% IV move (per share)")
    print("  Qlty    = Fundamental quality score (0-100)")
    print("  ⚠️      = Earnings before expiration (binary risk)")
    print("  Score   = Composite: return × 0.4 + IVR × 15 + OTM × 0.25 + θ bonus − γ penalty + quality")
    print(f"{'═' * 90}\n")


# ── CLI entry point ───────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="CSP (Cash-Secured Put) Screener v2.2 — Greeks, fundamentals, quality scoring"
    )
    # Ticker selection
    parser.add_argument(
        "-t", "--tickers", nargs="+", default=None,
        help="Tickers to screen (default: popular watchlist)"
    )
    parser.add_argument(
        "--ai-stocks", action="store_true",
        help="Use curated AI/tech + datacenter watchlist (NVDA, AMD, MSFT, EQIX, etc.)"
    )
    parser.add_argument(
        "--income", action="store_true",
        help="Income mode: Coach Mak strategy (delta 0.15-0.25, weekly income projection)"
    )
    parser.add_argument(
        "--mak-strategy", action="store_true",
        help="Mak Strategy Mode: Optimized for 5-10%% monthly (IVR>50, delta 0.20-0.35, return>1.0%%)"
    )
    parser.add_argument(
        "--spreads", action="store_true",
        help="Credit spread mode: Find put credit spread opportunities (defined risk)"
    )
    parser.add_argument(
        "--butterfly", "--bwb", action="store_true",
        help="Broken wing butterfly mode: Find credit BWB opportunities (Coach Mak style)"
    )
    parser.add_argument(
        "--sector", type=str, default=None,
        help="Filter by sector (e.g., 'Technology', 'Healthcare')"
    )

    # Options filters
    parser.add_argument("--min-ivr", type=float, default=0, help="Minimum IV Rank (0-100)")
    parser.add_argument("--min-return", type=float, default=0.5, help="Minimum monthly return %%")
    parser.add_argument("--min-delta", type=float, default=0.15, help="Min absolute delta")
    parser.add_argument("--max-delta", type=float, default=0.35, help="Max absolute delta")
    parser.add_argument("--min-dte", type=int, default=20, help="Min days to expiration")
    parser.add_argument("--max-dte", type=int, default=50, help="Max days to expiration")
    parser.add_argument("--top", type=int, default=25, help="Number of top results")

    # Fundamental filters
    parser.add_argument("--min-margin", type=float, default=None, help="Min gross margin %%")
    parser.add_argument("--min-fcf-yield", type=float, default=None, help="Min FCF yield %%")
    parser.add_argument("--min-revenue-growth", type=float, default=None, help="Min YoY revenue growth %%")

    # Display options
    parser.add_argument("--fundamentals", action="store_true", help="Show fundamentals summary table")
    parser.add_argument("--verbose", action="store_true", help="Full Greeks detail (incl. Rho, bid/ask)")

    args = parser.parse_args()

    # Mak Strategy Mode: Apply all derived filters
    if args.mak_strategy:
        args.min_ivr = 50  # High IV rank (expensive options)
        args.min_return = 1.0  # 1% monthly minimum
        args.min_delta = 0.20  # OTM but not too far
        args.max_delta = 0.35  # Stay out of gamma risk zone
        args.min_dte = 20  # Theta decay sweet spot
        args.max_dte = 50  # Max holding period
        if not args.tickers:  # Default to Mak's observed tickers
            tickers = ["TSLA", "PLTR", "AMZN", "GOOGL", "META", "NVDA", "AMD", "SOFI", "HOOD", "UBER", "CRM", "AAPL", "MSFT"]
            list_name = "🎯 Mak Strategy Mode (5-10% monthly target)"

    # Income mode: Coach Mak strategy preset
    if args.income:
        if args.min_delta == 0.15 and args.max_delta == 0.35:  # only override if defaults
            args.min_delta = 0.15
            args.max_delta = 0.25

    # Resolve ticker list
    if args.mak_strategy and not args.tickers:
        # Already set above
        pass
    elif args.income and not args.tickers and not args.ai_stocks:
        tickers = INCOME_TICKERS
        list_name = "💵 Income Strategy (Coach Mak)"
    elif args.ai_stocks:
        tickers = AI_TECH_TICKERS
        list_name = "AI/Tech + Datacenter Watchlist"
    elif args.tickers:
        tickers = args.tickers
        list_name = "Custom"
    else:
        tickers = DEFAULT_TICKERS
        list_name = "Default Watchlist"

    # Banner
    if args.butterfly:
        mode_str = "BROKEN WING BUTTERFLIES"
    elif args.spreads:
        mode_str = "PUT CREDIT SPREADS"
    else:
        mode_str = "Cash-Secured Puts"
    print("=" * 95)
    print(f"  💰 CSP SCREENER v2.2 — {mode_str}")
    print(f"  📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  📋 {list_name}: {', '.join(tickers)}")
    print(f"  🎯 Delta: {args.min_delta}–{args.max_delta} | DTE: {args.min_dte}–{args.max_dte}")
    print(f"  📊 Min Return: {args.min_return}% | Min IVR: {args.min_ivr}%", end="")
    if args.min_margin is not None:
        print(f" | Min Margin: {args.min_margin}%", end="")
    if args.min_fcf_yield is not None:
        print(f" | Min FCF Yield: {args.min_fcf_yield}%", end="")
    if args.min_revenue_growth is not None:
        print(f" | Min Rev Growth: {args.min_revenue_growth}%", end="")
    print()
    if args.butterfly:
        print("  🦋 Mode: Broken Wing Butterfly (buy put + sell 2 puts + buy lower put = credit entry)")
    elif args.spreads:
        print("  📐 Mode: Put Credit Spreads (sell put + buy lower put = defined risk)")
    if args.verbose:
        print("  🔬 Verbose mode: full detail enabled")
    print("=" * 95)

    all_results = []
    fund_data = {}

    for i, ticker in enumerate(tickers):
        if args.butterfly:
            scan_type = "butterflies"
        elif args.spreads:
            scan_type = "spreads"
        else:
            scan_type = "CSPs"
        print(f"  Scanning {ticker} for {scan_type}... ({i+1}/{len(tickers)})", flush=True)
        
        if args.butterfly:
            results, fund = screen_butterfly(ticker, args, fundamentals_cache=fund_data)
        elif args.spreads:
            results, fund = screen_spread(ticker, args, fundamentals_cache=fund_data)
        else:
            results, fund = screen_ticker(ticker, args, fundamentals_cache=fund_data)

        # Sector filter
        if args.sector and fund:
            if args.sector.lower() not in (fund.get("sector") or "").lower():
                continue

        # IV rank filter
        if args.min_ivr > 0:
            results = [r for r in results if r["iv_rank"] and r["iv_rank"] >= args.min_ivr]

        all_results.extend(results)

    if args.butterfly:
        print_butterfly_results(all_results, args, fund_data)
    elif args.spreads:
        print_spread_results(all_results, args, fund_data)
    else:
        print_results(all_results, args, fund_data)


if __name__ == "__main__":
    main()
