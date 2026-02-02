# MCP Schema Annotations Guide

This document explains the schema annotations added to the spell card generator MCP tool.

## Schema Features

### 1. Field Descriptions & Human-Readable Labels

The tool schema now includes:

| Schema Key    | Purpose                                    | Example                           |
| ------------- | ------------------------------------------ | --------------------------------- |
| `title`       | Label shown in MCP Inspector UI            | "Spell Name", "Generator Type"    |
| `description` | Help text displayed under each field       | "How long the spell takes to cast"|

### 2. Enum Dropdowns

Fields with fixed options use `enum` for dropdown menus:

- **`generator`**: Automatically populated with available generators (`plain`, `tornioduva`, etc.)
- **`school`**: All 8 D&D magic schools (Abjuration, Conjuration, etc.)

### 3. Examples

Examples help users understand expected values:

- **Field-level examples**: Multiple example values shown for each field
- **Tool-level examples**: Complete "Use Example" button in Inspector with two pre-filled spells:
  - **Fireball** (Level 3 Evocation using `plain` generator)
  - **Shield** (Level 1 Abjuration using `tornioduva` generator)

### 4. Validation Constraints

- **`level`**: `minimum: 0, maximum: 9` (cantrip to 9th level)
- **Required fields**: All spell properties marked as required

### 5. Metadata Support

The server now accepts optional metadata in tool calls for:

- Request tracing
- Authentication hints
- Client preferences
- Debug information

**Metadata locations** (all supported):
```json
{
  "method": "tools/call",
  "params": {
    "name": "generate_spell_card_stream",
    "arguments": {...},
    "metadata": {"request_id": "abc123", "preview": true}
  }
}
```

Or within params:
```json
{
  "method": "generate_spell_card_stream",
  "params": {
    "generator": "plain",
    "spell_data": {...},
    "_meta": {"request_id": "abc123"}
  }
}
```

Metadata is logged but not required for operation.

## Using in MCP Inspector

### With Examples

1. Connect Inspector to your server
2. Select `generate_spell_card_stream` tool
3. Click **"Use Example"** button
4. Choose Fireball or Shield
5. Form auto-fills with example data
6. Click **"Call Tool"** to generate

### Manual Entry

1. Select generator from dropdown (plain/tornioduva)
2. Fill spell fields with guidance from descriptions
3. Select school from dropdown (Evocation, Abjuration, etc.)
4. Set level slider (0-9)
5. Add optional metadata pairs if needed

## Testing Metadata

Example request with metadata:

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "generate_spell_card_stream",
    "arguments": {
      "generator": "plain",
      "spell_data": {
        "title": "Test Spell",
        "casting_time": "1 action",
        "range": "Self",
        "components": "V, S",
        "duration": "Instantaneous",
        "description": "A test spell for metadata",
        "school": "Evocation",
        "level": 1
      }
    },
    "metadata": {
      "request_id": "test-123",
      "user_role": "admin",
      "preview": true,
      "locale": "en-US"
    }
  },
  "id": "1"
}
```

Check server logs for: `Request metadata: {'request_id': 'test-123', ...}`

## Next Steps

Consider adding:
- **Character limits**: `maxLength` for title/description
- **Pattern validation**: Regex for components format (V, S, M)
- **Conditional fields**: Different schemas per generator
- **Internationalization**: Translated titles/descriptions
