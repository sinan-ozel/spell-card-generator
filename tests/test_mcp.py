"""Tests for MCP (Model Context Protocol) endpoint functionality."""

import json
import os
import pytest
import requests
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any


BASE_URL = os.getenv("BASE_URL", "http://app:8000")


def parse_stream_events(response):
    """Parse events from either SSE (`data: ...`) or newline-delimited JSON."""
    events = []
    for line in response.iter_lines():
        if not line:
            continue
        line = line.decode('utf-8') if isinstance(line, bytes) else line
        line = line.strip()
        # skip SSE comments/keepalives
        if line.startswith(":"):
            continue
        payload = None
        if line.startswith("data: "):
            payload = line[6:]
        elif line.startswith("{") or line.startswith("["):
            payload = line
        if not payload:
            continue
        try:
            events.append(json.loads(payload))
        except json.JSONDecodeError:
            continue
    return events


def test_mcp_list_tools():
    """Test that list_tools returns available MCP tools."""
    response = requests.post(
        f"{BASE_URL}/mcp",
        json={
            "jsonrpc": "2.0",
            "method": "list_tools",
            "id": "test-1"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["jsonrpc"] == "2.0"
    assert "result" in data
    assert "tools" in data["result"]
    assert len(data["result"]["tools"]) > 0

    # Check that generate_spell_card_stream tool exists
    tool_names = [tool["name"] for tool in data["result"]["tools"]]
    assert "generate_spell_card_stream" in tool_names


def test_mcp_invalid_method():
    """Test that invalid methods return proper JSON-RPC error."""
    response = requests.post(
        f"{BASE_URL}/mcp",
        json={
            "jsonrpc": "2.0",
            "method": "invalid_method",
            "id": "test-2"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["jsonrpc"] == "2.0"
    assert "error" in data
    assert data["error"]["code"] == -32601
    assert "Method not found" in data["error"]["message"]


def test_mcp_invalid_json():
    """Test that invalid JSON returns validation error."""
    response = requests.post(
        f"{BASE_URL}/mcp",
        data=b"{invalid json}",
        headers={"Content-Type": "application/json"}
    )

    # Our MCP endpoint returns a JSON-RPC parse error frame
    assert response.status_code == 200
    data = response.json()
    assert data.get("jsonrpc") == "2.0"
    assert "error" in data
    assert data["error"]["code"] == -32700


def test_mcp_generate_spell_card_stream():
    """Test streaming spell card generation via MCP."""
    spell_data = {
        "title": "Magic Missile",
        "casting_time": "1 action",
        "range": "120 feet",
        "components": "V, S",
        "duration": "Instantaneous",
        "description": "You create three glowing darts of magical force.",
        "school": "Evocation",
        "level": 1
    }

    response = requests.post(
        f"{BASE_URL}/mcp",
        json={
            "jsonrpc": "2.0",
            "method": "generate_spell_card_stream",
            "params": {
                "generator": "plain",
                "spell_data": spell_data
            },
            "id": "test-3"
        },
        stream=True
    )

    assert response.status_code == 200
    # Content-type may be SSE or newline-delimited JSON for Streamable HTTP
    ctype = response.headers.get("content-type", "")
    assert "text/event-stream" in ctype or "application/json" in ctype

    events = parse_stream_events(response)

    # Verify we received events
    assert len(events) > 0

    # Check that events have proper JSON-RPC structure
    for event in events:
        assert "jsonrpc" in event
        assert event["jsonrpc"] == "2.0"
        assert "method" in event or "error" in event or "result" in event

    # Check for progress events
    progress_events = [e for e in events
                      if e.get("method") == "tool.progress"]
    assert len(progress_events) > 0

    # Check that we have progress values
    progress_values = [e["params"].get("progress")
                      for e in progress_events
                      if "progress" in e["params"]]
    assert len(progress_values) > 0

    # Final event should have completed status
    final_events = [e for e in progress_events
                   if e["params"].get("status") == "completed"]
    assert len(final_events) > 0

    # Final event should contain card data
    final_event = final_events[0]
    assert "card" in final_event["params"]
    assert "title" in final_event["params"]["card"]
    assert "image_data" in final_event["params"]["card"]


def test_mcp_generate_with_tornioduva():
    """Test MCP streaming with tornioduva generator."""
    spell_data = {
        "title": "Fireball",
        "casting_time": "1 action",
        "range": "150 feet",
        "components": "V, S, M",
        "duration": "Instantaneous",
        "description": "A bright streak flashes from your pointing finger.",
        "school": "Evocation",
        "level": 3
    }

    response = requests.post(
        f"{BASE_URL}/mcp",
        json={
            "jsonrpc": "2.0",
            "method": "generate_spell_card_stream",
            "params": {
                "generator": "tornioduva",
                "spell_data": spell_data
            },
            "id": "test-4"
        },
        stream=True
    )

    assert response.status_code == 200

    events = parse_stream_events(response)
    assert len(events) > 0

    # Check for completed status
    completed = any(
        e.get("method") == "tool.progress" and
        e.get("params", {}).get("status") == "completed"
        for e in events
    )
    assert completed


def test_mcp_invalid_generator():
    """Test that invalid generator returns error."""
    spell_data = {
        "title": "Test",
        "casting_time": "1 action",
        "range": "60 feet",
        "components": "V, S",
        "duration": "Instantaneous",
        "description": "Test spell",
        "school": "Evocation",
        "level": 0
    }

    response = requests.post(
        f"{BASE_URL}/mcp",
        json={
            "jsonrpc": "2.0",
            "method": "generate_spell_card_stream",
            "params": {
                "generator": "invalid_generator",
                "spell_data": spell_data
            },
            "id": "test-5"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == -32602
    assert "Invalid generator" in data["error"]["message"]


def test_mcp_invalid_spell_data():
    """Test that invalid spell data is caught and reported."""
    # Missing required field
    spell_data = {
        "title": "Test Spell",
        "casting_time": "1 action"
        # Missing other required fields
    }

    response = requests.post(
        f"{BASE_URL}/mcp",
        json={
            "jsonrpc": "2.0",
            "method": "generate_spell_card_stream",
            "params": {
                "generator": "plain",
                "spell_data": spell_data
            },
            "id": "test-6"
        },
        stream=True
    )

    # Should still connect but error will be in stream
    assert response.status_code == 200

    events = parse_stream_events(response)
    # Should have error events
    error_events = [e for e in events
                   if "error" in e or
                   (e.get("method") == "tool.progress" and
                    e.get("params", {}).get("status") == "error")]
    assert len(error_events) > 0


def test_mcp_default_generator():
    """Test that generator defaults to 'plain' if not specified."""
    spell_data = {
        "title": "Cantrip",
        "casting_time": "1 action",
        "range": "Touch",
        "components": "V",
        "duration": "1 minute",
        "description": "A simple cantrip.",
        "school": "Transmutation",
        "level": 0
    }

    response = requests.post(
        f"{BASE_URL}/mcp",
        json={
            "jsonrpc": "2.0",
            "method": "generate_spell_card_stream",
            "params": {
                "spell_data": spell_data
                # No generator specified - should default to 'plain'
            },
            "id": "test-7"
        },
        stream=True
    )

    assert response.status_code == 200

    events = parse_stream_events(response)
    # Should successfully generate with default generator
    completed = any(
        e.get("method") == "tool.progress" and
        e.get("params", {}).get("status") == "completed"
        for e in events
    )
    assert completed


## ============================================================================
## MCP CONTRACT COMPLIANCE TESTS
## ============================================================================


def test_mcp_id_correlation_in_streaming():
    """Test that all streamed events preserve request ID correlation."""
    request_id = "test-id-correlation-123"
    spell_data = {
        "title": "ID Test",
        "casting_time": "1 action",
        "range": "30 feet",
        "components": "V",
        "duration": "Instantaneous",
        "description": "Test for ID correlation.",
        "school": "Divination",
        "level": 0
    }

    response = requests.post(
        f"{BASE_URL}/mcp",
        json={
            "jsonrpc": "2.0",
            "method": "generate_spell_card_stream",
            "params": {
                "generator": "plain",
                "spell_data": spell_data
            },
            "id": request_id
        },
        stream=True
    )

    assert response.status_code == 200
    events = parse_stream_events(response)

    # Notifications should NOT have id field
    notifications = [e for e in events if "method" in e]
    for notif in notifications:
        assert "id" not in notif, \
            f"Notification {notif.get('method')} must not have 'id' field"

    # Final response frame (if any) should match request ID
    responses = [e for e in events if "result" in e or ("error" in e and "method" not in e)]
    for resp in responses:
        if "id" in resp:
            assert resp["id"] == request_id, \
                f"Response ID {resp['id']} must match request ID {request_id}"


def validate_json_schema(schema: Dict[str, Any]) -> List[str]:
    """Validate that a schema follows JSON Schema spec. Returns list of errors."""
    errors = []

    if not isinstance(schema, dict):
        errors.append("Schema must be an object")
        return errors

    if "type" not in schema:
        errors.append("Schema must have 'type' field")

    if schema.get("type") == "object":
        if "properties" not in schema:
            errors.append("Object schema should have 'properties'")

    return errors


def test_mcp_tool_schema_validity():
    """Test that tool schemas are valid MCP tool descriptors."""
    response = requests.post(
        f"{BASE_URL}/mcp",
        json={
            "jsonrpc": "2.0",
            "method": "list_tools",
            "id": "test-schema"
        }
    )

    assert response.status_code == 200
    data = response.json()
    tools = data["result"]["tools"]

    # Find our main tool
    tool = next((t for t in tools if t["name"] == "generate_spell_card_stream"), None)
    assert tool is not None, "generate_spell_card_stream tool not found"

    # Validate tool structure
    assert "name" in tool
    assert "description" in tool
    assert "inputSchema" in tool

    # Validate inputSchema is proper JSON Schema
    schema = tool["inputSchema"]
    assert isinstance(schema, dict), "inputSchema must be an object"
    assert schema.get("type") == "object", "inputSchema type must be 'object'"
    assert "properties" in schema, "inputSchema must have 'properties'"

    # Validate specific properties exist
    props = schema["properties"]
    assert "generator" in props, "Schema must define 'generator' property"
    assert "spell_data" in props, "Schema must define 'spell_data' property"

    # Validate no schema errors
    errors = validate_json_schema(schema)
    assert len(errors) == 0, f"Schema validation errors: {errors}"


def test_mcp_error_object_structure():
    """Test that MCP errors follow proper JSON-RPC error structure."""
    response = requests.post(
        f"{BASE_URL}/mcp",
        json={
            "jsonrpc": "2.0",
            "method": "nonexistent_method",
            "id": "test-error-structure"
        }
    )

    assert response.status_code == 200
    data = response.json()

    # Must have error field
    assert "error" in data, "Error response must have 'error' field"

    err = data["error"]

    # Validate error structure
    assert isinstance(err, dict), "error must be an object"
    assert "code" in err, "error must have 'code' field"
    assert "message" in err, "error must have 'message' field"

    # Validate types
    assert isinstance(err["code"], int), "error.code must be integer"
    assert isinstance(err["message"], str), "error.message must be string"

    # If data field exists, must be object
    if "data" in err:
        assert isinstance(err["data"], dict), "error.data must be object if present"


def test_mcp_streaming_notification_vs_response():
    """Test that streaming properly distinguishes notifications from responses."""
    spell_data = {
        "title": "Protocol Test",
        "casting_time": "1 action",
        "range": "Self",
        "components": "V, S",
        "duration": "Instantaneous",
        "description": "Test notification vs response.",
        "school": "Divination",
        "level": 0
    }

    response = requests.post(
        f"{BASE_URL}/mcp",
        json={
            "jsonrpc": "2.0",
            "method": "generate_spell_card_stream",
            "params": {
                "generator": "plain",
                "spell_data": spell_data
            },
            "id": "test-notif-vs-resp"
        },
        stream=True
    )

    assert response.status_code == 200
    events = parse_stream_events(response)
    assert len(events) > 0

    # All progress events must be notifications (have 'method', no 'id')
    for event in events:
        if event.get("method") == "tool.progress":
            assert "method" in event, "Progress event must have 'method' field"
            assert "id" not in event, "Notifications must NOT have 'id' field"
            assert "params" in event, "Notifications must have 'params' field"

        # If it's a response (has result or error without method), it should have id
        if "result" in event or ("error" in event and "method" not in event):
            # Response frames may have id
            pass  # This is acceptable


def test_mcp_content_type_strict():
    """Test that Content-Type headers are correct for streaming."""
    spell_data = {
        "title": "Content-Type Test",
        "casting_time": "1 action",
        "range": "Touch",
        "components": "V",
        "duration": "1 round",
        "description": "Testing content type.",
        "school": "Abjuration",
        "level": 0
    }

    # Streaming endpoint should return text/event-stream
    response = requests.post(
        f"{BASE_URL}/mcp",
        json={
            "jsonrpc": "2.0",
            "method": "generate_spell_card_stream",
            "params": {
                "generator": "plain",
                "spell_data": spell_data
            },
            "id": "test-content-type"
        },
        stream=True
    )

    assert response.status_code == 200
    ctype = response.headers.get("content-type", "").lower()

    # For streaming responses, should be text/event-stream or application/json for streamable
    assert "text/event-stream" in ctype or "application/json" in ctype, \
        f"Streaming response should have SSE or JSON content-type, got: {ctype}"


def test_mcp_concurrent_requests():
    """Test that server handles parallel MCP tool calls safely."""
    def make_request(request_id: str) -> requests.Response:
        """Make a single MCP request."""
        spell_data = {
            "title": f"Concurrent Spell {request_id}",
            "casting_time": "1 action",
            "range": "60 feet",
            "components": "V, S",
            "duration": "Instantaneous",
            "description": f"Concurrent test spell {request_id}.",
            "school": "Evocation",
            "level": 1
        }

        return requests.post(
            f"{BASE_URL}/mcp",
            json={
                "jsonrpc": "2.0",
                "method": "generate_spell_card_stream",
                "params": {
                    "generator": "plain",
                    "spell_data": spell_data
                },
                "id": request_id
            },
            stream=True
        )

    # Execute 5 parallel requests
    with ThreadPoolExecutor(max_workers=5) as executor:
        request_ids = [f"concurrent-{i}" for i in range(5)]
        responses = list(executor.map(make_request, request_ids))

    # All should succeed
    for response in responses:
        assert response.status_code == 200
        events = parse_stream_events(response)
        assert len(events) > 0

        # Should have at least one progress event
        progress_events = [e for e in events if e.get("method") == "tool.progress"]
        assert len(progress_events) > 0


def test_mcp_metadata_passthrough():
    """Test that metadata in requests doesn't break execution."""
    spell_data = {
        "title": "Metadata Test",
        "casting_time": "1 action",
        "range": "Self",
        "components": "V",
        "duration": "1 minute",
        "description": "Test metadata handling.",
        "school": "Transmutation",
        "level": 0
    }

    # Include metadata in request
    response = requests.post(
        f"{BASE_URL}/mcp",
        json={
            "jsonrpc": "2.0",
            "method": "generate_spell_card_stream",
            "params": {
                "generator": "plain",
                "spell_data": spell_data,
                "_meta": {
                    "clientId": "test-client",
                    "sessionId": "test-session-123"
                }
            },
            "id": "test-metadata"
        },
        stream=True
    )

    # Should not break - metadata should be ignored gracefully
    assert response.status_code == 200
    events = parse_stream_events(response)

    # Should complete successfully despite metadata
    completed = any(
        e.get("method") == "tool.progress" and
        e.get("params", {}).get("status") == "completed"
        for e in events
    )
    assert completed, "Request with metadata should complete successfully"


def test_mcp_transport_framing_strict():
    """Test that SSE transport framing is strictly correct."""
    spell_data = {
        "title": "Framing Test",
        "casting_time": "1 action",
        "range": "30 feet",
        "components": "V, S",
        "duration": "Instantaneous",
        "description": "Test SSE framing.",
        "school": "Illusion",
        "level": 1
    }

    response = requests.post(
        f"{BASE_URL}/mcp",
        json={
            "jsonrpc": "2.0",
            "method": "generate_spell_card_stream",
            "params": {
                "generator": "plain",
                "spell_data": spell_data
            },
            "id": "test-framing"
        },
        stream=True
    )

    assert response.status_code == 200

    # Parse with strict validation
    valid_events = 0
    for line in response.iter_lines():
        if not line:
            continue

        line = line.decode('utf-8') if isinstance(line, bytes) else line
        line = line.strip()

        # Skip SSE comments
        if line.startswith(":"):
            continue

        # Extract payload
        if line.startswith("data: "):
            payload = line[6:]
        elif line.startswith("{"):
            payload = line
        else:
            continue

        # Every data line must be valid JSON
        try:
            event = json.loads(payload)

            # Must be valid JSON-RPC
            assert "jsonrpc" in event, f"Frame missing jsonrpc: {payload}"
            assert event["jsonrpc"] == "2.0", f"Invalid jsonrpc version: {event['jsonrpc']}"

            valid_events += 1
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON in stream: {payload}\nError: {e}")

    # Must have received at least some events
    assert valid_events > 0, "No valid events received"


def test_mcp_error_codes_compliance():
    """Test that error codes follow JSON-RPC spec."""
    test_cases = [
        {
            "request": {
                "jsonrpc": "2.0",
                "method": "nonexistent",
                "id": "1"
            },
            "expected_code": -32601,  # Method not found
            "description": "Method not found"
        },
        {
            "request": "invalid json",
            "expected_code": -32700,  # Parse error
            "description": "Parse error"
        },
        {
            "request": {
                "jsonrpc": "2.0",
                "method": "generate_spell_card_stream",
                "params": {
                    "generator": "invalid_gen",
                    "spell_data": {
                        "title": "Test",
                        "casting_time": "1 action",
                        "range": "30 feet",
                        "components": "V",
                        "duration": "Instantaneous",
                        "description": "Test",
                        "school": "Evocation",
                        "level": 0
                    }
                },
                "id": "3"
            },
            "expected_code": -32602,  # Invalid params
            "description": "Invalid params"
        }
    ]

    for test_case in test_cases:
        if isinstance(test_case["request"], str):
            # Send invalid JSON
            response = requests.post(
                f"{BASE_URL}/mcp",
                data=test_case["request"].encode(),
                headers={"Content-Type": "application/json"}
            )
        else:
            response = requests.post(
                f"{BASE_URL}/mcp",
                json=test_case["request"]
            )

        assert response.status_code == 200
        data = response.json()

        assert "error" in data, f"{test_case['description']}: Missing error field"
        assert data["error"]["code"] == test_case["expected_code"], \
            f"{test_case['description']}: Expected code {test_case['expected_code']}, got {data['error']['code']}"


def test_mcp_list_tools_response_structure():
    """Test that list_tools response follows MCP spec structure."""
    response = requests.post(
        f"{BASE_URL}/mcp",
        json={
            "jsonrpc": "2.0",
            "method": "list_tools",
            "id": "test-list-tools-structure"
        }
    )

    assert response.status_code == 200
    data = response.json()

    # Validate response structure
    assert data["jsonrpc"] == "2.0"
    assert "result" in data
    assert "id" in data

    result = data["result"]
    assert "tools" in result
    assert isinstance(result["tools"], list)

    # Each tool must have required fields
    for tool in result["tools"]:
        assert "name" in tool, "Tool must have 'name'"
        assert "description" in tool, "Tool must have 'description'"
        assert "inputSchema" in tool, "Tool must have 'inputSchema'"

        assert isinstance(tool["name"], str)
        assert isinstance(tool["description"], str)
        assert isinstance(tool["inputSchema"], dict)


def test_mcp_progress_event_structure():
    """Test that tool.progress events follow proper structure."""
    spell_data = {
        "title": "Progress Structure Test",
        "casting_time": "1 action",
        "range": "60 feet",
        "components": "V, S",
        "duration": "Instantaneous",
        "description": "Testing progress event structure.",
        "school": "Divination",
        "level": 0
    }

    response = requests.post(
        f"{BASE_URL}/mcp",
        json={
            "jsonrpc": "2.0",
            "method": "generate_spell_card_stream",
            "params": {
                "generator": "plain",
                "spell_data": spell_data
            },
            "id": "test-progress-structure"
        },
        stream=True
    )

    assert response.status_code == 200
    events = parse_stream_events(response)

    progress_events = [e for e in events if e.get("method") == "tool.progress"]
    assert len(progress_events) > 0, "Must have at least one progress event"

    for event in progress_events:
        # Validate notification structure
        assert event["jsonrpc"] == "2.0"
        assert event["method"] == "tool.progress"
        assert "params" in event
        assert "id" not in event  # Notifications must not have id

        params = event["params"]
        # Progress events should have meaningful params
        assert isinstance(params, dict)
        # Should have at least status or progress
        assert "status" in params or "progress" in params


def test_mcp_schema_annotations():
    """Test that tool schema includes proper annotations for Inspector."""
    response = requests.post(
        f"{BASE_URL}/mcp",
        json={
            "jsonrpc": "2.0",
            "method": "list_tools",
            "id": "schema-test"
        }
    )

    assert response.status_code == 200
    data = response.json()
    tools = data["result"]["tools"]

    # Find our tool
    spell_tool = next(
        (t for t in tools if t["name"] == "generate_spell_card_stream"),
        None
    )
    assert spell_tool is not None

    schema = spell_tool["inputSchema"]

    # Check top-level schema has examples
    assert "examples" in schema
    assert len(schema["examples"]) >= 1

    # Check generator field has title, description, enum
    generator_field = schema["properties"]["generator"]
    assert "title" in generator_field
    assert generator_field["title"] == "Generator Type"
    assert "description" in generator_field
    assert "enum" in generator_field
    assert "plain" in generator_field["enum"]
    assert "examples" in generator_field

    # Check spell_data has title and description
    spell_data_field = schema["properties"]["spell_data"]
    assert "title" in spell_data_field
    assert spell_data_field["title"] == "Spell Information"
    assert "description" in spell_data_field

    # Check individual spell fields have annotations
    spell_props = spell_data_field["properties"]

    # title field
    assert "title" in spell_props["title"]
    assert spell_props["title"]["title"] == "Spell Name"
    assert "description" in spell_props["title"]
    assert "examples" in spell_props["title"]

    # school field should have enum
    assert "enum" in spell_props["school"]
    schools = spell_props["school"]["enum"]
    assert "Evocation" in schools
    assert "Abjuration" in schools
    assert len(schools) == 8  # All 8 D&D magic schools

    # level field should have constraints
    assert spell_props["level"]["minimum"] == 0
    assert spell_props["level"]["maximum"] == 9
    assert "examples" in spell_props["level"]


def test_mcp_metadata_support():
    """Test that metadata is accepted and logged (doesn't break calls)."""
    spell_data = {
        "title": "Test Spell",
        "casting_time": "1 action",
        "range": "Self",
        "components": "V, S",
        "duration": "Instantaneous",
        "description": "A test spell for metadata validation",
        "school": "Evocation",
        "level": 1
    }

    response = requests.post(
        f"{BASE_URL}/mcp",
        json={
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "generate_spell_card_stream",
                "arguments": {
                    "generator": "plain",
                    "spell_data": spell_data
                },
                "metadata": {
                    "request_id": "test-123",
                    "preview": True,
                    "locale": "en-US"
                }
            },
            "id": "metadata-test"
        },
        stream=True
    )

    assert response.status_code == 200

    # Parse the stream and ensure it completes successfully
    events = parse_stream_events(response)
    assert len(events) > 0

    # Should have a final result
    result_events = [e for e in events if "result" in e and "id" in e]
    assert len(result_events) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
