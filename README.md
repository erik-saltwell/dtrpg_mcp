# dtrpg-mcp

An [MCP](https://modelcontextprotocol.io) server that lets an LLM search your
[DriveThruRPG](https://www.drivethrurpg.com) library and the public
DriveThruRPG catalog for tabletop RPG products, returning structured details
(title, description, publisher, authors, game system, and DriveThruRPG
product id) for each match.

It speaks MCP over **stdio** and exposes a single tool, `search`.

## Requirements

- Python >= 3.12
- A DriveThruRPG **Application Key** (see [Getting an API key](#getting-a-drivethrurpg-api-key) below)

## Installation

```bash
pip install dtrpg-mcp
```

or, to run it without installing anything permanently:

```bash
uvx dtrpg-mcp
```

## Configuration

The server needs one environment variable:

| Variable         | Required | Description                                                             |
| ---------------- | -------- | ------------------------------------------------------------------------ |
| `DTRPG_API_KEY`  | Yes      | Your DriveThruRPG Application Key, used to authenticate against the API. |

You can set it directly in your shell/MCP client config, or drop a `.env`
file next to your project (the server walks up from its own install
location looking for `.env`, so a `.env` in your working directory or a
parent of it will be picked up automatically via `python-dotenv`).

### Getting a DriveThruRPG API key

1. Log in to [drivethrurpg.com](https://www.drivethrurpg.com).
2. Go to **My Account -> Application Keys** (or open
   `https://www.drivethrurpg.com/en/account/application-keys` directly).
3. Click **Generate New Key**, give it a name (e.g. "dtrpg-mcp"), and create it.
4. Copy the generated key — this is your `DTRPG_API_KEY`.

The key only grants access to your library and to the public product
catalog search; it does not expose your payment details or let anything
make purchases on your behalf.

## Using it with an MCP client

Add it to your client's MCP server config. For example, in Claude Desktop's
`claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "dtrpg": {
      "command": "uvx",
      "args": ["dtrpg-mcp"],
      "env": {
        "DTRPG_API_KEY": "your-application-key-here"
      }
    }
  }
}
```

If installed via `pip` instead of `uvx`, use `"command": "dtrpg-mcp"` with
no args.

## Tools

### `search`

Search DriveThruRPG for products matching a title query, returning full
product details for each match.

**Parameters**

| Name          | Type    | Default | Description                                                                                          |
| ------------- | ------- | ------- | ------------------------------------------------------------------------------------------------------ |
| `query`       | string  | —       | Text to match against product titles.                                                                |
| `in_library`  | boolean | `true`  | If `true`, search only products already purchased in your library. If `false`, search the public DriveThruRPG catalog instead. |
| `max_values`  | integer | `10`    | Maximum number of results to return.                                                                  |

**Returns** a list of objects with:

| Field               | Description                                                                 |
| ------------------- | ---------------------------------------------------------------------------- |
| `product_id`        | The DriveThruRPG product id.                                                |
| `order_product_id`  | The id of your specific purchased order/product; `null` for catalog (not-owned) results. |
| `title`              | Product title.                                                              |
| `description`        | A short description/blurb of the product.                                   |
| `publisher`          | Publisher name.                                                             |
| `authors`            | List of author names (only populated for catalog search results — DriveThruRPG's library endpoint does not include author data). |
| `game_system`        | Game system tag, when DriveThruRPG's API surfaces one for the product; otherwise `null`. |

**Example calls**

Search your own library for anything with "dungeon" in the title:

```json
{"query": "dungeon"}
```

Search the public catalog (not just your library) for "bardo", capped to 5 results:

```json
{"query": "bardo", "in_library": false, "max_values": 5}
```

## Notes on the DriveThruRPG API

DriveThruRPG does not publish official API documentation. This client's
endpoint usage was reverse-engineered from the community projects
[glujan/drpg](https://github.com/glujan/drpg) and
[quickwick/drivethrurpg-calibre-plugin](https://github.com/quickwick/drivethrurpg-calibre-plugin),
and verified empirically against the live API. Notably, the per-product
detail endpoint (`GET products/{id}`) returns `403` for Application Keys
like the one this tool uses (it appears to require a different auth scope),
so `search` builds product details from the library (`order_products`) and
catalog search (`products`) list endpoints instead, both of which work with
a standard Application Key.

## Development

```bash
uv sync
uv run pytest
```

Run the server directly for manual/stdio testing:

```bash
uv run dtrpg-mcp
```
