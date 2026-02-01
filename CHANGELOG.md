# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.0] - 2026-02-01

### Added
- **MCP (Model Context Protocol) support**: The server now implements the MCP specification
  - New `/mcp` JSON-RPC endpoint with Server-Sent Events (SSE) streaming
  - `list_tools` method to discover available MCP tools
  - `generate_spell_card_stream` tool for streaming spell card generation with real-time progress updates
  - Progress events during card generation (10%, 30%, 80%, 100%)
  - Base64-encoded image data in streaming responses
- Streaming generator functions (`generate_stream`) in both `plain` and `tornioduva` generators
- Comprehensive MCP test suite in `tests/test_mcp.py` with 8 test cases
- Docker Compose setup for running server with MCP Inspector (`mcp/docker-compose.yaml`)
- VS Code task: "run server with MCP Inspector"
- `sse-starlette` dependency for Server-Sent Events support

### Changed
- Server is now both a REST API and an MCP server
- Version bumped from 0.3.0 to 0.4.0

### Maintained
- Full backwards compatibility with existing REST API endpoints (`/v1/generate`, `/v1/generators`)
- All existing tests continue to pass
- Original generator functions remain unchanged

## [0.3.0] - Previous Release

### Features
- REST API for generating D&D spell cards
- Multiple card generators (plain, tornioduva)
- Asynchronous card generation with optional callback URLs
- Dockerized deployment
- FastAPI-based server with OpenAPI documentation

[0.4.0]: https://github.com/sinan-ozel/spell-card-generator/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/sinan-ozel/spell-card-generator/releases/tag/v0.3.0
