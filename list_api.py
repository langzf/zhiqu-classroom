"""List all API endpoints from OpenAPI spec."""
import httpx
import json

r = httpx.get("http://localhost:8002/openapi.json")
data = r.json()
paths = data["paths"]

lines = []
for path in sorted(paths.keys()):
    methods = paths[path]
    for method in ("get", "post", "put", "delete", "patch"):
        if method in methods:
            detail = methods[method]
            op_id = detail.get("operationId", "?")
            tags = detail.get("tags", ["?"])
            tag = tags[0] if tags else "?"
            summary = detail.get("summary", "")
            lines.append(f"{method.upper():6s} {path:60s} op={op_id:40s} tag={tag:20s} {summary}")

print(f"\nTotal endpoints: {len(lines)}\n")
for line in lines:
    print(line)
