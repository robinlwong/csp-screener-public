/**
 * CSP (Cash-Secured Put) Screener v2.1 - C++ Implementation
 * Screens for optimal cash-secured put and put credit spread opportunities.
 * Full Greeks, fundamental filtering, AI/tech focus, and quality scoring.
 * 
 * Build:
 *   g++ -std=c++17 -O2 -o screener screener.cpp -lcurl -lpthread -lm
 * 
 * Dependencies:
 *   - libcurl (apt install libcurl4-openssl-dev)
 *   - nlohmann/json (header-only, included inline or apt install nlohmann-json3-dev)
 */

#include <iostream>
#include <iomanip>
#include <string>
#include <vector>
#include <map>
#include <cmath>
#include <algorithm>
#include <chrono>
#include <sstream>
#include <optional>
#include <curl/curl.h>

// Inline minimal JSON parser for simplicity (production: use nlohmann/json)
#include <fstream>

// ══════════════════════════════════════════════════════════════════════════════
// Constants and Watchlists
// ══════════════════════════════════════════════════════════════════════════════

const std::vector<std::string> DEFAULT_TICKERS = {
    "SPY", "QQQ", "AAPL", "MSFT", "AMZN", "GOOGL", "NVDA", "AMD",
    "META", "TSLA", "KO", "PEP", "JNJ", "JPM", "BAC"
};

const std::vector<std::string> AI_TECH_TICKERS = {
    // AI Chips & Semiconductors
    "NVDA", "AMD", "TSM", "AVGO", "MRVL", "ARM", "MU", "INTC", "QCOM", "SMCI",
    // AI Software & Cloud
    "MSFT", "GOOGL", "META", "AMZN", "PLTR", "CRM", "SNOW", "AI", "ORCL", "NOW",
    // Datacenter Infrastructure
    "EQIX", "DLR", "VRT", "ANET",
    // High-vol AI plays
    "TSLA",
    // Cybersecurity
    "CRWD", "ZS",
    // Growth / Coach Mak picks
    "RKLB", "NBIS", "GTLB", "UBER"
};

const std::vector<std::string> INCOME_TICKERS = {
    "NVDA", "AMZN", "TSLA", "GOOGL", "AMD", "META",
    "MSFT", "AAPL", "AVGO", "MU", "SMCI", "PLTR"
};

constexpr double RISK_FREE_RATE = 0.045;
constexpr double PI = 3.14159265358979323846;

// ══════════════════════════════════════════════════════════════════════════════
// Math Utilities - Normal Distribution
// ══════════════════════════════════════════════════════════════════════════════

/**
 * Standard normal probability density function (PDF)
 */
double norm_pdf(double x) {
    return std::exp(-0.5 * x * x) / std::sqrt(2.0 * PI);
}

/**
 * Standard normal cumulative distribution function (CDF)
 * Approximation using Abramowitz and Stegun method
 */
double norm_cdf(double x) {
    // Constants for approximation
    const double a1 =  0.254829592;
    const double a2 = -0.284496736;
    const double a3 =  1.421413741;
    const double a4 = -1.453152027;
    const double a5 =  1.061405429;
    const double p  =  0.3275911;

    int sign = (x < 0) ? -1 : 1;
    x = std::abs(x) / std::sqrt(2.0);

    double t = 1.0 / (1.0 + p * x);
    double y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * std::exp(-x * x);

    return 0.5 * (1.0 + sign * y);
}

// ══════════════════════════════════════════════════════════════════════════════
// Black-Scholes Greeks
// ══════════════════════════════════════════════════════════════════════════════

struct Greeks {
    double delta = 0.0;
    double gamma = 0.0;
    double theta = 0.0;  // $/day per contract
    double vega = 0.0;   // $/share per 1% IV
    double rho = 0.0;
};

/**
 * Calculate d1 and d2 for Black-Scholes
 */
std::pair<double, double> bs_d1_d2(double S, double K, double T, double r, double sigma) {
    if (T <= 0 || sigma <= 0) {
        return {0.0, 0.0};
    }
    double sqrt_T = std::sqrt(T);
    double d1 = (std::log(S / K) + (r + 0.5 * sigma * sigma) * T) / (sigma * sqrt_T);
    double d2 = d1 - sigma * sqrt_T;
    return {d1, d2};
}

/**
 * Calculate ALL Greeks for a European put via Black-Scholes
 */
Greeks bs_put_greeks(double S, double K, double T, double r, double sigma) {
    Greeks g;
    
    if (T <= 0 || sigma <= 0) {
        return g;
    }

    auto [d1, d2] = bs_d1_d2(S, K, T, r, sigma);
    double sqrt_T = std::sqrt(T);
    
    double n_d1 = norm_pdf(d1);       // PDF at d1
    double N_neg_d1 = norm_cdf(-d1);  // CDF at -d1
    double N_neg_d2 = norm_cdf(-d2);  // CDF at -d2

    // Delta (put): N(d1) - 1 = -N(-d1)
    g.delta = -N_neg_d1;

    // Gamma: n(d1) / (S * sigma * sqrt(T))
    double denom = S * sigma * sqrt_T;
    g.gamma = (denom > 0) ? n_d1 / denom : 0.0;

    // Theta (put): per-year, then convert to $/day per contract
    double theta_annual = -(S * n_d1 * sigma) / (2 * sqrt_T) 
                         + r * K * std::exp(-r * T) * N_neg_d2;
    double theta_per_day = theta_annual / 365.0;
    g.theta = theta_per_day * 100;  // per contract (100 shares)

    // Vega: S * n(d1) * sqrt(T) / 100 (per 1% IV change)
    g.vega = (S * n_d1 * sqrt_T) / 100.0;

    // Rho (put): -K * T * e^(-rT) * N(-d2) / 100
    g.rho = -K * T * std::exp(-r * T) * N_neg_d2 / 100.0;

    return g;
}

// ══════════════════════════════════════════════════════════════════════════════
// HTTP Client using libcurl
// ══════════════════════════════════════════════════════════════════════════════

static size_t WriteCallback(void* contents, size_t size, size_t nmemb, std::string* s) {
    size_t newLength = size * nmemb;
    s->append((char*)contents, newLength);
    return newLength;
}

std::string http_get(const std::string& url) {
    CURL* curl = curl_easy_init();
    std::string response;
    
    if (curl) {
        curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
        curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, WriteCallback);
        curl_easy_setopt(curl, CURLOPT_WRITEDATA, &response);
        curl_easy_setopt(curl, CURLOPT_USERAGENT, "Mozilla/5.0");
        curl_easy_setopt(curl, CURLOPT_FOLLOWLOCATION, 1L);
        curl_easy_setopt(curl, CURLOPT_TIMEOUT, 30L);
        
        CURLcode res = curl_easy_perform(curl);
        if (res != CURLE_OK) {
            std::cerr << "  ⚠️  HTTP error: " << curl_easy_strerror(res) << std::endl;
        }
        curl_easy_cleanup(curl);
    }
    return response;
}

// ══════════════════════════════════════════════════════════════════════════════
// Simple JSON Parser (minimal implementation)
// For production, use nlohmann/json or rapidjson
// ══════════════════════════════════════════════════════════════════════════════

class JsonValue {
public:
    enum Type { Null, Bool, Number, String, Array, Object };
    Type type = Null;
    
    double num_val = 0.0;
    std::string str_val;
    std::vector<JsonValue> arr_val;
    std::map<std::string, JsonValue> obj_val;
    bool bool_val = false;
    
    JsonValue() : type(Null) {}
    JsonValue(double n) : type(Number), num_val(n) {}
    JsonValue(const std::string& s) : type(String), str_val(s) {}
    JsonValue(bool b) : type(Bool), bool_val(b) {}
    
    bool is_null() const { return type == Null; }
    bool is_number() const { return type == Number; }
    bool is_string() const { return type == String; }
    bool is_array() const { return type == Array; }
    bool is_object() const { return type == Object; }
    
    double as_double(double def = 0.0) const { 
        return type == Number ? num_val : def; 
    }
    std::string as_string(const std::string& def = "") const { 
        return type == String ? str_val : def; 
    }
    
    const JsonValue& operator[](const std::string& key) const {
        static JsonValue null_val;
        if (type == Object) {
            auto it = obj_val.find(key);
            if (it != obj_val.end()) return it->second;
        }
        return null_val;
    }
    
    const JsonValue& operator[](size_t idx) const {
        static JsonValue null_val;
        if (type == Array && idx < arr_val.size()) return arr_val[idx];
        return null_val;
    }
    
    size_t size() const {
        if (type == Array) return arr_val.size();
        if (type == Object) return obj_val.size();
        return 0;
    }
};

// Minimal JSON parser
class JsonParser {
    const std::string& json;
    size_t pos = 0;
    
    void skip_ws() {
        while (pos < json.size() && std::isspace(json[pos])) pos++;
    }
    
    JsonValue parse_string() {
        pos++; // skip opening quote
        std::string s;
        while (pos < json.size() && json[pos] != '"') {
            if (json[pos] == '\\' && pos + 1 < json.size()) {
                pos++;
                switch (json[pos]) {
                    case 'n': s += '\n'; break;
                    case 't': s += '\t'; break;
                    case '"': s += '"'; break;
                    case '\\': s += '\\'; break;
                    default: s += json[pos];
                }
            } else {
                s += json[pos];
            }
            pos++;
        }
        if (pos < json.size()) pos++; // skip closing quote
        return JsonValue(s);
    }
    
    JsonValue parse_number() {
        size_t start = pos;
        if (json[pos] == '-') pos++;
        while (pos < json.size() && (std::isdigit(json[pos]) || json[pos] == '.' || 
               json[pos] == 'e' || json[pos] == 'E' || json[pos] == '+' || json[pos] == '-')) {
            pos++;
        }
        return JsonValue(std::stod(json.substr(start, pos - start)));
    }
    
    JsonValue parse_array() {
        JsonValue arr;
        arr.type = JsonValue::Array;
        pos++; // skip [
        skip_ws();
        while (pos < json.size() && json[pos] != ']') {
            arr.arr_val.push_back(parse_value());
            skip_ws();
            if (json[pos] == ',') pos++;
            skip_ws();
        }
        if (pos < json.size()) pos++; // skip ]
        return arr;
    }
    
    JsonValue parse_object() {
        JsonValue obj;
        obj.type = JsonValue::Object;
        pos++; // skip {
        skip_ws();
        while (pos < json.size() && json[pos] != '}') {
            skip_ws();
            if (json[pos] != '"') break;
            auto key = parse_string();
            skip_ws();
            if (json[pos] == ':') pos++;
            skip_ws();
            obj.obj_val[key.str_val] = parse_value();
            skip_ws();
            if (json[pos] == ',') pos++;
            skip_ws();
        }
        if (pos < json.size()) pos++; // skip }
        return obj;
    }
    
    JsonValue parse_value() {
        skip_ws();
        if (pos >= json.size()) return JsonValue();
        
        char c = json[pos];
        if (c == '"') return parse_string();
        if (c == '{') return parse_object();
        if (c == '[') return parse_array();
        if (c == '-' || std::isdigit(c)) return parse_number();
        if (json.substr(pos, 4) == "true") { pos += 4; return JsonValue(true); }
        if (json.substr(pos, 5) == "false") { pos += 5; return JsonValue(false); }
        if (json.substr(pos, 4) == "null") { pos += 4; return JsonValue(); }
        return JsonValue();
    }
    
public:
    JsonParser(const std::string& j) : json(j) {}
    JsonValue parse() { return parse_value(); }
};

JsonValue parse_json(const std::string& json) {
    JsonParser parser(json);
    return parser.parse();
}

// ══════════════════════════════════════════════════════════════════════════════
// Yahoo Finance API
// ══════════════════════════════════════════════════════════════════════════════

struct StockQuote {
    std::string symbol;
    double price = 0.0;
    double market_cap = 0.0;
    double pe_ratio = 0.0;
    double gross_margin = 0.0;
    double operating_margin = 0.0;
    double profit_margin = 0.0;
    double fcf_yield = 0.0;
    double revenue_growth = 0.0;
    std::string sector;
    bool valid = false;
};

struct OptionContract {
    double strike = 0.0;
    double bid = 0.0;
    double ask = 0.0;
    double last = 0.0;
    double implied_vol = 0.0;
    int volume = 0;
    int open_interest = 0;
    std::string expiration;
};

StockQuote fetch_quote(const std::string& symbol) {
    StockQuote quote;
    quote.symbol = symbol;
    
    // Yahoo Finance v8 API
    std::string url = "https://query1.finance.yahoo.com/v8/finance/chart/" + symbol + 
                      "?interval=1d&range=1d";
    std::string response = http_get(url);
    
    if (response.empty()) return quote;
    
    auto json = parse_json(response);
    auto result = json["chart"]["result"][0];
    auto meta = result["meta"];
    
    quote.price = meta["regularMarketPrice"].as_double();
    if (quote.price > 0) quote.valid = true;
    
    // Fetch fundamentals via quoteSummary
    std::string fund_url = "https://query1.finance.yahoo.com/v10/finance/quoteSummary/" + 
                           symbol + "?modules=defaultKeyStatistics,financialData,summaryDetail";
    std::string fund_response = http_get(fund_url);
    
    if (!fund_response.empty()) {
        auto fund_json = parse_json(fund_response);
        auto result = fund_json["quoteSummary"]["result"][0];
        auto stats = result["defaultKeyStatistics"];
        auto financial = result["financialData"];
        
        quote.pe_ratio = stats["trailingPE"]["raw"].as_double();
        quote.gross_margin = financial["grossMargins"]["raw"].as_double() * 100;
        quote.operating_margin = financial["operatingMargins"]["raw"].as_double() * 100;
        quote.profit_margin = financial["profitMargins"]["raw"].as_double() * 100;
        quote.revenue_growth = financial["revenueGrowth"]["raw"].as_double() * 100;
        quote.market_cap = stats["marketCap"]["raw"].as_double();
        
        // FCF yield calculation
        double fcf = financial["freeCashflow"]["raw"].as_double();
        if (quote.market_cap > 0 && fcf != 0) {
            quote.fcf_yield = (fcf / quote.market_cap) * 100;
        }
    }
    
    return quote;
}

std::vector<std::string> fetch_option_expirations(const std::string& symbol) {
    std::vector<std::string> expirations;
    
    std::string url = "https://query1.finance.yahoo.com/v7/finance/options/" + symbol;
    std::string response = http_get(url);
    
    if (response.empty()) return expirations;
    
    auto json = parse_json(response);
    auto result = json["optionChain"]["result"][0];
    auto exp_timestamps = result["expirationDates"];
    
    for (size_t i = 0; i < exp_timestamps.size(); i++) {
        time_t ts = static_cast<time_t>(exp_timestamps[i].as_double());
        struct tm* tm_info = gmtime(&ts);
        char buffer[11];
        strftime(buffer, 11, "%Y-%m-%d", tm_info);
        expirations.push_back(buffer);
    }
    
    return expirations;
}

std::vector<OptionContract> fetch_puts(const std::string& symbol, const std::string& expiration) {
    std::vector<OptionContract> puts;
    
    // Convert expiration to timestamp
    struct tm tm = {};
    strptime(expiration.c_str(), "%Y-%m-%d", &tm);
    time_t exp_ts = timegm(&tm);
    
    std::string url = "https://query1.finance.yahoo.com/v7/finance/options/" + symbol + 
                      "?date=" + std::to_string(exp_ts);
    std::string response = http_get(url);
    
    if (response.empty()) return puts;
    
    auto json = parse_json(response);
    auto result = json["optionChain"]["result"][0];
    auto options = result["options"][0];
    auto put_chain = options["puts"];
    
    for (size_t i = 0; i < put_chain.size(); i++) {
        auto& opt = put_chain[i];
        OptionContract contract;
        contract.strike = opt["strike"].as_double();
        contract.bid = opt["bid"].as_double();
        contract.ask = opt["ask"].as_double();
        contract.last = opt["lastPrice"].as_double();
        contract.implied_vol = opt["impliedVolatility"].as_double();
        contract.volume = static_cast<int>(opt["volume"].as_double());
        contract.open_interest = static_cast<int>(opt["openInterest"].as_double());
        contract.expiration = expiration;
        puts.push_back(contract);
    }
    
    return puts;
}

// ══════════════════════════════════════════════════════════════════════════════
// Screening Logic
// ══════════════════════════════════════════════════════════════════════════════

struct ScreeningResult {
    std::string ticker;
    double price = 0.0;
    double strike = 0.0;
    std::string expiration;
    int dte = 0;
    double bid = 0.0;
    double ask = 0.0;
    double mid = 0.0;
    Greeks greeks;
    double iv = 0.0;
    double iv_rank = -1.0;  // -1 = N/A
    double otm_pct = 0.0;
    double monthly_return = 0.0;
    double capital = 0.0;
    double premium = 0.0;
    int volume = 0;
    int oi = 0;
    int quality_score = 50;
    bool earnings_risk = false;
    double score = 0.0;
};

struct ScreeningArgs {
    std::vector<std::string> tickers;
    bool ai_stocks = false;
    bool income_mode = false;
    bool spreads = false;
    bool fundamentals = false;
    bool verbose = false;
    
    double min_ivr = 0.0;
    double min_return = 0.5;
    double min_delta = 0.15;
    double max_delta = 0.35;
    int min_dte = 20;
    int max_dte = 50;
    int top = 25;
    
    double min_margin = -999;
    double min_fcf_yield = -999;
    double min_revenue_growth = -999;
};

int compute_quality_score(const StockQuote& quote) {
    int score = 50;  // neutral start
    
    // Gross margin: >60% excellent, >40% good, <20% poor
    if (quote.gross_margin >= 60) score += 12;
    else if (quote.gross_margin >= 40) score += 6;
    else if (quote.gross_margin < 20 && quote.gross_margin > 0) score -= 8;
    
    // Operating margin
    if (quote.operating_margin >= 25) score += 10;
    else if (quote.operating_margin >= 15) score += 5;
    else if (quote.operating_margin < 0) score -= 10;
    
    // FCF yield
    if (quote.fcf_yield >= 5) score += 10;
    else if (quote.fcf_yield >= 2) score += 5;
    else if (quote.fcf_yield < 0) score -= 8;
    
    // Revenue growth
    if (quote.revenue_growth >= 20) score += 10;
    else if (quote.revenue_growth >= 10) score += 5;
    else if (quote.revenue_growth < 0) score -= 8;
    
    // P/E ratio
    if (quote.pe_ratio > 0 && quote.pe_ratio <= 25) score += 8;
    else if (quote.pe_ratio > 25 && quote.pe_ratio <= 50) score += 2;
    else if (quote.pe_ratio > 100 || quote.pe_ratio < 0) score -= 5;
    
    return std::max(0, std::min(100, score));
}

int days_until(const std::string& date_str) {
    struct tm tm = {};
    strptime(date_str.c_str(), "%Y-%m-%d", &tm);
    time_t exp_time = timegm(&tm);
    time_t now = time(nullptr);
    return static_cast<int>((exp_time - now) / 86400);
}

std::vector<ScreeningResult> screen_ticker(const std::string& symbol, const ScreeningArgs& args) {
    std::vector<ScreeningResult> results;
    
    // Fetch quote and fundamentals
    StockQuote quote = fetch_quote(symbol);
    if (!quote.valid) {
        std::cerr << "  ⚠️  Could not fetch data for " << symbol << std::endl;
        return results;
    }
    
    int quality_score = compute_quality_score(quote);
    
    // Apply fundamental filters
    if (args.min_margin > -999 && quote.gross_margin < args.min_margin) return results;
    if (args.min_fcf_yield > -999 && quote.fcf_yield < args.min_fcf_yield) return results;
    if (args.min_revenue_growth > -999 && quote.revenue_growth < args.min_revenue_growth) return results;
    
    // Fetch option expirations
    auto expirations = fetch_option_expirations(symbol);
    if (expirations.empty()) return results;
    
    for (const auto& exp : expirations) {
        int dte = days_until(exp);
        if (dte < args.min_dte || dte > args.max_dte) continue;
        
        double T = dte / 365.0;
        
        // Fetch puts for this expiration
        auto puts = fetch_puts(symbol, exp);
        
        for (const auto& put : puts) {
            // Skip ITM puts
            if (put.strike >= quote.price) continue;
            if (put.bid <= 0) continue;
            
            double mid = (put.bid + put.ask) / 2.0;
            double spread = put.ask - put.bid;
            
            // Skip wide spreads (>15%)
            if (mid > 0 && (spread / mid) > 0.15) continue;
            
            double sigma = (put.implied_vol > 0) ? put.implied_vol : 0.3;
            
            // Calculate Greeks
            Greeks greeks = bs_put_greeks(quote.price, put.strike, T, RISK_FREE_RATE, sigma);
            
            double abs_delta = std::abs(greeks.delta);
            if (abs_delta < args.min_delta || abs_delta > args.max_delta) continue;
            
            // Calculate returns
            double capital_required = put.strike * 100;
            double premium_total = mid * 100;
            double monthly_return = (dte > 0) ? (mid / put.strike) * (30.0 / dte) * 100 : 0;
            
            if (monthly_return < args.min_return) continue;
            
            double otm_pct = ((quote.price - put.strike) / quote.price) * 100;
            
            // Composite score
            double theta_score = std::min(std::abs(greeks.theta) / 10.0, 5.0);
            double gamma_penalty = std::min(greeks.gamma * 10000, 5.0);
            double qual_contribution = (quality_score / 100.0) * 10;
            
            double score = monthly_return * 0.40
                         + 0.5 * 15  // IVR placeholder (would need historical data)
                         + otm_pct * 0.25
                         + theta_score * 1.5
                         + qual_contribution * 0.8
                         - gamma_penalty * 0.5;
            
            ScreeningResult result;
            result.ticker = symbol;
            result.price = quote.price;
            result.strike = put.strike;
            result.expiration = exp;
            result.dte = dte;
            result.bid = put.bid;
            result.ask = put.ask;
            result.mid = mid;
            result.greeks = greeks;
            result.iv = put.implied_vol * 100;
            result.otm_pct = otm_pct;
            result.monthly_return = monthly_return;
            result.capital = capital_required;
            result.premium = premium_total;
            result.volume = put.volume;
            result.oi = put.open_interest;
            result.quality_score = quality_score;
            result.score = score;
            
            results.push_back(result);
        }
    }
    
    return results;
}

// ══════════════════════════════════════════════════════════════════════════════
// Output Formatting
// ══════════════════════════════════════════════════════════════════════════════

std::string star_rating(double score) {
    if (score >= 20) return "★★★";
    if (score >= 16) return "★★";
    if (score >= 12) return "★";
    return "";
}

std::string format_large_num(double n) {
    if (n == 0) return "N/A";
    std::string sign = (n < 0) ? "-" : "";
    n = std::abs(n);
    std::ostringstream oss;
    oss << std::fixed;
    if (n >= 1e12) { oss << std::setprecision(1) << sign << "$" << (n/1e12) << "T"; }
    else if (n >= 1e9) { oss << std::setprecision(1) << sign << "$" << (n/1e9) << "B"; }
    else if (n >= 1e6) { oss << std::setprecision(1) << sign << "$" << (n/1e6) << "M"; }
    else { oss << std::setprecision(0) << sign << "$" << n; }
    return oss.str();
}

void print_results(std::vector<ScreeningResult>& results, const ScreeningArgs& args) {
    if (results.empty()) {
        std::cout << "\n  No opportunities found matching your criteria.\n";
        std::cout << "  Try relaxing filters (lower --min-return or wider delta range)\n";
        return;
    }
    
    // Sort by score descending
    std::sort(results.begin(), results.end(), 
              [](const auto& a, const auto& b) { return a.score > b.score; });
    
    // Limit to top N
    size_t limit = std::min(static_cast<size_t>(args.top), results.size());
    
    std::cout << "\n📋 Top " << limit << " opportunities (of " << results.size() << " found):\n\n";
    
    // Header
    std::cout << std::left << std::setw(8) << "Ticker"
              << std::right << std::setw(9) << "Price"
              << std::setw(9) << "Strike"
              << std::setw(12) << "Exp"
              << std::setw(5) << "DTE"
              << std::setw(8) << "Delta"
              << std::setw(9) << "Θ $/day"
              << std::setw(9) << "Gamma"
              << std::setw(7) << "IV%"
              << std::setw(8) << "OTM%"
              << std::setw(9) << "Mo.Ret%"
              << std::setw(10) << "Capital"
              << std::setw(9) << "Premium"
              << std::setw(6) << "Qlty"
              << std::setw(7) << "Score"
              << std::setw(5) << "Rate"
              << "\n";
    
    std::cout << std::string(120, '-') << "\n";
    
    for (size_t i = 0; i < limit; i++) {
        const auto& r = results[i];
        std::cout << std::left << std::setw(8) << r.ticker
                  << std::right << std::fixed
                  << std::setw(8) << std::setprecision(2) << "$" << r.price
                  << std::setw(8) << std::setprecision(2) << "$" << r.strike
                  << std::setw(12) << r.expiration
                  << std::setw(5) << r.dte
                  << std::setw(8) << std::setprecision(2) << r.greeks.delta
                  << std::setw(8) << std::setprecision(2) << "$" << r.greeks.theta
                  << std::setw(9) << std::setprecision(5) << r.greeks.gamma
                  << std::setw(7) << std::setprecision(1) << r.iv
                  << std::setw(7) << std::setprecision(1) << r.otm_pct << "%"
                  << std::setw(8) << std::setprecision(2) << r.monthly_return << "%"
                  << std::setw(9) << std::setprecision(0) << "$" << r.capital
                  << std::setw(8) << std::setprecision(0) << "$" << r.premium
                  << std::setw(6) << r.quality_score
                  << std::setw(7) << std::setprecision(2) << r.score
                  << std::setw(5) << star_rating(r.score)
                  << "\n";
    }
    
    // Legend
    std::cout << "\n" << std::string(90, '=') << "\n";
    std::cout << "  ★★★ = Top tier | ★★ = Strong | ★ = Good\n";
    std::cout << "  Θ $/day = Theta decay per day per contract\n";
    std::cout << "  Γ Gamma = Rate of delta change (high = assignment risk accelerates)\n";
    std::cout << "  Qlty    = Fundamental quality score (0-100)\n";
    std::cout << std::string(90, '=') << "\n\n";
}

void print_banner(const ScreeningArgs& args, const std::vector<std::string>& tickers, 
                  const std::string& list_name) {
    auto now = std::chrono::system_clock::now();
    auto time = std::chrono::system_clock::to_time_t(now);
    
    std::cout << std::string(95, '=') << "\n";
    std::cout << "  💰 CSP SCREENER v2.1 (C++) — Cash-Secured Puts\n";
    std::cout << "  📅 " << std::put_time(std::localtime(&time), "%Y-%m-%d %H:%M:%S") << "\n";
    std::cout << "  📋 " << list_name << ": ";
    for (size_t i = 0; i < std::min(tickers.size(), size_t(8)); i++) {
        std::cout << tickers[i];
        if (i < std::min(tickers.size(), size_t(8)) - 1) std::cout << ", ";
    }
    if (tickers.size() > 8) std::cout << "...";
    std::cout << "\n";
    std::cout << "  🎯 Delta: " << args.min_delta << "–" << args.max_delta 
              << " | DTE: " << args.min_dte << "–" << args.max_dte << "\n";
    std::cout << "  📊 Min Return: " << args.min_return << "% | Min IVR: " << args.min_ivr << "%\n";
    std::cout << std::string(95, '=') << "\n";
}

// ══════════════════════════════════════════════════════════════════════════════
// CLI Argument Parser
// ══════════════════════════════════════════════════════════════════════════════

void print_help() {
    std::cout << R"(
CSP Screener v2.1 (C++) — Cash-Secured Put Opportunity Finder

Usage: screener [options]

Ticker Selection:
  -t, --tickers TICK...   Tickers to screen (space-separated)
  --ai-stocks             Use AI/Tech watchlist (NVDA, AMD, MSFT, etc.)
  --income                Income mode: Coach Mak strategy (delta 0.15-0.25)

Options Filters:
  --min-return PCT        Minimum monthly return % (default: 0.5)
  --min-delta VAL         Minimum absolute delta (default: 0.15)
  --max-delta VAL         Maximum absolute delta (default: 0.35)
  --min-dte DAYS          Minimum days to expiration (default: 20)
  --max-dte DAYS          Maximum days to expiration (default: 50)
  --top N                 Number of top results (default: 25)

Fundamental Filters:
  --min-margin PCT        Minimum gross margin %
  --min-fcf-yield PCT     Minimum FCF yield %
  --min-revenue-growth PCT  Minimum YoY revenue growth %

Display:
  --fundamentals          Show fundamentals summary table
  --verbose               Show full Greeks detail
  -h, --help              Show this help message

Examples:
  screener --ai-stocks --top 10
  screener -t NVDA AMD TSLA --min-return 1.0
  screener --income --fundamentals
)";
}

ScreeningArgs parse_args(int argc, char* argv[]) {
    ScreeningArgs args;
    
    for (int i = 1; i < argc; i++) {
        std::string arg = argv[i];
        
        if (arg == "-h" || arg == "--help") {
            print_help();
            exit(0);
        }
        else if (arg == "--ai-stocks") {
            args.ai_stocks = true;
        }
        else if (arg == "--income") {
            args.income_mode = true;
        }
        else if (arg == "--spreads") {
            args.spreads = true;
        }
        else if (arg == "--fundamentals") {
            args.fundamentals = true;
        }
        else if (arg == "--verbose") {
            args.verbose = true;
        }
        else if ((arg == "-t" || arg == "--tickers") && i + 1 < argc) {
            while (i + 1 < argc && argv[i + 1][0] != '-') {
                args.tickers.push_back(argv[++i]);
            }
        }
        else if (arg == "--min-return" && i + 1 < argc) {
            args.min_return = std::stod(argv[++i]);
        }
        else if (arg == "--min-delta" && i + 1 < argc) {
            args.min_delta = std::stod(argv[++i]);
        }
        else if (arg == "--max-delta" && i + 1 < argc) {
            args.max_delta = std::stod(argv[++i]);
        }
        else if (arg == "--min-dte" && i + 1 < argc) {
            args.min_dte = std::stoi(argv[++i]);
        }
        else if (arg == "--max-dte" && i + 1 < argc) {
            args.max_dte = std::stoi(argv[++i]);
        }
        else if (arg == "--top" && i + 1 < argc) {
            args.top = std::stoi(argv[++i]);
        }
        else if (arg == "--min-margin" && i + 1 < argc) {
            args.min_margin = std::stod(argv[++i]);
        }
        else if (arg == "--min-fcf-yield" && i + 1 < argc) {
            args.min_fcf_yield = std::stod(argv[++i]);
        }
        else if (arg == "--min-revenue-growth" && i + 1 < argc) {
            args.min_revenue_growth = std::stod(argv[++i]);
        }
    }
    
    // Income mode defaults
    if (args.income_mode && args.min_delta == 0.15 && args.max_delta == 0.35) {
        args.max_delta = 0.25;
    }
    
    return args;
}

// ══════════════════════════════════════════════════════════════════════════════
// Main
// ══════════════════════════════════════════════════════════════════════════════

int main(int argc, char* argv[]) {
    // Initialize libcurl
    curl_global_init(CURL_GLOBAL_DEFAULT);
    
    ScreeningArgs args = parse_args(argc, argv);
    
    // Resolve ticker list
    std::vector<std::string> tickers;
    std::string list_name;
    
    if (args.income_mode && args.tickers.empty() && !args.ai_stocks) {
        tickers = INCOME_TICKERS;
        list_name = "💵 Income Strategy (Coach Mak)";
    } else if (args.ai_stocks) {
        tickers = AI_TECH_TICKERS;
        list_name = "AI/Tech + Datacenter Watchlist";
    } else if (!args.tickers.empty()) {
        tickers = args.tickers;
        list_name = "Custom";
    } else {
        tickers = DEFAULT_TICKERS;
        list_name = "Default Watchlist";
    }
    
    print_banner(args, tickers, list_name);
    
    std::vector<ScreeningResult> all_results;
    
    for (size_t i = 0; i < tickers.size(); i++) {
        const auto& ticker = tickers[i];
        std::cout << "  Scanning " << ticker << " for CSPs... (" 
                  << (i + 1) << "/" << tickers.size() << ")" << std::flush;
        
        auto results = screen_ticker(ticker, args);
        all_results.insert(all_results.end(), results.begin(), results.end());
        
        std::cout << " [" << results.size() << " found]\n";
    }
    
    print_results(all_results, args);
    
    // Cleanup
    curl_global_cleanup();
    
    return 0;
}
