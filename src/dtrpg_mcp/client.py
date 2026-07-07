"""Minimal client for the DriveThruRPG API.

Covers a single scenario: searching for products (either in the caller's
purchased library, or the general DriveThruRPG catalog) and returning full
product details for each match (description, system, title, publisher,
author, DriveThruRPG product id).

Auth and endpoint shapes are based on the community client glujan/drpg
(https://github.com/glujan/drpg) and the drivethrurpg-calibre-plugin,
since DriveThruRPG has no official public API docs. Some field names were
determined empirically against the live API, since the applicationKey used
here is scoped to library/catalog-search endpoints only -- the single-item
`products/{id}` endpoint returns 403 regardless of auth and cannot be used.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

import requests
from dotenv import load_dotenv

BASE_URL = "https://api.drivethrurpg.com/api/vBeta/"

_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0",
}


@dataclass
class ProductDetails:
    product_id: int
    order_product_id: int | None
    title: str
    description: str
    publisher: str
    authors: list[str] = field(default_factory=list)
    game_system: str | None = None


class DriveThruRPGClient:
    """Thin wrapper around the DriveThruRPG vBeta API."""

    def __init__(self, api_key: str | None = None):
        if api_key is None:
            load_dotenv()
            api_key = os.environ["DTRPG_API_KEY"]
        self._api_key = api_key
        self._session = requests.Session()
        self._session.headers.update(_HEADERS)
        self._authenticate()

    def _authenticate(self) -> None:
        resp = self._session.post(
            BASE_URL + "auth_key", params={"applicationKey": self._api_key}
        )
        resp.raise_for_status()
        token = resp.json()["token"]
        self._session.headers["Authorization"] = token

    def _get(self, path: str, **params) -> dict:
        resp = self._session.get(BASE_URL + path, params=params)
        if resp.status_code == 401:
            self._authenticate()
            resp = self._session.get(BASE_URL + path, params=params)
        resp.raise_for_status()
        return resp.json()

    @staticmethod
    def _game_system_from_filters(filters: list[dict] | None) -> str | None:
        if not filters:
            return None
        return next(
            (f["name"] for f in filters if f.get("parentName") == "Game System"),
            None,
        )

    def _search_library(self, query: str, max_values: int) -> list[ProductDetails]:
        query_lower = query.lower()
        matches: list[ProductDetails] = []
        page = 1
        while len(matches) < max_values:
            items = self._get(
                "order_products",
                getChecksum=1,
                getFilters=1,
                page=page,
                pageSize=50,
                library=1,
                archived=0,
            )
            if not items:
                break
            for item in items:
                if query_lower in item["name"].lower():
                    product = item.get("product", {})
                    description = product.get("description", {})
                    matches.append(
                        ProductDetails(
                            product_id=item["productId"],
                            order_product_id=item["orderProductId"],
                            title=item["name"],
                            description=description.get("shortDescription", ""),
                            publisher=item["publisher"]["name"],
                            authors=[],
                            game_system=self._game_system_from_filters(
                                item.get("filters")
                            ),
                        )
                    )
                    if len(matches) >= max_values:
                        break
            page += 1
        return matches

    def _search_catalog(self, query: str, max_values: int) -> list[ProductDetails]:
        items = self._get(
            "products",
            name=query,
            page=1,
            pageSize=max_values,
            siteId=10,
            status=1,
        )
        matches = []
        for item in items[:max_values]:
            matches.append(
                ProductDetails(
                    product_id=item["productId"],
                    order_product_id=None,
                    title=item["description"]["name"],
                    description=item["description"].get("shortDescription", ""),
                    publisher=item["publisher"]["name"],
                    authors=item.get("authors", []),
                    game_system=self._game_system_from_filters(
                        item.get("storefrontPrimaryFilterValues")
                    ),
                )
            )
        return matches

    def search(
        self, query: str, in_library: int = 1, max_values: int = 10
    ) -> list[ProductDetails]:
        """Search for products whose title matches ``query``, returning at
        most ``max_values`` results with full product details.

        If ``in_library`` is truthy (default), searches the caller's
        purchased library. Otherwise searches the general DriveThruRPG
        catalog.
        """
        if in_library:
            return self._search_library(query, max_values)
        return self._search_catalog(query, max_values)
