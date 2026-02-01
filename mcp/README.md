# MCP Inspector Setup

This directory contains a Docker Compose configuration for running the Spell Card Generator server alongside the MCP Inspector for visual testing and debugging.

## Services

- **spell-card-server**: The spell card generator API with MCP endpoint at `/mcp`
- **mcp-inspector**: Visual tool for testing and debugging MCP servers

## Usage

### Start both services:

```bash
cd mcp
docker compose up --build
```

Or use the VS Code task: `Terminal` → `Run Task` → `run server with MCP Inspector`

### Access the services:

**Important:** The MCP Inspector requires an auth token. Check the docker logs for the full URL, which will look like:
```
http://localhost:6274/?MCP_PROXY_AUTH_TOKEN=<token>
```

- **MCP Inspector UI**: http://localhost:6274 (copy full URL with token from logs)
- **Spell Card Generator API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **MCP Endpoint**: http://localhost:8000/mcp

### Using the MCP Inspector:

1. Open http://localhost:5173 in your browser
2. Configure the connection to: `http://spell-card-server:8000/mcp`
3. Use the inspector to:
   - List available tools (`list_tools` method)
   - Test the `generate_spell_card_stream` tool
   - View streaming progress updates in real-time
   - Inspect the generated spell card data

### Stop the services:

```bash
docker compose down
```

## Testing the MCP Endpoint

You can also test the MCP endpoint directly with curl:

```bash
# List available tools
curl -N -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "list_tools",
    "id": "1"
  }'

# Generate a spell card (streaming)
curl -N -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "generate_spell_card_stream",
    "params": {
      "generator": "plain",
      "spell_data": {
        "title": "Fireball",
        "casting_time": "1 action",
        "range": "150 feet",
        "components": "V, S, M",
        "duration": "Instantaneous",
        "description": "A bright streak flashes from your pointing finger to a point you choose within range and then blossoms with a low roar into an explosion of flame.",
        "school": "Evocation",
        "level": 3
      }
    },
    "id": "2"
  }'
```

The `-N` flag tells curl not to buffer the output, so you'll see progress events as they stream in.
