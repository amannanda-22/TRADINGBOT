"""
Input validation for order parameters.

Every function raises ``ValueError`` with a clear, actionable message when a
constraint is violated.  Callers (CLI and order functions) catch these and
surface them to the user before any network call is made.
"""

from typing import Union


# Valid values for enumerated fields
_VALID_SIDES = {"BUY", "SELL"}
_VALID_ORDER_TYPES = {"MARKET", "LIMIT", "STOP_LIMIT"}


def validate_symbol(symbol: str) -> None:
    """Validate a futures trading-pair symbol.

    Rules
    -----
    - Must be a non-empty string.
    - Must be entirely uppercase.
    - Must be at least 3 characters long.

    Args:
        symbol: Trading pair, e.g. ``"BTCUSDT"``.

    Raises:
        ValueError: When any rule is violated.
    """
    if not isinstance(symbol, str) or not symbol.strip():
        raise ValueError("Symbol must be a non-empty string (e.g. 'BTCUSDT').")
    if symbol != symbol.upper():
        raise ValueError(
            f"Symbol must be uppercase. Got '{symbol}', expected '{symbol.upper()}'."
        )
    if len(symbol) < 3:
        raise ValueError(
            f"Symbol '{symbol}' is too short to be a valid trading pair."
        )


def validate_side(side: str) -> None:
    """Validate order side.

    Args:
        side: ``"BUY"`` or ``"SELL"``.

    Raises:
        ValueError: When *side* is not a recognised value.
    """
    if side not in _VALID_SIDES:
        raise ValueError(
            f"Side must be one of {sorted(_VALID_SIDES)}. Got: '{side}'."
        )


def validate_order_type(order_type: str) -> None:
    """Validate order type.

    Args:
        order_type: ``"MARKET"``, ``"LIMIT"``, or ``"STOP_LIMIT"``.

    Raises:
        ValueError: When *order_type* is not a recognised value.
    """
    if order_type not in _VALID_ORDER_TYPES:
        raise ValueError(
            f"Order type must be one of {sorted(_VALID_ORDER_TYPES)}. Got: '{order_type}'."
        )


def validate_quantity(quantity: Union[int, float]) -> None:
    """Validate order quantity.

    Args:
        quantity: Amount of base asset to trade.  Must be a positive number.

    Raises:
        ValueError: When *quantity* is non-numeric or not strictly positive.
    """
    try:
        qty = float(quantity)
    except (TypeError, ValueError):
        raise ValueError(
            f"Quantity must be a numeric value. Got: '{quantity}'."
        )
    if qty <= 0:
        raise ValueError(
            f"Quantity must be a positive number greater than zero. Got: {qty}."
        )


def validate_price(price: Union[int, float], field_name: str = "price") -> None:
    """Validate a price field (limit price or stop price).

    Args:
        price:      Price value to validate.
        field_name: Human-readable name used in error messages
                    (e.g. ``"price"`` or ``"stop_price"``).

    Raises:
        ValueError: When *price* is non-numeric or not strictly positive.
    """
    try:
        p = float(price)
    except (TypeError, ValueError):
        raise ValueError(
            f"{field_name} must be a numeric value. Got: '{price}'."
        )
    if p <= 0:
        raise ValueError(
            f"{field_name} must be a positive number greater than zero. Got: {p}."
        )
