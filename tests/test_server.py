import pytest
from fastmcp import Client

from dtrpg_mcp.client import ProductDetails
from dtrpg_mcp.server import _get_client, mcp


@pytest.fixture(autouse=True)
def clear_client_cache():
    _get_client.cache_clear()
    yield
    _get_client.cache_clear()


@pytest.fixture
def fake_client(monkeypatch):
    class FakeClient:
        def __init__(self):
            self.library_calls = []
            self.product_calls = []

        def search_library(self, query, max_values=10):
            self.library_calls.append((query, max_values))
            return [
                ProductDetails(
                    product_id=1,
                    order_product_id=2,
                    title=f"Library result for {query}",
                    description="desc",
                    publisher="pub",
                    authors=[],
                    game_system="Fantasy",
                )
            ]

        def search_products(self, query, max_values=10):
            self.product_calls.append((query, max_values))
            return [
                ProductDetails(
                    product_id=1,
                    order_product_id=None,
                    title=f"Catalog result for {query}",
                    description="desc",
                    publisher="pub",
                    authors=["author"],
                    game_system=None,
                )
            ]

    instance = FakeClient()
    monkeypatch.setattr(
        "dtrpg_mcp.server.DriveThruRPGClient", lambda *a, **k: instance
    )
    return instance


@pytest.mark.asyncio
async def test_tools_are_registered():
    tools = await mcp.list_tools()
    names = sorted(t.name for t in tools)
    assert names == ["search_library", "search_products"]


@pytest.mark.asyncio
async def test_search_library_tool_call(fake_client):
    async with Client(mcp) as client:
        result = await client.call_tool(
            "search_library", {"query": "dungeon", "max_values": 3}
        )

    assert result.data == [
        {
            "product_id": 1,
            "order_product_id": 2,
            "title": "Library result for dungeon",
            "description": "desc",
            "publisher": "pub",
            "authors": [],
            "game_system": "Fantasy",
        }
    ]
    assert fake_client.library_calls == [("dungeon", 3)]


@pytest.mark.asyncio
async def test_search_products_tool_call(fake_client):
    async with Client(mcp) as client:
        result = await client.call_tool(
            "search_products", {"query": "bardo", "max_values": 5}
        )

    assert result.data[0]["order_product_id"] is None
    assert result.data[0]["game_system"] is None
    assert fake_client.product_calls == [("bardo", 5)]


@pytest.mark.asyncio
async def test_search_library_tool_defaults(fake_client):
    async with Client(mcp) as client:
        await client.call_tool("search_library", {"query": "x"})

    assert fake_client.library_calls == [("x", 10)]


@pytest.mark.asyncio
async def test_search_products_tool_defaults(fake_client):
    async with Client(mcp) as client:
        await client.call_tool("search_products", {"query": "x"})

    assert fake_client.product_calls == [("x", 10)]
