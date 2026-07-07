"""Minimal client for the DriveThruRPG API.

Exposes two search calls -- ``search_library`` (the caller's purchased
products) and ``search_products`` (the general DriveThruRPG catalog) --
both returning full product details for each match (description, system,
title, publisher, author, DriveThruRPG product id).

Auth and endpoint shapes are based on the community client glujan/drpg
(https://github.com/glujan/drpg) and the drivethrurpg-calibre-plugin,
since DriveThruRPG has no official public API docs. Some field names were
determined empirically against the live API, since the applicationKey used
here is scoped to library/catalog-search endpoints only -- the single-item
`products/{id}` endpoint returns 403 regardless of auth and cannot be used.

`order_products` (the library listing) has no server-side title filter and
is capped at 50 items per page, with each page taking several seconds to
return. A library search that finds no early match must otherwise page
through the caller's entire library sequentially, which can take minutes
for a large library. To keep this reasonably fast, library pages are
fetched concurrently in small batches instead of one at a time.
"""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

import requests
from dotenv import load_dotenv

BASE_URL = "https://api.drivethrurpg.com/api/vBeta/"

_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0",
}

_LIBRARY_PAGE_SIZE = 50
_LIBRARY_BATCH_SIZE = 5


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

    def _fetch_library_page(self, page: int) -> list[dict]:
        return self._get(
            "order_products",
            getChecksum=1,
            getFilters=1,
            page=page,
            pageSize=_LIBRARY_PAGE_SIZE,
            library=1,
            archived=0,
        )

    @staticmethod
    def _library_item_to_details(item: dict) -> ProductDetails:
        product = item.get("product", {})
        description = product.get("description", {})
        return ProductDetails(
            product_id=item["productId"],
            order_product_id=item["orderProductId"],
            title=item["name"],
            description=description.get("shortDescription", ""),
            publisher=item["publisher"]["name"],
            authors=[],
            game_system=DriveThruRPGClient._game_system_from_filters(
                item.get("filters")
            ),
        )

    def search_library(self, query: str, max_values: int = 10) -> list[ProductDetails]:
        """Search the caller's purchased DriveThruRPG library for products
        whose title matches ``query``, returning at most ``max_values``
        results with full product details.

        Fetches pages of `order_products` in concurrent batches, since each
        page is an independent, slow network round trip and a non-matching
        query would otherwise have to page through the whole library
        sequentially (see module docstring).
        """
        query_lower = query.lower()
        matches: list[ProductDetails] = []
        next_page = 1
        with ThreadPoolExecutor(max_workers=_LIBRARY_BATCH_SIZE) as pool:
            while len(matches) < max_values:
                batch_pages = range(next_page, next_page + _LIBRARY_BATCH_SIZE)
                batch_results = list(pool.map(self._fetch_library_page, batch_pages))
                next_page += _LIBRARY_BATCH_SIZE

                reached_end = False
                for items in batch_results:
                    if not items:
                        reached_end = True
                        break
                    for item in items:
                        if query_lower in item["name"].lower():
                            matches.append(self._library_item_to_details(item))
                            if len(matches) >= max_values:
                                break
                    if len(matches) >= max_values:
                        break
                if reached_end or len(matches) >= max_values:
                    break
        return matches

    def search_products(self, query: str, max_values: int = 10) -> list[ProductDetails]:
        """Search the general DriveThruRPG catalog (not limited to the
        caller's library) for products whose title matches ``query``,
        returning at most ``max_values`` results with full product
        details."""
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
