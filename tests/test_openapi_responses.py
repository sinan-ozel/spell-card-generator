import pytest
import requests
import os

BASE_URL = os.getenv("BASE_URL", "http://app:8000")
OPENAPI_URL = f"{BASE_URL}/openapi.json"


def resolve_ref(ref, components):
    """Resolve a $ref in the OpenAPI schema."""
    if not ref.startswith("#/components/schemas/"):
        raise ValueError(f"Unsupported $ref: {ref}")
    schema_name = ref.split("/")[-1]
    return components[schema_name]


def build_example_from_schema(schema, components):
    """Recursively build an example from a schema definition."""
    if "$ref" in schema:
        schema = resolve_ref(schema["$ref"], components)
    if "example" in schema:
        return schema["example"]
    if schema.get("type") == "object":
        example = {}
        for prop, prop_schema in schema.get("properties", {}).items():
            example[prop] = build_example_from_schema(prop_schema, components)
        return example
    if schema.get("type") == "array":
        item_schema = schema.get("items", {})
        return [build_example_from_schema(item_schema, components)]
    # Fallback for simple types
    return schema.get("example", None)


def get_openapi_endpoints():
    """Yield (method, path, example) for each endpoint with a 200 response."""
    resp = requests.get(OPENAPI_URL)
    resp.raise_for_status()
    openapi = resp.json()
    components = openapi.get("components", {}).get("schemas", {})
    for path, methods in openapi["paths"].items():
        for method, details in methods.items():
            responses = details.get("responses", {})
            if "200" in responses:
                example = {}
                if "requestBody" in details:
                    content = details["requestBody"].get("content", {})
                    for media_type, media_details in content.items():
                        # Try to resolve $ref in schema
                        schema = media_details.get("schema", {})
                        if schema:
                            example = build_example_from_schema(schema, components)
                        # If there is a direct example, prefer it
                        if "example" in media_details:
                            example = media_details["example"]
                        elif "examples" in media_details:
                            first = next(iter(media_details["examples"].values()))
                            example = first.get("value", {})
                yield method, path, example


@pytest.mark.parametrize("method,path,example", list(get_openapi_endpoints()))
def test_openapi_200_responses(method, path, example):
    """
    Automatically checks that all documented endpoints with a 200 response
    in the OpenAPI spec actually return a 200 status code.
    """
    assert example, f"No example found for {method.upper()} {path}"
    url = f"{BASE_URL}{path}"
    if method == "get":
        resp = requests.get(url)
    elif method == "post":
        resp = requests.post(url, json=example)
    else:
        pytest.skip(f"Method {method.upper()} not supported for endpoint {url}")

    assert resp.status_code == 200, (
        f"Endpoint {method.upper()} {url} did not return 200. "
        f"Returned {resp.status_code}. Response: {resp.text}"

# TODO: Add another test where we remove one of the keys from the example, and assert 400 or 422.
    )