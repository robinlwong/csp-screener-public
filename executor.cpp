/**
 * CSP Trade Executor - C++ Version
 * Executes cash-secured put orders via Interactive Brokers TWS API.
 * 
 * Build: g++ -std=c++17 -o executor executor.cpp -I/path/to/twsapi -L/path/to/twsapi -lTwsApi -lpthread
 * 
 * Requires: IB TWS API (https://interactivebrokers.github.io/)
 */

#include <iostream>
#include <string>
#include <memory>
#include <thread>
#include <chrono>
#include <mutex>
#include <condition_variable>
#include <map>
#include <vector>
#include <cmath>

// IB TWS API headers (adjust path as needed)
// #include "EWrapper.h"
// #include "EReaderOSSignal.h"
// #include "EClientSocket.h"
// #include "Contract.h"
// #include "Order.h"

// For standalone compilation demo, we'll define minimal structures
// In production, use the actual IB TWS API headers

namespace ib {
    struct Contract {
        std::string symbol;
        std::string secType = "OPT";
        std::string exchange = "SMART";
        std::string currency = "USD";
        std::string lastTradeDateOrContractMonth;
        double strike = 0.0;
        std::string right;  // "P" for put, "C" for call
    };

    struct Order {
        int orderId = 0;
        std::string action;     // "BUY" or "SELL"
        double totalQuantity = 0;
        std::string orderType;  // "LMT" or "MKT"
        double lmtPrice = 0.0;
    };

    struct TickPrice {
        double bid = 0.0;
        double ask = 0.0;
        double last = 0.0;
    };
}

/**
 * CSP Executor class for Interactive Brokers
 */
class CSPExecutor {
private:
    std::string host_;
    int port_;
    int clientId_;
    bool connected_ = false;
    int nextOrderId_ = 0;
    
    std::mutex mtx_;
    std::condition_variable cv_;
    std::map<int, ib::TickPrice> prices_;

public:
    CSPExecutor(const std::string& host = "127.0.0.1", 
                int port = 7497, 
                int clientId = 1)
        : host_(host), port_(port), clientId_(clientId) {}
    
    ~CSPExecutor() {
        disconnect();
    }

    /**
     * Connect to TWS/Gateway
     */
    bool connect() {
        std::cout << "[INFO] Connecting to IB at " << host_ << ":" << port_ << std::endl;
        
        // In production: use EClientSocket::eConnect()
        // this->client_->eConnect(host_.c_str(), port_, clientId_);
        
        // Simulated connection for demo
        connected_ = true;
        nextOrderId_ = 1000;
        
        std::cout << "[INFO] Connected successfully" << std::endl;
        return true;
    }

    /**
     * Disconnect from TWS/Gateway
     */
    void disconnect() {
        if (connected_) {
            // In production: client_->eDisconnect();
            connected_ = false;
            std::cout << "[INFO] Disconnected" << std::endl;
        }
    }

    /**
     * Create a put option contract
     */
    ib::Contract createPutContract(const std::string& symbol,
                                    double strike,
                                    const std::string& expiry) {
        ib::Contract contract;
        contract.symbol = symbol;
        contract.secType = "OPT";
        contract.exchange = "SMART";
        contract.currency = "USD";
        contract.strike = strike;
        contract.right = "P";  // Put
        
        // Format expiry: YYYYMMDD
        contract.lastTradeDateOrContractMonth = expiry;
        
        return contract;
    }

    /**
     * Request market data for an option
     */
    ib::TickPrice getOptionPrice(const ib::Contract& contract) {
        ib::TickPrice price;
        
        // In production: use reqMktData() and wait for tickPrice callbacks
        // Simulated prices for demo
        price.bid = 2.50;
        price.ask = 2.60;
        price.last = 2.55;
        
        return price;
    }

    /**
     * Sell to open a cash-secured put
     */
    struct ExecutionResult {
        std::string symbol;
        double strike;
        std::string expiry;
        int quantity;
        std::string orderType;
        double limitPrice;
        double bidPrice;
        double askPrice;
        double estimatedPremium;
        double collateralRequired;
        std::string status;
        int orderId;
        bool dryRun;
    };

    ExecutionResult sellPut(const std::string& symbol,
                            double strike,
                            const std::string& expiry,
                            int quantity = 1,
                            double limitPrice = 0.0,
                            bool dryRun = true) {
        
        ExecutionResult result;
        result.symbol = symbol;
        result.strike = strike;
        result.expiry = expiry;
        result.quantity = quantity;
        result.dryRun = dryRun;
        
        // Create contract
        auto contract = createPutContract(symbol, strike, expiry);
        
        // Get current prices
        auto prices = getOptionPrice(contract);
        result.bidPrice = prices.bid;
        result.askPrice = prices.ask;
        
        // Calculate values
        double midPrice = (prices.bid + prices.ask) / 2.0;
        result.estimatedPremium = midPrice * 100.0 * quantity;
        result.collateralRequired = strike * 100.0 * quantity;
        
        // Create order
        ib::Order order;
        order.action = "SELL";
        order.totalQuantity = quantity;
        
        if (limitPrice > 0) {
            order.orderType = "LMT";
            order.lmtPrice = limitPrice;
            result.orderType = "LIMIT";
            result.limitPrice = limitPrice;
        } else {
            order.orderType = "MKT";
            result.orderType = "MARKET";
            result.limitPrice = 0;
        }
        
        if (dryRun) {
            std::cout << "[DRY RUN] Would sell " << quantity << "x " 
                      << symbol << " $" << strike << " Put @ " 
                      << (limitPrice > 0 ? std::to_string(limitPrice) : "MKT") << std::endl;
            result.status = "DRY_RUN";
            result.orderId = 0;
        } else {
            // In production: placeOrder(contract, order)
            order.orderId = nextOrderId_++;
            result.orderId = order.orderId;
            result.status = "SUBMITTED";
            std::cout << "[LIVE] Order submitted: ID " << order.orderId << std::endl;
        }
        
        return result;
    }

    /**
     * Execute multiple trades from screener output
     */
    struct TradeInput {
        std::string ticker;
        double strike;
        std::string exp;
        double mid;
    };

    std::vector<ExecutionResult> executeFromScreener(
            const std::vector<TradeInput>& trades,
            int maxPositions = 5,
            double maxCollateral = 50000.0,
            bool dryRun = true) {
        
        std::vector<ExecutionResult> results;
        double totalCollateral = 0.0;
        
        for (size_t i = 0; i < trades.size() && (int)results.size() < maxPositions; ++i) {
            const auto& trade = trades[i];
            double collateralNeeded = trade.strike * 100.0;
            
            if (totalCollateral + collateralNeeded > maxCollateral) {
                std::cout << "[INFO] Skipping " << trade.ticker 
                          << " - would exceed max collateral" << std::endl;
                continue;
            }
            
            auto result = sellPut(
                trade.ticker,
                trade.strike,
                trade.exp,
                1,
                trade.mid,
                dryRun
            );
            
            results.push_back(result);
            totalCollateral += collateralNeeded;
        }
        
        return results;
    }
};

/**
 * Print execution result
 */
void printResult(const CSPExecutor::ExecutionResult& r) {
    std::cout << "\n📋 Trade Result:" << std::endl;
    std::cout << "   Symbol: " << r.symbol << std::endl;
    std::cout << "   Strike: $" << r.strike << std::endl;
    std::cout << "   Expiry: " << r.expiry << std::endl;
    std::cout << "   Quantity: " << r.quantity << std::endl;
    std::cout << "   Bid/Ask: $" << r.bidPrice << "/$" << r.askPrice << std::endl;
    std::cout << "   Est. Premium: $" << r.estimatedPremium << std::endl;
    std::cout << "   Collateral: $" << r.collateralRequired << std::endl;
    std::cout << "   Status: " << r.status << std::endl;
}

/**
 * Print usage
 */
void printUsage(const char* progName) {
    std::cout << "CSP Trade Executor - C++ Version\n\n"
              << "Usage:\n"
              << "  " << progName << " --symbol NVDA --strike 120 --expiry 20260321\n"
              << "  " << progName << " --demo\n\n"
              << "Options:\n"
              << "  --host      TWS/Gateway host (default: 127.0.0.1)\n"
              << "  --port      Port (default: 7497 for paper trading)\n"
              << "  --symbol    Underlying symbol\n"
              << "  --strike    Strike price\n"
              << "  --expiry    Expiration date (YYYYMMDD)\n"
              << "  --quantity  Number of contracts (default: 1)\n"
              << "  --limit     Limit price (omit for market order)\n"
              << "  --live      Actually execute (default is dry run)\n"
              << "  --demo      Run demo with sample trades\n";
}

int main(int argc, char* argv[]) {
    std::string host = "127.0.0.1";
    int port = 7497;
    int clientId = 1;
    std::string symbol;
    double strike = 0.0;
    std::string expiry;
    int quantity = 1;
    double limitPrice = 0.0;
    bool dryRun = true;
    bool demo = false;

    // Parse command line arguments
    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        
        if (arg == "--host" && i + 1 < argc) host = argv[++i];
        else if (arg == "--port" && i + 1 < argc) port = std::stoi(argv[++i]);
        else if (arg == "--symbol" && i + 1 < argc) symbol = argv[++i];
        else if (arg == "--strike" && i + 1 < argc) strike = std::stod(argv[++i]);
        else if (arg == "--expiry" && i + 1 < argc) expiry = argv[++i];
        else if (arg == "--quantity" && i + 1 < argc) quantity = std::stoi(argv[++i]);
        else if (arg == "--limit" && i + 1 < argc) limitPrice = std::stod(argv[++i]);
        else if (arg == "--live") dryRun = false;
        else if (arg == "--demo") demo = true;
        else if (arg == "--help" || arg == "-h") {
            printUsage(argv[0]);
            return 0;
        }
    }

    // Create executor
    CSPExecutor executor(host, port, clientId);
    
    if (!executor.connect()) {
        std::cerr << "Failed to connect to IB. Make sure TWS/Gateway is running." << std::endl;
        return 1;
    }

    if (demo) {
        // Demo mode with sample trades
        std::cout << "\n🎯 Running demo with sample trades...\n" << std::endl;
        
        std::vector<CSPExecutor::TradeInput> sampleTrades = {
            {"NVDA", 120.0, "20260321", 3.50},
            {"AMD", 140.0, "20260321", 2.80},
            {"MSFT", 380.0, "20260321", 5.20},
            {"GOOGL", 175.0, "20260321", 4.10},
            {"META", 550.0, "20260321", 8.50}
        };
        
        auto results = executor.executeFromScreener(sampleTrades, 5, 100000.0, dryRun);
        
        std::cout << "\n📊 Execution Summary (" << results.size() << " trades):" << std::endl;
        for (const auto& r : results) {
            std::string status = (r.status == "DRY_RUN" || r.status == "SUBMITTED") ? "✅" : "⏳";
            std::cout << "   " << status << " " << r.symbol 
                      << " $" << r.strike << " Put - " << r.status << std::endl;
        }
    }
    else if (!symbol.empty() && strike > 0 && !expiry.empty()) {
        // Single trade mode
        auto result = executor.sellPut(symbol, strike, expiry, quantity, limitPrice, dryRun);
        printResult(result);
    }
    else {
        printUsage(argv[0]);
    }

    executor.disconnect();
    return 0;
}
