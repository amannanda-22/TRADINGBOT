# Binance Futures Testnet Trading Bot

A professional, production-ready CLI trading bot for **Binance Futures Testnet (USDT-M)**
built with Python 3.x.

Supports **Market**, **Limit**, and **Stop-Limit** orders with full input validation,
structured rotating logs, and clean separation between the API layer and the CLI layer.

---

## Project Structure

```
trading_bot/
├── bot/
│   ├── __init__.py          # Package exports
│   ├── client.py            # Binance Futures Testnet client wrapper
│   ├── orders.py            # Order placement logic (market / limit / stop-limit)
│   ├── validators.py        # Input validation — raises clear ValueError on bad input
│   └── logging_config.py   # Rotating file + console logging setup
├── cli.py                   # CLI entry point (argparse)
├── requirements.txt         # Runtime dependencies
├── .env                     # API credentials  ← fill this in before running
├── .gitignore
└── README.md
```

---

## Setup

### 1 — Get Testnet API Keys

1. Visit **https://testnet.binancefuture.com**
2. Register / log in
3. Go to **API Management** → **Generate Key**
4. Copy your **API Key** and **Secret Key**

### 2 — Create a virtual environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python -m venv venv
source venv/bin/activate
```

### 3 — Install dependencies

```bash
pip install -r requirements.txt
```

### 4 — Configure credentials

Edit `.env` and paste your testnet keys:

```env
BINANCE_API_KEY=your_testnet_api_key_here
BINANCE_API_SECRET=your_testnet_api_secret_here
BINANCE_TESTNET_URL=https://testnet.binancefuture.com
```

> **Security:** `.env` is in `.gitignore` and must never be committed.

---

## Usage

All commands are run from the `trading_bot/` directory (where `cli.py` lives).

### Help

```bash
python cli.py --help
python cli.py place-order --help
```

---

### Market Order — BUY

Executes immediately at the best available price.

```bash
python cli.py place-order --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001
```

**Expected output:**
```
=== ORDER REQUEST ===
Symbol:     BTCUSDT
Side:       BUY
Type:       MARKET
Quantity:   0.001

=== ORDER RESPONSE ===
Order ID:     18164753457
Status:       FILLED
Executed Qty: 0.001
Avg Price:    58,423.60

✅  Order placed successfully!
```

---

### Market Order — SELL

```bash
python cli.py place-order --symbol BTCUSDT --side SELL --type MARKET --quantity 0.001
```

---

### Limit Order — BUY

Rests on the order book until the price reaches `50000` (GTC).

```bash
python cli.py place-order --symbol BTCUSDT --side BUY --type LIMIT --quantity 0.001 --price 50000
```

**Expected output:**
```
=== ORDER REQUEST ===
Symbol:     BTCUSDT
Side:       BUY
Type:       LIMIT
Quantity:   0.001
Price:      50,000.00

=== ORDER RESPONSE ===
Order ID:     18164806068
Status:       NEW
Executed Qty: 0.0000
Avg Price:    50,000.00  (order open — not yet filled)

✅  Order placed successfully!
```

---

### Limit Order — SELL

```bash
python cli.py place-order --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.001 --price 150000
```

---

### Stop-Limit Order — BUY *(Bonus)*

Triggers a BUY limit when price rises **above** `stop_price`.
Use when the current market price is below the stop price (breakout entry).

```bash
python cli.py place-order --symbol BTCUSDT --side BUY --type STOP_LIMIT --quantity 0.002 --price 75000 --stop-price 74000
```

**Expected output:**
```
=== ORDER REQUEST ===
Symbol:     BTCUSDT
Side:       BUY
Type:       STOP_LIMIT
Quantity:   0.002
Price:      75,000.00
Stop Price: 74,000.00

=== ORDER RESPONSE ===
Order ID:     18165012340
Status:       NEW
Executed Qty: 0.0000
Avg Price:    75,000.00  (order open — not yet filled)
Stop Price:   74,000.00

✅  Order placed successfully!
```

---

### Stop-Limit Order — SELL *(Bonus)*

Triggers a SELL limit when price falls **below** `stop_price`.
Use when current market price is above the stop price (stop-loss on a long position).

```bash
python cli.py place-order --symbol BTCUSDT --side SELL --type STOP_LIMIT --quantity 0.002 --price 43000 --stop-price 44000
```

---

## Validation — Error Handling Examples

The bot validates all inputs before any network call:

```bash
# Invalid side
python cli.py place-order --symbol BTCUSDT --side HOLD --type MARKET --quantity 0.001
# ❌  Validation Error: Side must be one of ['BUY', 'SELL']. Got: 'HOLD'.

# Invalid order type
python cli.py place-order --symbol BTCUSDT --side BUY --type FOK --quantity 0.001
# ❌  Validation Error: Order type must be one of ['LIMIT', 'MARKET', 'STOP_LIMIT']. Got: 'FOK'.

# Negative quantity
python cli.py place-order --symbol BTCUSDT --side BUY --type MARKET --quantity -5
# ❌  Validation Error: Quantity must be a positive number greater than zero. Got: -5.0.

# LIMIT order missing --price
python cli.py place-order --symbol BTCUSDT --side BUY --type LIMIT --quantity 0.001
# ❌  Validation Error: --price is required for LIMIT orders.

# STOP_LIMIT missing --stop-price
python cli.py place-order --symbol BTCUSDT --side BUY --type STOP_LIMIT --quantity 0.001 --price 45000
# ❌  Validation Error: --stop-price is required for STOP_LIMIT orders.
```

> **Note:** Symbol and order type are normalised to uppercase automatically,
> so `btcusdt`, `buy`, and `market` are all accepted.

---

## Sample Log Output

Log file: `logs/trading_bot.log` (max 5 MB, 3 rotated backups)

```
2026-07-01 11:15:35 | INFO     | bot.client | Binance Futures Testnet client initialized successfully
2026-07-01 11:15:35 | INFO     | bot.orders | Placing MARKET BUY order | symbol=BTCUSDT qty=0.001
2026-07-01 11:15:35 | INFO     | bot.orders | MARKET order accepted by exchange | orderId=18164753457 status=NEW
2026-07-01 11:15:36 | INFO     | bot.orders | Fill confirmed after 1 poll(s) | orderId=18164753457 status=FILLED avgPrice=58423.60 executedQty=0.001
2026-07-01 11:15:36 | INFO     | bot.orders | MARKET order result | orderId=18164753457 status=FILLED avgPrice=58423.60 executedQty=0.001
2026-07-01 11:15:58 | INFO     | bot.orders | Placing LIMIT BUY order | symbol=BTCUSDT qty=0.001 price=50000.0
2026-07-01 11:15:58 | INFO     | bot.orders | LIMIT order placed | orderId=18164806068 status=NEW price=50000.00000000
2026-07-01 11:16:45 | INFO     | bot.orders | Placing STOP_LIMIT BUY order | symbol=BTCUSDT qty=0.002 price=75000.0 stopPrice=74000.0
2026-07-01 11:16:46 | INFO     | bot.orders | STOP_LIMIT order placed | orderId=18165012340 status=NEW stopPrice=74000.00000000
2026-07-01 11:22:05 | ERROR    | bot.orders | API error (MARKET order): APIError(code=-4164): Order's notional must be no smaller than 20
```

---

## Architecture

```
cli.py
  │  Parses CLI args → normalises to uppercase → validates
  ▼
bot/validators.py
  │  Raises ValueError with clear message on bad input
  ▼
bot/orders.py
  │  Calls Binance API, polls fill status, normalises response
  ▼
bot/client.py
  │  Wraps python-binance Client (testnet=True)
  │  Provides create_order_direct() to bypass library routing quirks
  ▼
Binance Futures Testnet  (https://testnet.binancefuture.com)
```

### Module Responsibilities

| Module | Responsibility |
|---|---|
| `bot/client.py` | Authentication, connection, direct order routing |
| `bot/orders.py` | Order placement, fill polling, normalised responses |
| `bot/validators.py` | Pure input validation — no side effects |
| `bot/logging_config.py` | Log format, rotation, handler attachment |
| `cli.py` | Argument parsing, formatted output, exit codes |

---

## Assumptions

1. **Testnet only** — all orders use `testnet=True`; no real funds are at risk.
2. `GTC` (Good Till Cancelled) time-in-force is applied to all non-market orders.
3. **Stop-Limit orders map to Binance Futures `STOP` type**, which triggers on
   `stopPrice` and fills at `price`. Price direction rules:
   - **BUY STOP**: `stopPrice` must be **above** the current market price.
   - **SELL STOP**: `stopPrice` must be **below** the current market price.
4. **Minimum notional** of `quantity × price ≥ $50` applies to stop-limit orders
   on BTCUSDT Testnet. Use `quantity ≥ 0.002` near $50k BTC to be safe.
5. Quantities are passed as supplied — the caller is responsible for respecting
   exchange lot-size and minimum-notional rules for each symbol.
6. **Market order status on Testnet**: The Binance Futures Testnet matching engine
   sometimes returns `status=NEW` in the create-order response before confirming
   the fill. The bot polls order status once after placement to surface the actual
   `FILLED` state and `avgPrice`. If the fill is not confirmed within ~1.6 seconds,
   the initial response is returned — the order is still accepted and will fill.
7. Some versions of `python-binance` route `STOP` order types to the algo-order
   endpoint instead of `/fapi/v1/order`. The bot uses `create_order_direct()` to
   bypass this and always target the correct endpoint.
8. API keys are loaded exclusively from `.env` via `python-dotenv`. The `.env`
   file is gitignored and must never be committed.

---

## Error Handling Reference

| Scenario | Behaviour |
|---|---|
| Missing / wrong API keys | `ValueError` with setup instructions |
| Invalid symbol / side / type | `ValueError` before any network call |
| Non-positive qty or price | `ValueError` before any network call |
| Missing `--price` for LIMIT | `ValueError` at CLI layer |
| Missing `--stop-price` | `ValueError` at CLI layer |
| Notional below exchange minimum | `BinanceAPIException -4164`; error printed |
| Stop price on wrong side of market | `BinanceAPIException -2021`; error printed |
| Network / connectivity failure | `BinanceRequestException`; error printed |
| Any unhandled exception | Full traceback written to log file |

---

## Requirements

```
python-binance>=1.0.19
python-dotenv>=1.0.0
requests>=2.31.0
```

Install with:
```bash
pip install -r requirements.txt
```

---

*Built for Binance Futures Testnet (USDT-M). Do not use with real API keys.*
