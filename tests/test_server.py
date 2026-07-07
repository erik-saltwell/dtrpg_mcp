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
            self.calls = []

        def search(self, query, in_library=1, max_values=10):
            self.calls.append((query, in_library, max_values))
            return [
                ProductDetails(
                    product_id=1,
                    order_product_id=2 if in_library else None,
                    title=f"Result for {query}",
                    description="desc",
                    publisher="pub",
                    authors=["author"],
                    game_system="Fantasy" if in_library else None,
                )
            ]

    instance = FakeClient()
    monkeypatch.setattr(
        "dtrpg_mcp.server.DriveThruRPGClient", lambda *a, **k: instance
    )
    return instance


@pytest.mark.asyncio
async def test_search_tool_is_registered():
    tools = await mcp.list_tools()
    names = [t.name for t in tools]
    assert names == ["search"]


@pytest.mark.asyncio
async def test_search_tool_library_call(fake_client):
    async with Client(mcp) as client:
        result = await client.call_tool(
            "search", {"query": "dungeon", "in_library": True, "max_values": 3}
        )

    assert result.data == [
        {
            "product_id": 1,
            "order_product_id": 2,
            "title": "Result for dungeon",
            "description": "desc",
            "publisher": "pub",
            "authors": ["author"],
            "game_system": "Fantasy",
        }
    ]
    assert fake_client.calls == [("dungeon", 1, 3)]


@pytest.mark.asyncio
async def test_search_tool_catalog_call(fake_client):
    async with Client(mcp) as client:
        result = await client.call_tool(
            "search", {"query": "bardo", "in_library": False, "max_values": 5}
        )

    assert result.data[0]["order_product_id"] is None
    assert result.data[0]["game_system"] is None
    assert fake_client.calls == [("bardo", 0, 5)]


@pytest.mark.asyncio
async def test_search_tool_defaults(fake_client):
    async with Client(mcp) as client:
        await client.call_tool("search", {"query": "x"})

    assert fake_client.calls == [("x", 1, 10)]
