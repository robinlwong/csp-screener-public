# 💰 CSP Screener v2.2 — Coach Mak Strategy Edition

> **Cash-Secured Put Opportunity Finder with Full Black-Scholes Greeks, Fundamental Scoring & Mak's 5-10% Monthly Strategy**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Made with ❤️](https://img.shields.io/badge/Made%20with-❤️-red.svg)](https://github.com/robinlwong/csp-screener-public)

---

## 👨‍👩‍👧‍👦 New to Options? Start Here!

**Looking for a beginner-friendly explanation?** Check out our **[Family Guide](https://docs.google.com/document/d/YOUR_GOOGLE_DOC_ID/edit)** (Google Docs) - it explains cash-secured puts in plain English with real examples and step-by-step instructions. No jargon, no confusion!

---

A professional-grade options screener optimized for **premium selling strategies** (CSPs, Put Credit Spreads, Broken Wing Butterflies). Includes analysis of Coach Mak's (@wealthcoachmak) trading methodology derived from real trades (Feb 2026).

**No API keys required** — uses free Yahoo Finance data.

---
**No API keys required** — uses free Yahoo Finance data.

---

## Table of Contents

- [🎯 What This Tool Does](#-what-this-tool-does)
- [🚀 Quick Start](#-quick-start)
- [📊 Strategy Overview](#-strategy-overview)
- [📖 CLI Reference](#-cli-reference)
- [🧮 How to Achieve 5-10% Monthly](#-how-to-achieve-5-10-monthly)
- [⚙️ Trade Management](#️-trade-management)
- [🏗️ Architecture & Code Overview](#️-architecture--code-overview)
- [🔧 Development Guide](#-development-guide)
- [📚 Additional Documentation](#-additional-documentation)
- [⚠️ Disclaimer](#️-disclaimer)

---

## 🎯 What This Tool Does

**CSP Screener v2.2** is a CLI tool for screening options premium-selling opportunities. It targets three strategies:

- **Cash-Secured Puts (CSPs)** — Naked put selling (default mode)
- **Put Credit Spreads (PCS)** — Defined risk with `--spreads` flag
- **Broken Wing Butterflies (BWB)** — Advanced defined-risk with `--butterfly` flag

### Core Features

- **Direct market data** via Yahoo Finance API (no authentication needed)
- **Full Black-Scholes Greeks** — Delta, Gamma, Theta, Vega, Rho
- **Fundamental analysis** — Margins, FCF yield, revenue growth, quality scoring
- **Coach Mak Strategy Mode** — Pre-configured filters for 5-10% monthly returns
- **Interactive Brokers integration** — Optional trade execution via TWS/Gateway
- **Parallel C++ implementation** — High-performance alternative to Python

### What's New in Coach Mak Edition

#### Mak Strategy Mode (`--mak-strategy`)
Implements the **exact filters** derived from analyzing Coach Mak's actual trades:
- **IVR ≥ 50:** Target expensive options (high premium)
- **Delta 0.20-0.35:** OTM sweet spot (avoid gamma risk)
- **Monthly return ≥ 1.0%:** Minimum acceptable income
- **DTE 20-50 days:** Theta decay optimization
- **Auto-watchlist:** TSLA, PLTR, AMZN, GOOGL, META, NVDA, AMD, SOFI, HOOD, UBER, CRM

**Target:** **5-10% monthly portfolio returns** through disciplined premium selling.

#### Comprehensive Analysis
- **MAK-ANALYSIS.md:** 14,000-word deep-dive into Mak's strategy
- **MAK-STRATEGY.md:** Condensed reference guide with examples
- **EXECUTIVE-SUMMARY.md:** Strategy analysis & implementation guide
- **Trade-by-trade breakdown** of February 2026 positions

---

## 🚀 Quick Start

### Installation
```bash
pip install -r requirements.txt
```

### Basic Usage

**Mak Strategy Mode (Recommended):**
```bash
python3 screener.py --mak-strategy --top 15
```

**AI/Tech Focus:**
```bash
python3 screener.py --ai-stocks --mak-strategy --top 15
```

**Custom Tickers:**
```bash
python3 screener.py -t NVDA AMD TSLA PLTR --mak-strategy
```

**With Fundamentals:**
```bash
python3 screener.py --mak-strategy --fundamentals --top 20
```

**Trade Execution (Dry-Run):**
```bash
python3 executor.py --symbol NVDA --strike 120 --expiry 2026-03-21
```

### C++ Build & Run

```bash
g++ -std=c++17 -O2 -o screener screener.cpp -lcurl -lpthread -lm
./screener --mak-strategy --top 15
```

---

## 📊 Strategy Overview

### Performance Target
**5-10% monthly** (60-120% annualized) through:
1. Selling cash-secured puts on quality stocks
2. Taking profits at 80-90% of max gain (1-7 days)
3. Rolling losers to collect more premium
4. Layering into high-conviction positions

### Recent Example: GOOGL $305 CSP
- **Opened:** 2/5/26 @ $1.81 premium
- **Closed:** 2/6/26 @ $0.22 buyback
- **Profit:** +$159 (88% gain) in **1 day** 🔥

### Key Principles
1. **Quick profit-taking** > holding for 100%
2. **High IV environments** = fatter premiums
3. **Synchronized expirations** = batch management
4. **Stocks worth owning** (fundamentals matter)
5. **Capital velocity** > squeezing every dollar

### Real Trade Examples

#### 1. GOOGL $305 CSP (Closed Winner)
```
Opened:  2/5/26 @ $1.81 premium ($181)
Closed:  2/6/26 @ $0.22 buyback ($22)
Profit:  +$159 (88% gain)
Duration: 1 day

Lesson: Take 80-90% profits quickly. Capital velocity > max profit.
```

#### 2. TSLA $345 CSP (Open)
```
Opened:  2/5/26 @ $5.65 premium ($565)
Strike:  $345
Exp:     3/6/26 (29 DTE)
Return:  1.64% monthly = ~20.6% annualized

Lesson: High IV = fatter premiums. Layer into convictions (2nd TSLA position).
```

#### 3. PLTR $100 CSP (Open)
```
Opened:  2/5/26 @ $1.41 premium ($141)
Strike:  $100
Exp:     3/6/26 (29 DTE)
Return:  1.41% monthly = ~17.8% annualized

Lesson: Sync expirations (same 3/6 as TSLA) for batch management.
```

---

## 📖 CLI Reference

### Screening Modes

| Mode | Flag | Description |
|------|------|-------------|
| Cash-Secured Puts | _(default)_ | Naked put selling, capital = strike × 100 |
| Put Credit Spreads | `--spreads` | Sell OTM put + buy further OTM put, defined risk |
| Broken Wing Butterflies | `--butterfly` | Buy put + sell 2 puts + buy lower put |
| Coach Mak Strategy | `--mak-strategy` | Auto-applies: IVR≥50, delta 0.20-0.35, return≥1%, DTE 20-50 |
| Income Mode | `--income` | Delta 0.15-0.25, income projections |

### Ticker Selection

```bash
# Mak strategy with auto-watchlist
python3 screener.py --mak-strategy

# AI stocks + Mak filters
python3 screener.py --ai-stocks --mak-strategy

# Custom tickers
python3 screener.py -t TSLA PLTR AMZN --mak-strategy

# Sector filter
python3 screener.py --mak-strategy --sector Technology
```

### Common Flags

| Flag | Default | Purpose |
|------|---------|---------|
| `-t, --tickers` | varies by mode | Custom ticker list |
| `--mak-strategy` | off | Apply Coach Mak's filters |
| `--spreads` | off | Put credit spread mode |
| `--butterfly` | off | Broken wing butterfly mode |
| `--income` | off | Income strategy mode |
| `--ai-stocks` | off | AI/tech watchlist |
| `--min-delta` | 0.15 | Minimum absolute delta |
| `--max-delta` | 0.35 | Maximum absolute delta |
| `--min-dte` | 20 | Minimum days to expiration |
| `--max-dte` | 50 | Maximum days to expiration |
| `--min-ivr` | 0 | Minimum IV Rank (0-100) |
| `--min-return` | 0.5 | Minimum monthly return % |
| `--top` | 25 | Number of results |
| `--fundamentals` | off | Show fundamentals table |
| `--verbose` | off | Full Greeks output |
| `--sector` | none | Filter by sector |
| `--min-margin` | none | Min gross profit margin % |
| `--min-fcf-yield` | none | Min free cash flow yield % |
| `--min-revenue-growth` | none | Min YoY revenue growth % |

**Mak Strategy Mode auto-sets:**
- `--min-ivr 50`
- `--min-return 1.0`
- `--min-delta 0.20`
- `--max-delta 0.35`

### Display Options

```bash
# Show fundamentals table
python3 screener.py --mak-strategy --fundamentals

# Verbose mode (full Greeks including Rho)
python3 screener.py --mak-strategy --verbose

# Combined
python3 screener.py --mak-strategy --fundamentals --verbose --top 15
```

### Output Table Columns

| Column | Description |
|--------|-------------|
| **Ticker** | Stock symbol |
| **Strike** | Put option strike price |
| **Exp** | Expiration date |
| **DTE** | Days to expiration |
| **Bid/Ask** | Option bid and ask prices |
| **Mid** | Midpoint price (fair value) |
| **Delta** | Probability proxy (~20-35% for Mak strategy) |
| **Θ $/day** | **Daily income** from theta decay (per contract) |
| **Gamma** | Delta change rate (lower = better) |
| **Vega** | Sensitivity to IV changes |
| **IV%** | Implied volatility |
| **IVR** | **IV Rank** (0-100, higher = expensive options) |
| **OTM%** | Distance out of the money (safety cushion) |
| **Mo.Ret%** | **Monthly return on capital** (key metric!) |
| **Capital** | Cash required (strike × 100) |
| **Premium** | Total credit collected (mid × 100) |
| **Qlty** | Fundamental quality score (0-100) |
| **Score** | Composite ranking score |
| **Rating** | ★★★ Top tier / ★★ Strong / ★ Good |
| **Earn** | ⚠️ if earnings before expiration |

### Star Ratings

- **★★★** Top 20% of opportunities (composite score > 80th percentile)
- **★★** Strong opportunities (50-80th percentile)
- **★** Good opportunities (below 50th percentile)

---

## 🧮 How to Achieve 5-10% Monthly

### Math Breakdown

**Target:** 5-10% monthly portfolio return

**Method:** Multiple positions @ 1-2% each

**Example Portfolio ($100K):**
- 10 CSPs × $10K capital each = $100K deployed
- Average 1.5% monthly per position = $150/position
- Total monthly income: 10 × $150 = **$1,500 (1.5% of portfolio)**

### Scaling to 10%

1. **More positions:** 15-20 CSPs instead of 10
2. **Higher returns:** Target 2-3% per position (higher IV)
3. **Quick turnaround:** Close at 80-90%, redeploy capital 2-3x/month
4. **Compounding:** Reinvest gains into new positions

### Reality Check

- Not all positions win (expect ~70-80% win rate)
- Some will need to be rolled (extend time)
- Occasional assignments (own the stock, sell covered calls)

**Mak's February:**
- 12 open positions (TSLA, PLTR, AMZN, SOFI, META, CRM, etc.)
- 2 closed winners (GOOGL CSP +88%, GOOGL PCS)
- Result: Likely on track for 5-10% despite -11.7% on long positions

---

## ⚙️ Trade Management

### Entry Checklist
- [ ] IV Rank > 50 (expensive options)
- [ ] Delta 0.20-0.35 (OTM but not too far)
- [ ] DTE 20-50 days (theta sweet spot)
- [ ] Monthly return > 1.0% (minimum acceptable)
- [ ] No earnings before expiration
- [ ] Quality fundamentals (stock worth owning)
- [ ] Liquid options (bid-ask spread <15%)

### Exit Strategy (Winners)
- **Target:** 80-90% of max profit
- **Time:** 1-7 days if hit
- **Example:** Sold put for $1.81, buy back at $0.22 (88% profit) ✅
- **Don't:** Hold for $0.01 buyback (diminishing returns)

### Exit Strategy (Losers)
- **Roll:** Extend expiration, collect more premium
- **Adjust strike:** Move lower if conviction remains
- **Accept assignment:** Own the stock, sell covered calls
- **Don't:** Panic close at max loss (CSP philosophy is to own stock)

### Position Sizing
- **Start small:** 5-10% of portfolio per position
- **Layer:** Add to winners (2-3 contracts on same ticker)
- **Diversify:** 10-15 positions across sectors
- **Allocate:** More capital to higher-vol names (TSLA $565 vs PLTR $141)

### Risk Management

#### Portfolio Level
- **Max positions:** 10-15 at once (avoid over-concentration)
- **Sector limit:** No more than 40% in one sector
- **Correlation:** Avoid too many tech CSPs (they move together)
- **Hedge:** Long shares + LEAPS can offset short put risk

#### Position Level
- **Delta 0.20-0.35:** Avoid ATM strikes (gamma explosion)
- **Quality stocks:** Only sell puts on stocks you'd own
- **Liquidity:** Bid-ask spread <15% (can exit easily)
- **Earnings:** Check calendar, avoid binary events

#### Psychology
- ✅ **No greed:** Take 80-90%, don't hold for 100%
- ✅ **No fear:** Accept assignment risk (it's cash-secured)
- ✅ **Patience:** Roll losers, collect more premium
- ✅ **Discipline:** Follow the rules, don't chase every trade

---

## 🏗️ Architecture & Code Overview

### Repository Structure

```
csp-screener/
├── screener.py           # Main screener (1,712 lines)
├── executor.py           # IB trade executor (323 lines)
├── screener.cpp          # C++ screener (934 lines)
├── executor.cpp          # C++ executor (376 lines)
├── requirements.txt      # Python dependencies
├── README.md             # This file
├── EXECUTIVE-SUMMARY.md  # Strategy overview & implementation guide
├── MAK-ANALYSIS.md       # Deep analysis of Mak's strategy (14KB)
├── MAK-STRATEGY.md       # Quick reference strategy guide (5KB)
└── mak-watchlist.txt     # Mak's observed tickers
```

### Tech Stack

- **Language (primary):** Python 3
- **Language (alternative):** C++17
- **Data source:** Yahoo Finance API via `yfinance` (free, no auth required)
- **Trade execution:** Interactive Brokers TWS/Gateway via `ib_insync` (optional)
- **No web framework, no database, no frontend** — pure CLI tool

#### Python Dependencies

```
yfinance>=0.2.31    # Yahoo Finance API
tabulate>=0.9.0     # CLI table formatting
numpy>=1.24.0       # Numerical computation
scipy>=1.10.0       # Black-Scholes (norm.pdf/cdf from scipy.stats)
```

Optional: `ib_insync` for Interactive Brokers integration.

### Data Flow

```
CLI Args → Mode Selection → Ticker List → Per Ticker:
  → Fetch fundamentals (cached) → Fetch option chain → Per Expiration:
    → Per Put Strike:
      → Calculate Black-Scholes Greeks
      → Apply filters (delta/DTE/return/IVR)
      → Compute composite score
  → Aggregate & sort by score → Display results table
```

### Code Organization in screener.py

1. **Imports & warnings suppression**
2. **Watchlist constants** (`DEFAULT_TICKERS`, `AI_TECH_TICKERS`, `INCOME_TICKERS`)
3. **Black-Scholes Greeks** — `bs_d1_d2()`, `bs_put_greeks()` returning delta, gamma, theta, vega, rho
4. **IV Rank estimation** — `estimate_iv_rank()` compares current IV to 52-week historical vol
5. **Earnings date detection** — `get_earnings_date()` for binary event avoidance
6. **Fundamentals** — `get_fundamentals()`, `compute_quality_score()` (0-100 scale)
7. **Screening engines** — `screen_ticker()` (CSP), `screen_spread()` (PCS), `screen_butterfly()` (BWB)
8. **Display functions** — `print_results()`, `print_spread_results()`, `print_butterfly_results()`, `print_fundamentals_table()`, `print_income_projection()`
9. **CLI entry point** — `main()` with argparse

### executor.py

`CSPExecutor` class wraps Interactive Brokers API:
- `connect()` / `disconnect()` — IB TWS/Gateway connection
- `get_account_summary()` — balances and buying power
- `sell_put()` — place CSP order (dry-run by default)
- `execute_from_screener()` — batch execution from JSON

**Safety:** dry-run mode is the default; `--live` flag required for real orders.

### Key Constants

```python
RISK_FREE_RATE = 0.045  # Used in Black-Scholes calculations

# Mak strategy auto-selects these 13 tickers:
# TSLA, PLTR, AMZN, GOOGL, META, NVDA, AMD, SOFI, HOOD, UBER, CRM, AAPL, MSFT
```

### Scoring Formula

```
Score = (Monthly_Return × 0.40)      # Primary driver
      + (IVR × 0.15)                  # Prefer expensive options
      + (OTM% × 0.25)                 # Safety cushion
      + (Theta_Decay × 1.5)           # Daily income generation
      + (Quality_Score × 0.8)         # Fundamentals
      - (Gamma_Risk × 0.5)            # Penalty for assignment risk
```

**Rationale:**
- **Monthly return (40%):** Income generation is primary goal
- **Theta (high weight):** Daily income matters more than absolute premium
- **Quality (high weight):** Only sell puts on stocks worth owning
- **Gamma (penalty):** Avoid strikes near ATM (delta explosion zone)

### Conventions

#### Naming

- **Functions:** `snake_case` — `bs_put_greeks`, `get_earnings_date`, `screen_ticker`
- **Variables:** `snake_case` — `iv_rank`, `strike_price`, `monthly_ret`
- **Constants:** `UPPER_CASE` — `RISK_FREE_RATE`, `DEFAULT_TICKERS`
- **Classes:** `PascalCase` — `CSPExecutor`

#### Error Handling

- Per-ticker `try/except` blocks — one ticker failure doesn't crash the run
- Stderr for diagnostic messages
- Graceful degradation: missing data defaults to neutral values (e.g., `None` IV rank skips IVR filter)

#### Data Validation Patterns

```python
if strike >= price:           # Skip ITM puts
if bid <= 0:                  # Skip invalid prices
if (ask - bid) / mid > 0.15: # Skip wide bid-ask spreads
```

#### State Management

Functional/stateless design. Two local accumulators:
- `all_results = []` — aggregates across tickers
- `fund_data = {}` — fundamentals cache within a single run

No persistent state, no database, no config files.

---

## 🔧 Development Guide

### Important Notes for Contributors

- **No `.env` file** — all configuration is via CLI flags. IB connection defaults to `127.0.0.1:7497`.
- **Yahoo Finance is the sole data source** for screening — no API keys needed, but rate limits apply. The `yfinance` library handles all HTTP calls internally.
- **The C++ and Python implementations are independent** — changes to one do not automatically reflect in the other. Keep them in sync if modifying shared logic.
- **Dry-run is the default** in executor.py — never remove this safety default.
- **`warnings.filterwarnings("ignore")`** is set at module level in screener.py to suppress yfinance deprecation warnings.

### Testing

**No formal test suite exists.** There is no pytest/unittest configuration.

When adding tests:
- Greek calculations (`bs_d1_d2`, `bs_put_greeks`) are pure functions and straightforward to unit test
- `compute_quality_score()` is also pure and testable
- Screening functions depend on live Yahoo Finance data — mock `yfinance` calls for deterministic tests
- Executor has built-in dry-run mode for safety

### Known Issues & Attention Items

1. **No test suite** — multiple screener changes have been committed with zero test coverage. If the project grows, this is the highest-risk gap.
2. **C++ implementation** — several Python-side changes (Mak strategy mode, spread enhancements) have no corresponding commits to `screener.cpp`/`executor.cpp`, meaning the two implementations are now out of sync.
3. **No CI/CD pipeline** — no GitHub Actions, no linting config, no type checking config.

### Roadmap

#### Planned Features
- [ ] **Profit tracker:** Import trades, track realized gains
- [ ] **Rolling calculator:** Suggest roll parameters (strike, exp, credit)
- [ ] **Earnings calendar:** Auto-filter positions with earnings
- [ ] **Portfolio correlations:** Warn if too concentrated
- [ ] **Morning mode:** Live IV updates during opening hour
- [ ] **Backtesting:** Historical performance of strategy
- [ ] **Test suite:** pytest coverage for core functions

#### Contributions
Pull requests welcome! Areas of interest:
- Additional screener modes (iron condors, call spreads)
- Live market data integration
- Portfolio management features
- Performance analytics
- Test coverage

---

## 📚 Additional Documentation

### Included Files

1. **MAK-ANALYSIS.md** — 14,000-word comprehensive analysis of Coach Mak's strategy
2. **MAK-STRATEGY.md** — Quick reference guide with trade management rules
3. **EXECUTIVE-SUMMARY.md** — Strategy overview & implementation guide
4. **mak-watchlist.txt** — Mak's observed tickers

### External Resources
- Coach Mak's X: [@wealthcoachmak](https://x.com/wealthcoachmak)
- Mak's Opt-In Page: [sellingoptions.carrd.co](https://sellingoptions.carrd.co)
- Options basics: [The Options Playbook](https://www.optionsplaybook.com/)

### Integration with Other Projects

This screener works alongside:

- **[Trading Tracker](https://github.com/robinlwong/trading-tracker)** - Log and track Mak's trades
- **[Polymarket Polygun](https://github.com/robinlwong/polymarket-polygun)** - Automated prediction market trading

Together, these tools form a comprehensive options trading research and execution stack.

---

## 🎯 Quick Command Reference

```bash
# Mak's strategy (recommended starting point)
python3 screener.py --mak-strategy --top 15

# With fundamentals
python3 screener.py --mak-strategy --fundamentals

# AI/tech focus
python3 screener.py --ai-stocks --mak-strategy

# Custom tickers
python3 screener.py -t TSLA PLTR NVDA --mak-strategy

# Spreads mode (defined risk)
python3 screener.py --spreads --mak-strategy

# Quality filter
python3 screener.py --mak-strategy --min-margin 40 --min-fcf-yield 2

# Full detail
python3 screener.py --mak-strategy --fundamentals --verbose --top 20
```

**Start here:** `python3 screener.py --mak-strategy --fundamentals --top 15`

---

## ⚠️ Disclaimer

This tool is for **educational and research purposes only**. It does not constitute financial advice. Options trading involves significant risk of loss, including the risk of losing more than your initial investment.

**Coach Mak's trades** analyzed here are for educational purposes and may not reflect his complete strategy or current positions. Always do your own research and consider consulting a financial advisor before trading.

**Past performance does not guarantee future results.** The 5-10% monthly target is aspirational and depends on market conditions, discipline, and risk management.

---

## 📄 License

MIT License — see LICENSE file for details.

---

## 🙏 Acknowledgments

**Coach Mak (@wealthcoachmak)** for sharing his trades publicly and providing educational content on premium selling strategies. This screener is built to help others learn and implement similar methodologies.

**The options trading community** for open-source tools and educational resources.

---

**Version:** 2.2 (Coach Mak Edition)  
**Last Updated:** 2026-02-18  
**Maintainer:** Robin Wong (robinlwong)  
**Documentation:** Consolidated by Jarvis ⚡

---

Happy premium selling! 💰⚡
