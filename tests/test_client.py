import responses as responses_lib

from dtrpg_mcp.client import BASE_URL

ORDER_PRODUCTS_PAGE_1 = [
    {
        "productId": 51416,
        "name": "GM Mastery: Inns & Taverns Essentials",
        "orderProductId": 10976233,
        "publisher": {"name": "Roleplaying Tips Publishing"},
        "filters": [
            {"filterId": 1, "parentFilterId": 2, "name": "Fantasy", "parentName": "Game System"},
        ],
        "product": {
            "description": {
                "name": "GM Mastery: Inns & Taverns Essentials",
                "shortDescription": "A guide to designing taverns.",
            }
        },
    },
    {
        "productId": 108028,
        "name": "Dungeon World",
        "orderProductId": 21063615,
        "publisher": {"name": "Burning Wheel"},
        "filters": None,
        "product": {
            "description": {
                "name": "Dungeon World",
                "shortDescription": "A game of fantasy adventure.",
            }
        },
    },
]

CATALOG_RESULTS = [
    {
        "productId": 141936,
        "description": {
            "name": "Bardo #1",
            "shortDescription": "A story about the afterlife.",
        },
        "publisher": {"name": "Creative Impulse"},
        "authors": ["Deegan Hockstein"],
        "storefrontPrimaryFilterValues": [],
    },
]


def test_search_library_filters_by_title_substring(client, mocked_responses):
    mocked_responses.add(
        responses_lib.GET,
        BASE_URL + "order_products",
        json=ORDER_PRODUCTS_PAGE_1,
        status=200,
    )
    mocked_responses.add(
        responses_lib.GET,
        BASE_URL + "order_products",
        json=[],
        status=200,
    )

    results = client.search("dungeon", in_library=1, max_values=10)

    assert len(results) == 1
    assert results[0].product_id == 108028
    assert results[0].title == "Dungeon World"
    assert results[0].order_product_id == 21063615
    assert results[0].description == "A game of fantasy adventure."
    assert results[0].publisher == "Burning Wheel"
    assert results[0].game_system is None


def test_search_library_extracts_game_system(client, mocked_responses):
    mocked_responses.add(
        responses_lib.GET,
        BASE_URL + "order_products",
        json=ORDER_PRODUCTS_PAGE_1,
        status=200,
    )
    mocked_responses.add(
        responses_lib.GET,
        BASE_URL + "order_products",
        json=[],
        status=200,
    )

    results = client.search("Inns", in_library=1, max_values=10)

    assert len(results) == 1
    assert results[0].game_system == "Fantasy"


def test_search_library_respects_max_values(client, mocked_responses):
    many_items = [
        {
            "productId": i,
            "name": f"Dungeon Book {i}",
            "orderProductId": 1000 + i,
            "publisher": {"name": "Pub"},
            "filters": None,
            "product": {"description": {"name": f"Dungeon Book {i}", "shortDescription": ""}},
        }
        for i in range(5)
    ]
    mocked_responses.add(
        responses_lib.GET,
        BASE_URL + "order_products",
        json=many_items,
        status=200,
    )

    results = client.search("dungeon", in_library=1, max_values=2)

    assert len(results) == 2


def test_search_catalog_when_not_in_library(client, mocked_responses):
    mocked_responses.add(
        responses_lib.GET,
        BASE_URL + "products",
        json=CATALOG_RESULTS,
        status=200,
    )

    results = client.search("bardo", in_library=0, max_values=10)

    assert len(results) == 1
    assert results[0].product_id == 141936
    assert results[0].order_product_id is None
    assert results[0].title == "Bardo #1"
    assert results[0].authors == ["Deegan Hockstein"]
    assert results[0].publisher == "Creative Impulse"


def test_reauthenticates_on_401(client, mocked_responses):
    mocked_responses.add(
        responses_lib.GET,
        BASE_URL + "order_products",
        json={"error": "expired"},
        status=401,
    )
    mocked_responses.add(
        responses_lib.POST,
        BASE_URL + "auth_key",
        json={"token": "new-token", "refreshToken": "r", "refreshTokenTTL": 1},
        status=200,
    )
    mocked_responses.add(
        responses_lib.GET,
        BASE_URL + "order_products",
        json=[],
        status=200,
    )

    results = client.search("anything", in_library=1, max_values=5)

    assert results == []
    assert client._session.headers["Authorization"] == "new-token"
