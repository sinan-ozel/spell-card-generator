"""Tests for MCP (Model Context Protocol) endpoint functionality."""

import json
import os
import pytest
import requests


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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
