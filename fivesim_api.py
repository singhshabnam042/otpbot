"""
fivesim_api.py — 5sim.net API wrapper
All API calls to 5sim.net are centralised here.

Docs: https://5sim.net/docs
"""

import logging
import time
from typing import Any, Optional

import requests

import config

logger = logging.getLogger(__name__)


class FiveSimAPI:
    """Clean wrapper around the 5sim.net REST API."""

    BASE_URL = config.FIVESIM_BASE_URL

    def __init__(self, api_key: str = config.FIVESIM_API_KEY) -> None:
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.api_key}",
                "Accept": "application/json",
            }
        )

    # ─────────────────────────────────────────
    # Internal helpers
    # ─────────────────────────────────────────

    def _get(self, path: str, params: Optional[dict] = None, auth: bool = True) -> Any:
        """
        Make a GET request.
        If auth=False the Authorization header is omitted (guest endpoints).
        """
        url = f"{self.BASE_URL}{path}"
        headers = {}
        if not auth:
            # Guest endpoints don't need auth
            headers["Authorization"] = ""

        for attempt in range(1, 4):          # up to 3 attempts (exponential back-off)
            try:
                resp = self.session.get(url, params=params, headers=headers, timeout=15)
                resp.raise_for_status()
                return resp.json()
            except requests.exceptions.HTTPError as exc:
                logger.warning("HTTP error on attempt %d for %s: %s", attempt, url, exc)
                if resp.status_code in (429, 500, 502, 503, 504):
                    time.sleep(2 ** attempt)
                    continue
                raise
            except requests.exceptions.RequestException as exc:
                logger.warning("Request error on attempt %d for %s: %s", attempt, url, exc)
                time.sleep(2 ** attempt)
        raise RuntimeError(f"Failed to GET {url} after 3 attempts")

    # ─────────────────────────────────────────
    # User / account endpoints
    # ─────────────────────────────────────────

    def get_balance(self) -> float:
        """
        GET /v1/user/profile
        Returns the account balance as a float (USD).
        """
        data = self._get("/v1/user/profile")
        return float(data.get("balance", 0.0))

    # ─────────────────────────────────────────
    # Price / availability endpoints
    # ─────────────────────────────────────────

    def get_prices(self, product: str = "google") -> dict:
        """
        GET /v1/guest/prices?product=<product>
        Returns a nested dict:
          { country: { operator: { cost: float, count: int, rate: float } } }
        """
        # Guest endpoint — no auth needed
        data = self._get("/v1/guest/prices", params={"product": product}, auth=False)
        return data  # already the nested dict

    def find_cheapest_options(
        self,
        product: str = "google",
        max_price_cents: int = config.MAX_PRICE,
        min_stock: int = config.MIN_STOCK,
    ) -> list[dict]:
        """
        Parse all prices and return a sorted list (cheapest first) of options that:
          - cost <= max_price_cents (in cents)
          - have at least min_stock numbers available

        Each element: { "country": str, "operator": str, "cost": float, "count": int }
        """
        prices = self.get_prices(product=product)
        options: list[dict] = []

        for country, operators in prices.items():
            if not isinstance(operators, dict):
                continue
            for operator, info in operators.items():
                if not isinstance(info, dict):
                    continue
                cost_usd: float = float(info.get("cost", 999))
                count: int = int(info.get("count", 0))
                cost_cents: float = cost_usd * 100

                if cost_cents <= max_price_cents and count >= min_stock:
                    options.append(
                        {
                            "country": country,
                            "operator": operator,
                            "cost": cost_usd,
                            "count": count,
                        }
                    )

        # Sort by price (cheapest first), then by count descending (more stock = better)
        options.sort(key=lambda x: (x["cost"], -x["count"]))
        return options

    # ─────────────────────────────────────────
    # Order management endpoints
    # ─────────────────────────────────────────

    def buy_number(
        self, country: str, operator: str, product: str = "google"
    ) -> dict:
        """
        GET /v1/user/buy/activation/{country}/{operator}/{product}
        Buys a fresh activation number.
        Returns the order dict from 5sim.net.
        """
        path = f"/v1/user/buy/activation/{country}/{operator}/{product}"
        return self._get(path)

    def check_order(self, order_id: int) -> dict:
        """
        GET /v1/user/check/{order_id}
        Returns current order status including any received SMS.
        """
        return self._get(f"/v1/user/check/{order_id}")

    def cancel_order(self, order_id: int) -> dict:
        """
        GET /v1/user/cancel/{order_id}
        Cancels the order and triggers a refund.
        """
        return self._get(f"/v1/user/cancel/{order_id}")

    def finish_order(self, order_id: int) -> dict:
        """
        GET /v1/user/finish/{order_id}
        Marks the order as finished.
        """
        return self._get(f"/v1/user/finish/{order_id}")

    # ─────────────────────────────────────────
    # SMS helpers
    # ─────────────────────────────────────────

    def get_sms(self, order_id: int) -> list[dict]:
        """
        Calls check_order and extracts the 'sms' list.
        Returns a list of SMS dicts: [{ "text": str, "code": str, "created_at": str }, ...]
        """
        order = self.check_order(order_id)
        return order.get("sms", []) or []

    def buy_best_number(
        self,
        product: str = "google",
        max_price_cents: int = config.MAX_PRICE,
        min_stock: int = config.MIN_STOCK,
        max_retries: int = config.MAX_RETRIES,
    ) -> dict:
        """
        High-level helper: find cheapest options and try to buy one.
        Auto-retries up to max_retries times with next cheapest option.

        Returns the purchased order dict on success.
        Raises RuntimeError if all attempts fail.
        """
        options = self.find_cheapest_options(
            product=product,
            max_price_cents=max_price_cents,
            min_stock=min_stock,
        )

        if not options:
            raise RuntimeError(
                f"No numbers available under ${max_price_cents/100:.2f}. "
                "Please try again later."
            )

        tried: list[str] = []
        for option in options[:max_retries]:
            country = option["country"]
            operator = option["operator"]
            tried.append(f"{country}/{operator}")
            try:
                logger.info(
                    "Trying to buy number: country=%s operator=%s cost=$%.4f count=%d",
                    country,
                    operator,
                    option["cost"],
                    option["count"],
                )
                order = self.buy_number(country=country, operator=operator, product=product)
                if order.get("id"):
                    logger.info("Successfully bought order id=%s", order["id"])
                    return order
            except Exception as exc:
                logger.warning("Failed buying %s/%s: %s", country, operator, exc)

        raise RuntimeError(
            f"Could not buy a number after trying: {', '.join(tried)}. "
            "Try again later or increase MAX_PRICE."
        )
