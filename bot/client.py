"""
Binance Futures Testnet client wrapper.

Encapsulates authentication, connection setup, and direct order routing so
that the rest of the codebase never imports python-binance directly.
"""

import logging
import os
from typing import Any, Dict, Optional

from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceRequestException
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class BinanceFuturesClient:
    """Authenticated client pointed at the Binance Futures Testnet.

    API credentials are read from environment variables (via .env) unless
    supplied explicitly.  The underlying python-binance ``Client`` is created
    with ``testnet=True`` so futures calls route to
    ``https://testnet.binancefuture.com``.

    Args:
        api_key:    Testnet API key.  Falls back to ``BINANCE_API_KEY`` env var.
        api_secret: Testnet API secret.  Falls back to ``BINANCE_API_SECRET``.

    Raises:
        ValueError: When credentials are not found.
        BinanceAPIException: When the connection cannot be established.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
    ) -> None:
        self._api_key = api_key or os.getenv("BINANCE_API_KEY", "")
        self._api_secret = api_secret or os.getenv("BINANCE_API_SECRET", "")

        if not self._api_key or not self._api_secret:
            raise ValueError(
                "Binance API credentials not found. "
                "Set BINANCE_API_KEY and BINANCE_API_SECRET in your .env file."
            )

        self._client: Client = self._build_client()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_client(self) -> Client:
        """Instantiate and return a testnet-pointing python-binance Client."""
        try:
            client = Client(
                api_key=self._api_key,
                api_secret=self._api_secret,
                testnet=True,
            )
            logger.info("Binance Futures Testnet client initialized successfully")
            return client
        except (BinanceAPIException, BinanceRequestException) as exc:
            logger.error("Failed to initialize Binance client: %s", exc, exc_info=True)
            raise
        except Exception as exc:
            logger.error("Unexpected error building Binance client: %s", exc, exc_info=True)
            raise

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get_client(self) -> Client:
        """Return the raw python-binance Client (for MARKET/LIMIT orders).

        Returns:
            Authenticated ``binance.client.Client`` instance.
        """
        return self._client

    def create_order_direct(self, **params: Any) -> Dict[str, Any]:
        """Submit an order directly to ``/fapi/v1/order``.

        Some versions of python-binance route ``STOP`` order types to the
        algo-order endpoint instead of the regular order endpoint.  This
        method bypasses that routing and always targets ``/fapi/v1/order``,
        which is the correct endpoint for stop-limit orders on Binance Futures.

        Returns:
            Raw Binance API response dict.

        Raises:
            BinanceAPIException: On exchange-level errors.
        """
        return self._client._request_futures_api(
            "post", "order", signed=True, data=params
        )

    def get_order(self, symbol: str, order_id: int) -> Dict[str, Any]:
        """Fetch the current state of an existing order.

        Used to poll fill status after order placement, since the Binance
        Futures Testnet sometimes returns ``status=NEW`` for market orders
        in the create-order response before the matching engine processes them.

        Args:
            symbol:   Trading pair (e.g. ``"BTCUSDT"``).
            order_id: Binance order ID returned at placement.

        Returns:
            Raw order status dict from the Binance API.
        """
        return self._client.futures_get_order(symbol=symbol, orderId=order_id)

    def ping(self) -> bool:
        """Send a lightweight ping to the Futures Testnet.

        Returns:
            ``True`` if the exchange responded, ``False`` otherwise.
        """
        try:
            self._client.futures_ping()
            logger.info("Futures Testnet ping successful")
            return True
        except (BinanceAPIException, BinanceRequestException) as exc:
            logger.error("Ping failed: %s", exc, exc_info=True)
            return False

    def get_account_info(self) -> Dict[str, Any]:
        """Fetch and return futures account information.

        Returns:
            Raw account dict from the Binance API.

        Raises:
            BinanceAPIException: On API-level errors.
        """
        try:
            info = self._client.futures_account()
            logger.info("Fetched futures account info successfully")
            return info
        except (BinanceAPIException, BinanceRequestException) as exc:
            logger.error("Failed to fetch account info: %s", exc, exc_info=True)
            raise
