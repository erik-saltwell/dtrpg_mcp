"""FastMCP server exposing DriveThruRPG search over stdio."""

from __future__ import annotations

from dataclasses import asdict
from functools import lru_cache

from fastmcp import FastMCP

from dtrpg_mcp.client import DriveThruRPGClient

mcp = FastMCP("dtrpg-mcp")


@lru_cache(maxsize=1)
def _get_client() -> DriveThruRPGClient:
    """Lazily construct the API client on first tool call.

    Deferred (rather than built at import time) so the server can start,
    and report a clear tool-call error, even if DTRPG_API_KEY is missing
    or invalid -- rather than crashing on startup.
    """
    return DriveThruRPGClient()


@mcp.tool
def search_library(query: str, max_values: int = 10) -> list[dict]:
    """Search products the caller has already purchased in their
    DriveThruRPG library.

    Args:
        query: Text to match against product titles (case-insensitive
            substring match).
        max_values: Maximum number of results to return (default 10).

    Returns:
        A list of product detail objects, each with: product_id,
        order_product_id, title, description, publisher, authors, and
        game_system (null when not available).
    """
    client = _get_client()
    results = client.search_library(query, max_values=max_values)
    return [asdict(r) for r in results]


@mcp.tool
def search_products(query: str, max_values: int = 10) -> list[dict]:
    """Search the general public DriveThruRPG catalog for products, not
    limited to the caller's purchased library.

    Args:
        query: Text to match against product titles (keyword match).
        max_values: Maximum number of results to return (default 10).

    Returns:
        A list of product detail objects, each with: product_id,
        order_product_id (always null here, since these are not
        necessarily owned), title, description, publisher, authors, and
        game_system (null when not available).
    """
    client = _get_client()
    results = client.search_products(query, max_values=max_values)
    return [asdict(r) for r in results]


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
