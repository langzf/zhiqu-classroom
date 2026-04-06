"""Dump full API spec grouped by tag, with request/response schemas."""
import httpx, json

r = httpx.get("http://localhost:8002/openapi.json")
data = r.json()
paths = data["paths"]
schemas = data.get("components", {}).get("schemas", {})

# Group by tag
by_tag = {}
for path in sorted(paths.keys()):
    methods = paths[path]
    for method in ("get", "post", "put", "delete", "patch"):
        if method not in methods:
            continue
        detail = methods[method]
        tag = detail.get("tags", ["untagged"])[0]
        op_id = detail.get("operationId", "?")
        summary = detail.get("summary", "")
        
        # Extract params
        params = []
        for p in detail.get("parameters", []):
            params.append(f"  {p['in']}:{p['name']}({p.get('schema',{}).get('type','?')})")
        
        # Extract request body schema ref
        req_body = ""
        rb = detail.get("requestBody", {})
        if rb:
            content = rb.get("content", {})
            for ct, cv in content.items():
                ref = cv.get("schema", {}).get("$ref", "")
                if ref:
                    req_body = ref.split("/")[-1]
                else:
                    req_body = json.dumps(cv.get("schema", {}))[:100]
        
        by_tag.setdefault(tag, []).append({
            "method": method.upper(),
            "path": path,
            "op_id": op_id,
            "summary": summary,
            "params": params,
            "req_body": req_body,
        })

for tag in sorted(by_tag.keys()):
    endpoints = by_tag[tag]
    print(f"\n{'='*80}")
    print(f"TAG: {tag} ({len(endpoints)} endpoints)")
    print(f"{'='*80}")
    for ep in endpoints:
        print(f"\n  {ep['method']:6s} {ep['path']}")
        print(f"         op: {ep['op_id']}")
        print(f"         summary: {ep['summary']}")
        if ep['req_body']:
            print(f"         body: {ep['req_body']}")
        for p in ep['params']:
            print(f"         param:{p}")
