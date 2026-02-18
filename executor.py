#!/usr/bin/env python3
"""
CSP Trade Executor
Executes cash-secured put orders via Interactive Brokers API.
Requires: pip install ib_insync

Usage:
    python executor.py --symbol NVDA --strike 120 --expiry 2026-03-21 --quantity 1
    python executor.py --from-json screened_trades.json
"""

import argparse
import json
import logging
from datetime import datetime
from typing import Optional

from ib_insync import IB, Option, LimitOrder, MarketOrder, util

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


class CSPExecutor:
    """Execute Cash-Secured Put trades via Interactive Brokers."""
    
    def __init__(self, host: str = '127.0.0.1', port: int = 7497, client_id: int = 1):
        """
        Initialize the executor.
        
        Args:
            host: TWS/Gateway host (default localhost)
            port: 7497 for TWS paper, 7496 for live, 4001/4002 for Gateway
            client_id: Unique client ID for this connection
        """
        self.ib = IB()
        self.host = host
        self.port = port
        self.client_id = client_id
        self.connected = False
    
    def connect(self) -> bool:
        """Connect to Interactive Brokers TWS/Gateway."""
        try:
            self.ib.connect(self.host, self.port, clientId=self.client_id)
            self.connected = True
            logger.info(f"Connected to IB at {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from IB."""
        if self.connected:
            self.ib.disconnect()
            self.connected = False
            logger.info("Disconnected from IB")
    
    def get_account_summary(self) -> dict:
        """Get account summary including buying power."""
        summary = {}
        for item in self.ib.accountSummary():
            if item.tag in ['NetLiquidation', 'BuyingPower', 'AvailableFunds', 'TotalCashValue']:
                summary[item.tag] = float(item.value)
        return summary
    
    def create_put_contract(
        self,
        symbol: str,
        strike: float,
        expiry: str,
        exchange: str = 'SMART',
        currency: str = 'USD'
    ) -> Option:
        """
        Create an option contract for a put.
        
        Args:
            symbol: Underlying symbol (e.g., 'NVDA')
            strike: Strike price
            expiry: Expiration date as 'YYYY-MM-DD' or 'YYYYMMDD'
            exchange: Exchange (default SMART for best execution)
            currency: Currency (default USD)
        
        Returns:
            Option contract object
        """
        # Format expiry as YYYYMMDD
        if '-' in expiry:
            expiry = expiry.replace('-', '')
        
        contract = Option(
            symbol=symbol,
            lastTradeDateOrContractMonth=expiry,
            strike=strike,
            right='P',  # Put
            exchange=exchange,
            currency=currency
        )
        
        # Qualify the contract to get full details
        qualified = self.ib.qualifyContracts(contract)
        if qualified:
            return qualified[0]
        return contract
    
    def get_option_price(self, contract: Option) -> dict:
        """Get current bid/ask/mid for an option."""
        self.ib.reqMktData(contract, '', False, False)
        self.ib.sleep(2)  # Wait for data
        
        ticker = self.ib.ticker(contract)
        return {
            'bid': ticker.bid if ticker.bid > 0 else None,
            'ask': ticker.ask if ticker.ask > 0 else None,
            'mid': (ticker.bid + ticker.ask) / 2 if ticker.bid > 0 and ticker.ask > 0 else None,
            'last': ticker.last if ticker.last > 0 else None
        }
    
    def sell_put(
        self,
        symbol: str,
        strike: float,
        expiry: str,
        quantity: int = 1,
        limit_price: Optional[float] = None,
        dry_run: bool = True
    ) -> dict:
        """
        Sell to open a cash-secured put.
        
        Args:
            symbol: Underlying symbol
            strike: Strike price
            expiry: Expiration date
            quantity: Number of contracts (default 1)
            limit_price: Limit price (None for market order)
            dry_run: If True, don't actually place the order
        
        Returns:
            Order result dictionary
        """
        contract = self.create_put_contract(symbol, strike, expiry)
        
        # Get current pricing
        prices = self.get_option_price(contract)
        logger.info(f"Current prices for {symbol} ${strike} Put {expiry}: {prices}")
        
        # Create order (sell to open = negative quantity)
        if limit_price:
            order = LimitOrder('SELL', quantity, limit_price)
        else:
            order = MarketOrder('SELL', quantity)
        
        # Calculate collateral required
        collateral = strike * 100 * quantity
        premium = (prices['mid'] or prices['bid'] or 0) * 100 * quantity
        
        result = {
            'symbol': symbol,
            'strike': strike,
            'expiry': expiry,
            'quantity': quantity,
            'order_type': 'LIMIT' if limit_price else 'MARKET',
            'limit_price': limit_price,
            'current_bid': prices['bid'],
            'current_ask': prices['ask'],
            'current_mid': prices['mid'],
            'estimated_premium': premium,
            'collateral_required': collateral,
            'dry_run': dry_run
        }
        
        if dry_run:
            logger.info(f"[DRY RUN] Would sell {quantity}x {symbol} ${strike} Put @ {limit_price or 'MKT'}")
            result['status'] = 'DRY_RUN'
        else:
            trade = self.ib.placeOrder(contract, order)
            self.ib.sleep(1)
            result['status'] = trade.orderStatus.status
            result['order_id'] = trade.order.orderId
            logger.info(f"Order placed: {trade.orderStatus.status}")
        
        return result
    
    def execute_from_screener(
        self,
        trades: list,
        max_positions: int = 5,
        max_collateral: float = 50000,
        dry_run: bool = True
    ) -> list:
        """
        Execute multiple trades from screener output.
        
        Args:
            trades: List of trade dicts with 'ticker', 'strike', 'exp' keys
            max_positions: Maximum number of positions to open
            max_collateral: Maximum total collateral to use
            dry_run: If True, don't actually place orders
        
        Returns:
            List of execution results
        """
        results = []
        total_collateral = 0
        
        for i, trade in enumerate(trades[:max_positions]):
            collateral_needed = trade['strike'] * 100
            
            if total_collateral + collateral_needed > max_collateral:
                logger.info(f"Skipping {trade['ticker']} - would exceed max collateral")
                continue
            
            result = self.sell_put(
                symbol=trade['ticker'],
                strike=trade['strike'],
                expiry=trade['exp'],
                quantity=1,
                limit_price=trade.get('mid') or trade.get('bid'),
                dry_run=dry_run
            )
            
            results.append(result)
            total_collateral += collateral_needed
        
        return results


def main():
    parser = argparse.ArgumentParser(description='Execute CSP trades via Interactive Brokers')
    
    # Connection settings
    parser.add_argument('--host', default='127.0.0.1', help='TWS/Gateway host')
    parser.add_argument('--port', type=int, default=7497, help='Port (7497=TWS paper, 7496=TWS live)')
    parser.add_argument('--client-id', type=int, default=1, help='Client ID')
    
    # Single trade mode
    parser.add_argument('--symbol', '-s', help='Underlying symbol')
    parser.add_argument('--strike', '-k', type=float, help='Strike price')
    parser.add_argument('--expiry', '-e', help='Expiration date (YYYY-MM-DD)')
    parser.add_argument('--quantity', '-q', type=int, default=1, help='Number of contracts')
    parser.add_argument('--limit', '-l', type=float, help='Limit price (omit for market)')
    
    # Batch mode
    parser.add_argument('--from-json', help='Execute trades from JSON file')
    parser.add_argument('--max-positions', type=int, default=5, help='Max positions to open')
    parser.add_argument('--max-collateral', type=float, default=50000, help='Max collateral')
    
    # Safety
    parser.add_argument('--live', action='store_true', help='Actually execute (default is dry run)')
    
    args = parser.parse_args()
    dry_run = not args.live
    
    executor = CSPExecutor(host=args.host, port=args.port, client_id=args.client_id)
    
    if not executor.connect():
        print("Failed to connect to IB. Make sure TWS/Gateway is running.")
        return 1
    
    try:
        # Show account info
        summary = executor.get_account_summary()
        print(f"\n📊 Account Summary:")
        for k, v in summary.items():
            print(f"   {k}: ${v:,.2f}")
        print()
        
        if args.from_json:
            # Batch mode
            with open(args.from_json) as f:
                trades = json.load(f)
            
            results = executor.execute_from_screener(
                trades,
                max_positions=args.max_positions,
                max_collateral=args.max_collateral,
                dry_run=dry_run
            )
            
            print(f"\n📋 Execution Results ({len(results)} trades):")
            for r in results:
                status = "✅" if r['status'] in ['Filled', 'DRY_RUN'] else "⏳"
                print(f"   {status} {r['symbol']} ${r['strike']} Put - {r['status']}")
        
        elif args.symbol and args.strike and args.expiry:
            # Single trade mode
            result = executor.sell_put(
                symbol=args.symbol,
                strike=args.strike,
                expiry=args.expiry,
                quantity=args.quantity,
                limit_price=args.limit,
                dry_run=dry_run
            )
            
            print(f"\n📋 Trade Result:")
            print(f"   Symbol: {result['symbol']}")
            print(f"   Strike: ${result['strike']}")
            print(f"   Expiry: {result['expiry']}")
            print(f"   Quantity: {result['quantity']}")
            print(f"   Bid/Ask: ${result['current_bid']}/{result['current_ask']}")
            print(f"   Est. Premium: ${result['estimated_premium']:,.2f}")
            print(f"   Collateral: ${result['collateral_required']:,.2f}")
            print(f"   Status: {result['status']}")
        
        else:
            parser.print_help()
    
    finally:
        executor.disconnect()
    
    return 0


if __name__ == '__main__':
    exit(main())
