# Mak's Trading Strategy Documentation

**Source:** @wealthcoachmak on X  
**Reference:** sellingoptions.carrd.co

---

## Core Strategy: Covered Calls & Cash-Secured Puts

### Philosophy
- Sell options to collect premium income
- Use CSPs to acquire stocks at discounts
- Use Covered Calls for income on existing shares
- Mix defined-risk spreads (PCS) with naked positions

---

## Strategy Breakdown

### 1. Cash-Secured Puts (CSP)
**Purpose:** Acquire quality stocks at a discount while earning premium

**Tickers actively used (Feb 2026):**
- TSLA, PLTR, AMZN, SOFI, HOOD, UBER

**Example (Feb 5):**
- PLTR $100 strike, exp 3/6/26, $1.41 premium

**Logic:**
- Sell puts on stocks you want to own
- If assigned → you bought at strike minus premium (discount)
- If expires worthless → keep premium, repeat

---

### 2. Put Credit Spreads (PCS)
**Purpose:** Defined-risk alternative to CSPs

**Tickers used (Feb 2026):**
- META, CRM, GOOGL (closed)

**Why use PCS vs CSP:**
- Less capital required
- Defined max loss (spread width)
- Still bullish/neutral bias
- Used on high-priced stocks where CSP capital requirement is high

---

### 3. Covered Calls (CC)
**Purpose:** Generate income on long stock positions

**Example (Feb 5):**
- AMZN CC (selling calls on 10 shares purchased at $222.43)

**Logic:**
- Already own shares (or assigned from CSP)
- Sell calls above current price
- If called away → profit from shares + premium
- If expires → keep shares + premium, repeat

---

### 4. Multi-Leg Strategies
**Broken Wing Butterfly (META, Jan 28):**
- Advanced defined-risk strategy
- Asymmetric risk/reward profile
- Used occasionally on specific setups

---

## Rolling Strategy

**Evidence:** XYZ CSP rolled (Feb 5)

**When to roll:**
- Position going against you (stock dropping)
- Want to avoid assignment
- Extend time to collect more premium
- Move strike lower for better defense

---

## Performance Targets

**Stated by Mak:** "Or 5-10% a month?" 🤷

This confirms his target monthly return range:
- **Conservative:** 5% per month = 60% annualized
- **Aggressive:** 10% per month = 120% annualized (compounded: ~213% annually)

**Context:** This is consistent with active premium selling strategies. The wide range (5-10%) reflects:
- Market volatility (IV levels)
- Opportunity availability
- Risk management (not chasing every trade)

---

## Recent Activity Patterns (Feb 2026)

### High-Activity Tickers
1. **TSLA** - Multiple CSP positions
2. **PLTR** - CSP + shares purchased
3. **AMZN** - CSP + CC + shares
4. **META** - Multiple strategies (BWB + PCS)

### Stock Accumulation
Purchased shares on Feb 5:
- AMD: 10 @ $194.18
- AMZN: 10 @ $222.43
- PLTR: 20 @ $129.78

**Context:** Down $165K on long positions (shares/LEAPS) in AMZN, TSLA, META. These purchases may be **buying the dip** on quality names.

---

## Performance Context (Feb 2026)

**Past month:** -$165K (-11.70%)

**Loss sources:**
- Share prices declining (AMZN, TSLA, META)
- LEAPS positions underwater

**CSP performance:** Not explicitly mentioned → likely profitable or break-even

**Key insight:** Losses in **long directional bets**, not premium selling. The CSP strategy appears to be working as designed.

---

## Stock Selection Criteria (Inferred)

From observed trades:
- **Large-cap tech/growth** (AMZN, META, TSLA, GOOGL, CRM)
- **High-volatility names** (TSLA, PLTR, SOFI) = fatter premiums
- **Quality fundamentals** (stocks worth owning if assigned)
- **Actively traded** (tight bid-ask spreads)

---

## CSP Screener Logic to Implement

Based on Mak's strategy, our screener should prioritize:

1. **High IV Rank** - Options are expensive relative to history
2. **Strong fundamentals** - Companies you'd want to own
3. **High theta decay** - More daily income
4. **Moderate delta** (0.20-0.35) - OTM but not too far
5. **Liquid options** - Tight bid-ask spreads
6. **No earnings before expiration** - Avoid binary risk
7. **DTE 20-50 days** - Sweet spot for theta decay

**Additional filters:**
- Quality score (margins, FCF, revenue growth)
- IV Rank > 50 (options relatively expensive)
- Theta/premium ratio (maximize daily income)
- Gamma risk penalty (avoid delta explosion near ATM)

---

## Trade Management (Observed)

### Closing Winners: Quick Profit-Taking

**GOOGL $305 CSP (Feb 5-6):**
- **Opened:** 2/5 @ $1.81 premium ($181)
- **Closed:** 2/6 @ $0.22 buyback ($22)
- **Profit:** +$159 (88% gain)
- **Duration:** 1 day 🔥

**Key lesson:** Take profits aggressively when the market gives them. Closed at 88% max profit in 1 day rather than holding for the remaining $22. This is **professional profit management** — lock in wins, free up capital, move to next trade.

**GOOGL PCS:** Also closed Feb 5 (details pending)

---

### Rolling Losers

**XYZ CSP rolled Feb 5:**
- Extend time, collect more premium
- Avoid assignment if stock outlook changed
- Convert losing position into potential winner

---

### Adding to Winners

**TSLA CSP opened twice (Jan 28 + Feb 5):**
- Layer into positions
- Scale in when thesis is strong
- Multiple shots at same target

---

### Profit-Taking Philosophy (Inferred)

Based on GOOGL closure:
- **Take 80-90% profits quickly** (1-2 days if available)
- Don't hold for last 10-20% if you can lock in the win
- Free up capital faster = more opportunities
- Compound wins by redeploying capital

**Math:** If you can make 88% in 1 day, that's better than 100% in 30 days (annualized return is massively higher).

---

*Last updated: 2026-02-06 by Jarvis ⚡*
