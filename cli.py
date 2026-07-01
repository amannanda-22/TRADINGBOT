#!/usr/bin/env python3
"""
Binance Futures Testnet Trading Bot — CLI entry point.

Examples
--------
Market order::

    python cli.py place-order --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001

Limit order::

    python cli.py place-order --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.001 --price 150000

Stop-limit order (bonus)::

    python cli.py place-order --symbol BTCUSDT --side BUY --type STOP_LIMIT \\
        --quantity 0.002 --price 75000 --stop-price 74000
"""

import argparse
import sys
from typing import Optional

from bot.client import BinanceFuturesClient
from bot.logging_config import setup_logging
from bot.orders import place_limit_order, place_market_order, place_stop_limit_order
from bot.validators import (
    validate_order_type,
    validate_price,
    validate_quantity,
    validate_side,
    validate_symbol,
)


# ─── Display helpers ──────────────────────────────────────────────────────────

def _print_request(
    symbol: str,
    side: str,
    order_type: str,
    quantity: float,
    price: Optional[float] = None,
    stop_price: Optional[float] = None,
) -> None:
    """Print a formatted order-request summary block."""
    print()
    print("=== ORDER REQUEST ===")
    print(f"Symbol:     {symbol}")
    print(f"Side:       {side}")
    print(f"Type:       {order_type}")
    print(f"Quantity:   {quantity}")
    if price is not None:
        print(f"Price:      {price:,.2f}")
    if stop_price is not None:
        print(f"Stop Price: {stop_price:,.2f}")


def _resolve_price_display(response: dict) -> str:
    """Choose the most informative price string for the response block.

    Priority:
    1. ``avgPrice`` when > 0  (order filled — this is the actual fill price).
    2. ``price``  when status is FILLED (limit order filled at limit price).
    3. ``price``  with "resting" label when order is open but not yet filled.
    4. Descriptive N/A when no price info is available.
    """
    avg   = response.get("avg_price")
    price = response.get("price")
    status = response.get("status", "")

    # Filled — use avgPrice
    if avg:
        try:
            v = float(avg)
            if v > 0:
                return f"{v:,.2f}"
        except (ValueError, TypeError):
            pass

    # Has a resting limit price
    if price:
        try:
            v = float(price)
            if v > 0:
                if status == "FILLED":
                    return f"{v:,.2f}"
                return f"{v:,.2f}  (order open — not yet filled)"
        except (ValueError, TypeError):
            pass

    return "N/A"


def _print_response(response: dict) -> None:
    """Print a formatted order-response summary block."""
    print()
    print("=== ORDER RESPONSE ===")
    print(f"Order ID:     {response.get('order_id')}")
    print(f"Status:       {response.get('status')}")
    print(f"Executed Qty: {response.get('executed_qty', '0')}")
    print(f"Avg Price:    {_resolve_price_display(response)}")

    sp = response.get("stop_price")
    if sp:
        try:
            v = float(sp)
            if v > 0:
                print(f"Stop Price:   {v:,.2f}")
        except (ValueError, TypeError):
            pass


# ─── Command handler ──────────────────────────────────────────────────────────

def cmd_place_order(args: argparse.Namespace) -> int:
    """Execute the ``place-order`` sub-command.

    Validates all inputs before any network call.  Prints a request summary
    and a response block, then exits with code ``0`` on success or ``1`` on
    any error.

    Returns:
        Exit code: ``0`` = success, ``1`` = error.
    """
    symbol     = args.symbol.strip().upper()
    side       = args.side.strip().upper()
    order_type = args.type.strip().upper()
    quantity   = args.quantity
    price      = args.price
    stop_price = args.stop_price

    # Validate all parameters before touching the network
    try:
        validate_symbol(symbol)
        validate_side(side)
        validate_order_type(order_type)
        validate_quantity(quantity)

        if order_type in ("LIMIT", "STOP_LIMIT") and price is None:
            raise ValueError(f"--price is required for {order_type} orders.")
        if order_type == "STOP_LIMIT" and stop_price is None:
            raise ValueError("--stop-price is required for STOP_LIMIT orders.")
        if price is not None:
            validate_price(price, field_name="price")
        if stop_price is not None:
            validate_price(stop_price, field_name="stop_price")

    except ValueError as exc:
        print(f"\n❌  Validation Error: {exc}", file=sys.stderr)
        return 1

    _print_request(symbol, side, order_type, quantity, price, stop_price)

    try:
        client = BinanceFuturesClient()

        if order_type == "MARKET":
            response = place_market_order(client, symbol, side, quantity)
        elif order_type == "LIMIT":
            response = place_limit_order(client, symbol, side, quantity, price)
        else:  # STOP_LIMIT
            response = place_stop_limit_order(
                client, symbol, side, quantity, price, stop_price
            )

        _print_response(response)
        print("\n✅  Order placed successfully!")
        return 0

    except ValueError as exc:
        print(f"\n❌  Validation Error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"\n❌  Error placing order: {exc}", file=sys.stderr)
        return 1


# ─── Argument parser ──────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    """Construct and return the root argument parser."""
    parser = argparse.ArgumentParser(
        prog="trading_bot",
        description="Binance Futures Testnet Trading Bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python cli.py place-order --symbol BTCUSDT --side BUY"
            " --type MARKET --quantity 0.001\n"
            "  python cli.py place-order --symbol BTCUSDT --side SELL"
            " --type LIMIT --quantity 0.001 --price 150000\n"
            "  python cli.py place-order --symbol BTCUSDT --side BUY"
            " --type STOP_LIMIT --quantity 0.002 --price 75000 --stop-price 74000"
        ),
    )

    subs = parser.add_subparsers(dest="command", required=True)

    po = subs.add_parser(
        "place-order",
        help="Place a futures order on the Binance Testnet",
    )
    po.add_argument(
        "--symbol", required=True,
        help="Trading pair symbol, e.g. BTCUSDT (case-insensitive)",
    )
    po.add_argument(
        "--side", required=True,
        help="Order side: BUY or SELL (case-insensitive)",
    )
    po.add_argument(
        "--type", required=True, dest="type",
        help="Order type: MARKET | LIMIT | STOP_LIMIT (case-insensitive)",
    )
    po.add_argument(
        "--quantity", required=True, type=float,
        help="Order quantity in base asset units (e.g. 0.001 BTC)",
    )
    po.add_argument(
        "--price", default=None, type=float,
        help="Limit price — required for LIMIT and STOP_LIMIT orders",
    )
    po.add_argument(
        "--stop-price", default=None, type=float, dest="stop_price",
        help="Stop trigger price — required for STOP_LIMIT orders",
    )
    po.set_defaults(func=cmd_place_order)

    return parser


# ─── Entry point ──────────────────────────────────────────────────────────────

def main() -> None:
    """Parse CLI arguments and dispatch to the appropriate command handler."""
    setup_logging()
    parser = _build_parser()
    args   = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
