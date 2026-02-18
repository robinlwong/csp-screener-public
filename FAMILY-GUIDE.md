# Cash-Secured Puts - Family Guide

**A Simple Way to Earn 5-10% Monthly Income from Stocks You Already Like**

---

## 🤔 What Is This?

Imagine you want to buy Apple stock, but you think it's a bit expensive right now. What if someone paid YOU to agree to buy it at a lower price?

That's exactly what cash-secured puts (CSPs) do.

**In Plain English:**
- You pick a stock you'd be happy to own (like Tesla, Amazon, Apple)
- You pick a "buy price" below today's price (like $10-20 cheaper)
- Someone pays you money TODAY for your promise to buy at that price
- **80% of the time:** The stock stays above your price, you keep the money, game over
- **20% of the time:** The stock drops, you buy it at your discounted price (and you already got paid!)

**The Strategy:** Coach Mak (@wealthcoachmak) makes 5-10% monthly doing this. We built a tool to find these opportunities automatically.

---

## 💰 Real Example: Google (GOOGL) Trade

**What Happened:**
- Date: February 5, 2026
- Google stock was trading around $310
- Coach Mak sold a cash-secured put at $305 (5% below current price)
- He collected **$181 premium** ($1.81 per share × 100 shares)
- Capital required: $30,500 (to buy 100 shares if assigned)

**The Outcome (Next Day!):**
- Google stayed above $305 (didn't drop)
- He closed the position by buying back the put for only $22
- **Profit: $159 in 24 hours** (88% of max profit)
- **Return: 0.52% in 1 day** → ~15% monthly if repeated

**The Lesson:**
He could have held for 100% profit, but **capital velocity matters**. Close winners at 80-90%, redeploy the money into new trades. That's how you hit 5-10% monthly.

---

## 🎯 How It Works (The 5-Step Process)

### Step 1: Pick Stocks You'd Actually Want to Own
**Good picks:**
- Companies you understand (Tesla, Apple, Amazon)
- Quality businesses (strong profits, growing)
- Stocks you'd be happy to hold for years

**Bad picks:**
- Penny stocks or sketchy companies
- Stocks you don't understand
- Companies with bad fundamentals

### Step 2: Use the Screener Tool to Find Opportunities

**What the tool does:**
- Scans 100+ stocks every day
- Finds puts that are:
  - **20-35% chance of being assigned** (safe distance from current price)
  - **High premium** (expensive options = more income)
  - **20-50 days until expiration** (sweet spot for time decay)
  - **1%+ monthly return** minimum

**How to use it:**
```bash
# Run the screener (Mak Strategy Mode)
python3 screener.py --mak-strategy --top 15
```

**What you see:**
A table with the best opportunities, showing:
- **Ticker** - Stock symbol
- **Strike** - The price you'd buy at
- **Premium** - Money you collect TODAY
- **Mo.Ret%** - Monthly return percentage
- **OTM%** - How far below current price (safety cushion)
- **Quality** - Fundamental score (0-100)

### Step 3: Pick Your Trade

**What to look for:**
- ⭐⭐⭐ Star rating (top opportunities)
- 1.5%+ monthly return
- Quality score >60 (good company fundamentals)
- Stock you'd be happy to own

**Example from screener output:**
```
Ticker: TSLA
Strike: $345
Premium: $565
Mo.Ret: 1.64%
OTM%: 15%
Rating: ★★★
```

Translation: "Sell Tesla $345 put, collect $565, Tesla is 15% above your buy price, earn 1.64% this month"

### Step 4: Execute the Trade

**Through your broker (Interactive Brokers, TD Ameritrade, etc.):**
1. Select "Sell to Open"
2. Choose "PUT" option
3. Enter strike price ($345)
4. Enter expiration date
5. Confirm you have enough cash ($34,500 for Tesla example)
6. Place order at "mid price" (between bid and ask)

**Capital Required:**
Strike × 100 shares = Capital needed in cash

**Example:** $345 strike × 100 = $34,500 required

### Step 5: Manage the Position

**If Stock Stays Above Strike (80% of cases):**
- Close at 80-90% profit (don't wait for 100%)
- **Rule:** When you can buy back for $0.20-0.50, close it
- Redeploy capital into new trade

**If Stock Drops Below Strike (20% of cases):**
- **Option A:** Accept assignment, own the stock at discount, sell covered calls
- **Option B:** "Roll" the put (extend expiration, collect more premium)
- **Never panic close** - you wanted to own this stock anyway!

---

## 📊 How to Hit 5-10% Monthly (The Math)

**Target:** 5-10% monthly portfolio return

**Method:** Multiple small positions (1-2% each)

**Example Portfolio ($100,000):**
- 10 positions × $10,000 each = $100,000 deployed
- Average 1.5% monthly per position = $150/position
- Total monthly income: 10 × $150 = **$1,500 (1.5% portfolio)**

**Scaling to 10%:**
1. **More positions:** 15-20 CSPs instead of 10
2. **Higher returns:** Target 2-3% per position (higher IV markets)
3. **Quick turnaround:** Close at 80-90% profit, redeploy 2-3x per month
4. **Compounding:** Reinvest profits into new positions

**Reality Check:**
- Not all positions win (expect 70-80% win rate)
- Some need to be rolled (extend time)
- Occasional assignments (own stock, sell covered calls)
- Coach Mak averages 5-10% monthly doing this consistently

---

## ⚙️ Coach Mak's Rules (Learn from the Best)

### Entry Rules
- ✅ **IV Rank > 50** - Only trade when options are expensive
- ✅ **Delta 0.20-0.35** - Don't get too close to current price
- ✅ **DTE 20-50 days** - Sweet spot for theta decay
- ✅ **Return > 1%** monthly minimum
- ✅ **No earnings before expiration** - Avoid binary events
- ✅ **Quality fundamentals** - Only stocks worth owning

### Exit Rules (Winners)
- 🎯 **Target: 80-90% profit** - Don't hold for 100%
- 🎯 **Time: 1-7 days** if hit
- 🎯 **Example:** Sold for $1.81, buy back at $0.22 (88% profit) ✅
- 🎯 **Don't:** Hold for $0.01 buyback (diminishing returns)

### Exit Rules (Losers)
- 🔄 **Roll:** Extend expiration, collect more premium
- 🔄 **Adjust strike:** Move lower if conviction remains
- 🔄 **Accept assignment:** Own stock, sell covered calls
- ❌ **Don't:** Panic close at max loss (defeats the strategy)

### Position Sizing
- 📊 **Start small:** 5-10% of portfolio per position
- 📊 **Layer:** Add to winners (2-3 contracts on same ticker)
- 📊 **Diversify:** 10-15 positions across sectors
- 📊 **Allocate:** More capital to higher-vol names (TSLA $565 vs PLTR $141)

---

## 🛡️ Risk Management (Stay Safe!)

### Portfolio Level
- ⚠️ **Max 10-15 positions** at once (avoid over-concentration)
- ⚠️ **Sector limit:** No more than 40% in one sector
- ⚠️ **Correlation:** Don't have all tech CSPs (they move together)
- ⚠️ **Hedge:** Long shares + LEAPS can offset short put risk

### Position Level
- ⚠️ **Delta 0.20-0.35:** Avoid ATM strikes (gamma explosion)
- ⚠️ **Quality stocks:** Only sell puts on stocks you'd own
- ⚠️ **Liquidity:** Bid-ask spread <15% (can exit easily)
- ⚠️ **Earnings:** Check calendar, avoid binary events

### Psychology
- ✅ **No greed:** Take 80-90%, don't hold for 100%
- ✅ **No fear:** Accept assignment risk (it's cash-secured)
- ✅ **Patience:** Roll losers, collect more premium
- ✅ **Discipline:** Follow the rules, don't chase every trade

---

## 🚨 What Can Go Wrong? (Honest Risks)

### Risk 1: Stock Crashes
**Scenario:** You sell Tesla $345 put, Tesla drops to $250

**Impact:**
- You're assigned 100 shares at $345 = $34,500
- Current value: $25,000
- Unrealized loss: $9,500
- But you collected $565 premium (reduces loss to ~$9,000)

**How to handle:**
- Accept assignment, hold stock long-term
- Sell covered calls to collect more premium
- Tesla is quality company, likely recovers over time

### Risk 2: Black Swan Event
**Scenario:** Market crashes 20% in a week

**Impact:**
- Multiple positions assigned at once
- Large unrealized losses
- Capital tied up

**How to prevent:**
- Never use margin (only cash-secured)
- Keep 20-30% cash reserve
- Diversify across sectors
- Only pick stocks you'd hold through a crash

### Risk 3: Opportunity Cost
**Scenario:** Stock rockets up, you miss gains

**Impact:**
- You sold Tesla $345 put, Tesla jumps to $400
- You only earned $565 premium
- If you'd bought shares, you'd be up $5,500

**Reality:**
- This is the tradeoff - you trade upside for consistent income
- CSP strategy optimizes for **income**, not **capital gains**

---

## 📚 What the Screener Tool Shows You

### Main Table Columns Explained

| Column | What It Means | What to Look For |
|--------|---------------|------------------|
| **Ticker** | Stock symbol | Stocks you recognize and like |
| **Strike** | Price you'd buy at | 10-20% below current price |
| **Premium** | Money you collect TODAY | Higher = better |
| **Mo.Ret%** | Monthly return percentage | 1.5%+ ideal |
| **OTM%** | Safety cushion | 15-25% ideal |
| **Delta** | Rough probability of assignment | 0.20-0.35 range |
| **IVR** | IV Rank (0-100) | 50+ preferred |
| **Qlty** | Fundamental score | 60+ preferred |
| **Rating** | ★★★ / ★★ / ★ | Stars = better opportunities |

### Star Ratings

- **★★★** Top 20% of opportunities (best composite score)
- **★★** Strong opportunities (solid picks)
- **★** Good opportunities (still worth considering)

---

## 🎓 Learning Resources

### Coach Mak's Trading
- **X (Twitter):** [@wealthcoachmak](https://x.com/wealthcoachmak)
- **Opt-In Page:** [sellingoptions.carrd.co](https://sellingoptions.carrd.co)
- **Strategy:** 5-10% monthly via disciplined CSP selling

### Options Education
- **The Options Playbook:** [optionsplaybook.com](https://www.optionsplaybook.com/)
- **Investopedia:** [Cash-Secured Put](https://www.investopedia.com/terms/c/cash-secured-put.asp)
- **TastyTrade:** [tastytrade.com](https://www.tastytrade.com/) (education + platform)

### Our Tools
- **CSP Screener:** Finds opportunities automatically (this tool!)
- **Trading Tracker:** Logs and analyzes your trades ([GitHub](https://github.com/robinlwong/trading-tracker))

---

## 🚀 Getting Started Checklist

### Before Your First Trade
- [ ] Open brokerage account (Interactive Brokers, TD Ameritrade, etc.)
- [ ] Get approved for options trading (Level 1 or 2)
- [ ] Deposit capital ($10k+ recommended to start)
- [ ] Pick 5-10 stocks you'd be happy to own
- [ ] Run the screener tool to see opportunities
- [ ] Paper trade for 1-2 weeks (practice mode)

### Your First Real Trade
- [ ] Start small (1 contract = 100 shares = $5k-$15k capital)
- [ ] Pick a ★★★ rated opportunity
- [ ] Stock you know and trust
- [ ] Set calendar reminder for expiration date
- [ ] Log the trade in a spreadsheet
- [ ] Set alert for 80% profit (for early close)

### Monthly Routine
- [ ] Run screener 2-3x per week
- [ ] Close winners at 80-90% profit
- [ ] Roll or accept assignments on losers
- [ ] Calculate monthly return
- [ ] Review what worked / what didn't
- [ ] Adjust position sizing based on results

---

## ❓ Frequently Asked Questions

### Q: How much money do I need to start?
**A:** $10,000 minimum. This lets you do 1-2 positions safely. $50,000+ is better for proper diversification (5-10 positions).

### Q: What if I don't have that much capital?
**A:** Use **put credit spreads** instead (defined risk, less capital). The tool has a `--spreads` mode for this.

### Q: How much time does this take?
**A:** 1-2 hours per week once you're set up. Run screener, pick trades, manage positions. Not day trading.

### Q: What if the stock crashes?
**A:** You own it at your chosen price. Hold it, sell covered calls to collect more premium. The CSP strategy assumes you WANT to own these stocks.

### Q: Is this gambling?
**A:** No - you're selling insurance on stocks you'd buy anyway. 80% of the time you keep the premium. The other 20%, you buy a stock you wanted at a discount.

### Q: What's the worst that can happen?
**A:** Stock goes to zero (company bankrupt). You lose 100% of capital for that position. **That's why you only pick quality companies.**

### Q: Can I lose more than I put in?
**A:** No - it's "cash secured" meaning you have the cash set aside. No margin, no leverage.

### Q: How is this different from buying stocks?
**A:** You're collecting income while waiting to buy. If the stock never drops to your price, you just keep the income and move on.

---

## 📝 Sample Trade Log (Track Your Progress)

| Date | Ticker | Strike | Premium | Capital | Status | Profit | Return | Notes |
|------|--------|--------|---------|---------|--------|--------|--------|-------|
| 2/5/26 | GOOGL | $305 | $181 | $30,500 | Closed | $159 | 0.52% | Closed next day at 88% profit |
| 2/5/26 | TSLA | $345 | $565 | $34,500 | Open | - | - | 29 DTE, watching |
| 2/5/26 | PLTR | $100 | $141 | $10,000 | Open | - | - | 29 DTE, same exp as TSLA |

**Monthly Summary Example:**
- Total Capital Deployed: $75,000
- Closed Winners: 2 trades, +$450 profit
- Open Positions: 8 trades
- Monthly Return to Date: 0.6%
- Target: 5-10% by month end

---

## 🎯 Next Steps

1. **Read the full technical README** at [GitHub](https://github.com/robinlwong/csp-screener) (if you want the deep details)
2. **Open a brokerage account** and get options approval
3. **Run the screener tool** to see what opportunities look like
4. **Paper trade for 1-2 weeks** to get comfortable
5. **Start with 1 contract** on a stock you love
6. **Track everything** in a spreadsheet
7. **Join Coach Mak's community** for ongoing education

---

**Questions?** Reach out to Robin - happy to walk you through your first trade!

---

**Disclaimer:** This is educational content, not financial advice. Options trading involves risk of loss. Only invest capital you can afford to lose. Past performance (Coach Mak's results) does not guarantee future results. Consult a financial advisor before trading.

---

**Created by:** Robin Wong & Jarvis  
**Last Updated:** 2026-02-18  
**For:** Family & Friends Learning CSP Strategy
