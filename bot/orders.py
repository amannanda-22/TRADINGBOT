"""
Order placement functions for Binance Futures Testnet.

Each public function validates its inputs, delegates to the underlying
python-binance client, and returns a normalised response dict so callers
never have to inspect raw Binance payloads.

Testnet note
------------
The Binance Futures Testnet matching engine occasionally returns
``status=NEW`` for market orders in the initial create-order response,
even when the order fills within milliseconds.  Market order functions
here poll the order status once after placement to capture fill details.
"""

import logging
import time
from typing import Any, Dict

from binance.exceptions import BinanceAPIException, BinanceRequestException

from .client import BinanceFuturesClient
from .validators import validate_price, validate_quantity, validate_side, validate_symbol

logger = logging.getLogger(__name__)

# Poll settings for market order fill confirmation
_POLL_DELAY_SECS = 0.8
_POLL_ATTEMPTS = 2


# ─── Private helpers ──────────────────────────────────────────────────────────

def _format_response(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Normalise a raw Binance order response into a compact dict.

    Args:
        raw: Dict returned directly by the Binance API.

    Returns:
        Dict of key fields plus the original payload under ``"raw"``.
    """
    return {
        "order_id":        raw.get("orderId"),
        "client_order_id": raw.get("clientOrderId"),
        "symbol":          raw.get("symbol"),
        "side":            raw.get("side"),
        "type":            raw.get("type"),
        "status":          raw.get("status"),
        "executed_qty":    raw.get("executedQty"),
        "avg_price":       raw.get("avgPrice"),
        "price":           raw.get("price"),
        "stop_price":      raw.get("stopPrice"),
        "time_in_force":   raw.get("timeInForce"),
        "update_time":     raw.get("updateTime"),
        "raw":             raw,
    }


def _poll_fill_status(
    client: BinanceFuturesClient,
    symbol: str,
    order_id: int,
    raw: Dict[str, Any],
) -> Dict[str, Any]:
    """Poll order status to capture fill details after placement.

    Called when the create-order response shows ``status=NEW`` for a market
    order.  Waits a short delay then queries ``/fapi/v1/order`` up to
    ``_POLL_ATTEMPTS`` times.  Returns the first FILLED/PARTIALLY_FILLED
    response, or the original *raw* dict if fill is not confirmed in time.

    Args:
        client:   BinanceFuturesClient instance.
        symbol:   Trading pair.
        order_id: Binance order ID.
        raw:      Original create-order response to fall back to.

    Returns:
        Updated raw order dict (or original if polling did not yield a fill).
    """
    for attempt in range(1, _POLL_ATTEMPTS + 1):
        time.sleep(_POLL_DELAY_SECS)
        try:
            updated = client.get_order(symbol=symbol, order_id=order_id)
            status = updated.get("status", "")
            if status in ("FILLED", "PARTIALLY_FILLED"):
                logger.info(
                    "Fill confirmed after %d poll(s) | orderId=%s "
                    "status=%s avgPrice=%s executedQty=%s",
                    attempt, order_id,
                    updated.get("status"),
                    updated.get("avgPrice"),
                    updated.get("executedQty"),
                )
                return updated
            logger.debug(
                "Poll %d/%d | orderId=%s status=%s",
                attempt, _POLL_ATTEMPTS, order_id, status,
            )
        except Exception as exc:
            logger.warning("Fill-status poll failed (attempt %d): %s", attempt, exc)

    logger.info(
        "Order %s still %s after polling — returning initial response "
        "(testnet matching engine may be delayed)",
        order_id, raw.get("status"),
    )
    return raw


# ─── Public API ───────────────────────────────────────────────────────────────

def place_market_order(
    client: BinanceFuturesClient,
    symbol: str,
    side: str,
    quantity: float,
) -> Dict[str, Any]:
    """Place a MARKET order on Binance Futures Testnet.

    Polls fill status once after placement to surface ``avgPrice`` and
    ``executedQty``, which the Testnet create-order response may omit.

    Args:
        client:   Authenticated :class:`BinanceFuturesClient` instance.
        symbol:   Trading pair, e.g. ``"BTCUSDT"``.
        side:     ``"BUY"`` or ``"SELL"``.
        quantity: Amount of base asset to trade.

    Returns:
        Normalised order response dict.

    Raises:
        ValueError: On invalid inputs.
        BinanceAPIException: On exchange-level errors.
        BinanceRequestException: On connectivity errors.
    """
    validate_symbol(symbol)
    validate_side(side)
    validate_quantity(quantity)

    logger.info(
        "Placing MARKET %s order | symbol=%s qty=%s", side, symbol, quantity
    )

    try:
        raw = client.get_client().futures_create_order(
            symbol=symbol,
            side=side,
            type="MARKET",
            quantity=quantity,
        )
        logger.info(
            "MARKET order accepted by exchange | orderId=%s status=%s",
            raw.get("orderId"), raw.get("status"),
        )

        # Testnet may return NEW before the matching engine confirms the fill.
        if raw.get("status") == "NEW":
            raw = _poll_fill_status(client, symbol, raw["orderId"], raw)

        response = _format_response(raw)
        logger.info(
            "MARKET order result | orderId=%s status=%s "
            "avgPrice=%s executedQty=%s",
            response["order_id"], response["status"],
            response["avg_price"], response["executed_qty"],
        )
        return response

    except BinanceAPIException as exc:
        logger.error("API error (MARKET order): %s", exc, exc_info=True)
        raise
    except BinanceRequestException as exc:
        logger.error("Request error (MARKET order): %s", exc, exc_info=True)
        raise
    except Exception as exc:
        logger.error("Unexpected error (MARKET order): %s", exc, exc_info=True)
        raise


def place_limit_order(
    client: BinanceFuturesClient,
    symbol: str,
    side: str,
    quantity: float,
    price: float,
) -> Dict[str, Any]:
    """Place a LIMIT order (GTC) on Binance Futures Testnet.

    The order rests on the book until *price* is reached or it is cancelled.

    Args:
        client:   Authenticated :class:`BinanceFuturesClient` instance.
        symbol:   Trading pair, e.g. ``"BTCUSDT"``.
        side:     ``"BUY"`` or ``"SELL"``.
        quantity: Amount of base asset to trade.
        price:    Limit price.

    Returns:
        Normalised order response dict.

    Raises:
        ValueError: On invalid inputs.
        BinanceAPIException: On exchange-level errors.
        BinanceRequestException: On connectivity errors.
    """
    validate_symbol(symbol)
    validate_side(side)
    validate_quantity(quantity)
    validate_price(price)

    logger.info(
        "Placing LIMIT %s order | symbol=%s qty=%s price=%s",
        side, symbol, quantity, price,
    )

    try:
        raw = client.get_client().futures_create_order(
            symbol=symbol,
            side=side,
            type="LIMIT",
            quantity=quantity,
            price=price,
            timeInForce="GTC",
        )
        response = _format_response(raw)
        logger.info(
            "LIMIT order placed | orderId=%s status=%s price=%s",
            response["order_id"], response["status"], response["price"],
        )
        return response

    except BinanceAPIException as exc:
        logger.error("API error (LIMIT order): %s", exc, exc_info=True)
        raise
    except BinanceRequestException as exc:
        logger.error("Request error (LIMIT order): %s", exc, exc_info=True)
        raise
    except Exception as exc:
        logger.error("Unexpected error (LIMIT order): %s", exc, exc_info=True)
        raise


def place_stop_limit_order(
    client: BinanceFuturesClient,
    symbol: str,
    side: str,
    quantity: float,
    price: float,
    stop_price: float,
) -> Dict[str, Any]:
    """Place a STOP-LIMIT order on Binance Futures Testnet.

    Uses :meth:`BinanceFuturesClient.create_order_direct` to target
    ``/fapi/v1/order`` directly.  Some python-binance versions route
    ``type=STOP`` to the algo-order endpoint instead, which has stricter
    requirements; this method bypasses that routing.

    Price direction rules
    ---------------------
    - **BUY  STOP**: ``stop_price`` must be **above** the current market price
      (triggers on an upward breakout; ``price`` ≥ ``stop_price``).
    - **SELL STOP**: ``stop_price`` must be **below** the current market price
      (triggers on a downward move; ``price`` ≤ ``stop_price``).

    Minimum notional
    ----------------
    ``quantity × stop_price`` must meet the exchange minimum (≥ $50 for
    BTCUSDT on Testnet).  Use ``quantity ≥ 0.002`` to be safe near $50k BTC.

    Args:
        client:     Authenticated :class:`BinanceFuturesClient` instance.
        symbol:     Trading pair, e.g. ``"BTCUSDT"``.
        side:       ``"BUY"`` or ``"SELL"``.
        quantity:   Amount of base asset to trade.
        price:      Limit price executed after the stop triggers.
        stop_price: Trigger price.

    Returns:
        Normalised order response dict.

    Raises:
        ValueError: On invalid inputs.
        BinanceAPIException: On exchange-level errors (e.g. wrong price
            direction, notional too small).
        BinanceRequestException: On connectivity errors.
    """
    validate_symbol(symbol)
    validate_side(side)
    validate_quantity(quantity)
    validate_price(price, field_name="price")
    validate_price(stop_price, field_name="stop_price")

    logger.info(
        "Placing STOP_LIMIT %s order | symbol=%s qty=%s "
        "price=%s stopPrice=%s",
        side, symbol, quantity, price, stop_price,
    )

    try:
        raw = client.create_order_direct(
            symbol=symbol,
            side=side,
            type="STOP",           # Binance Futures STOP = stop-limit order
            quantity=quantity,
            price=price,
            stopPrice=stop_price,
            timeInForce="GTC",
        )
        response = _format_response(raw)
        logger.info(
            "STOP_LIMIT order placed | orderId=%s status=%s stopPrice=%s",
            response["order_id"], response["status"], response["stop_price"],
        )
        return response

    except BinanceAPIException as exc:
        logger.error("API error (STOP_LIMIT order): %s", exc, exc_info=True)
        raise
    except BinanceRequestException as exc:
        logger.error("Request error (STOP_LIMIT order): %s", exc, exc_info=True)
        raise
    except Exception as exc:
        logger.error("Unexpected error (STOP_LIMIT order): %s", exc, exc_info=True)
        raise
