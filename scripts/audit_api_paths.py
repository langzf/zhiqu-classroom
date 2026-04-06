"""
API Path Audit Script
Extracts all backend endpoint paths and frontend API call paths,
then compares them for mismatches.
"""
import re
import os

PROJECT = r"C:\Users\18513\.openclaw\workspace\zhiqu-classroom"

# ─── Backend route extraction ───
# main.py mount config (manually mapped from reading the file):
MOUNTS = {
    "content_engine/router_admin.py": "/api/v1/admin",
    "content_engine/router_student.py": "/api/v1",
    "ai_tutor/router_admin.py": "/api/v1/admin",
    "ai_tutor/router_student.py": "/api/v1",
    "learning_orchestrator/router_admin.py": "/api/v1/admin",
    "learning_orchestrator/router_student.py": "/api/v1",
    "user_profile/router.py": "",  # has its own /api/v1/user prefix in APIRouter
}

def extract_backend_routes():
    """Extract all backend routes with full paths."""
    routes = []
    
    for rel_path, mount_prefix in MOUNTS.items():
        filepath = os.path.join(PROJECT, "services", rel_path)
        if not os.path.exists(filepath):
            print(f"  WARN: {filepath} not found")
            continue
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract router prefix
        prefix_match = re.search(r'APIRouter\(prefix=["\']([^"\']*)["\']', content)
        router_prefix = prefix_match.group(1) if prefix_match else ""
        
        # Extract all endpoint decorators
        pattern = r'@router\.(get|post|put|patch|delete)\(["\']([^"\']*)["\']'
        for match in re.finditer(pattern, content):
            method = match.group(1).upper()
            endpoint_path = match.group(2)
            full_path = mount_prefix + router_prefix + endpoint_path
            routes.append({
                "file": rel_path,
                "method": method,
                "path": full_path,
                "mount_prefix": mount_prefix,
                "router_prefix": router_prefix,
                "endpoint_path": endpoint_path,
            })
    
    return routes

def extract_frontend_api_calls(base_dir, client_base_url):
    """Extract all frontend API calls."""
    calls = []
    api_dir = os.path.join(base_dir, "src", "api")
    
    for filename in os.listdir(api_dir):
        if not filename.endswith('.ts') or filename == 'client.ts':
            continue
        
        filepath = os.path.join(api_dir, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Match patterns like: api.get('/path'), api.post('/path'), api.get(`/path/${id}`)
        # Also match: api.put, api.patch, api.delete
        pattern = r'api\.(get|post|put|patch|delete)\([`"\']([^`"\']*)'
        for match in re.finditer(pattern, content):
            method = match.group(1).upper()
            path = match.group(2)
            # Replace template literals ${...} with :param
            path = re.sub(r'\$\{[^}]+\}', ':param', path)
            full_path = client_base_url + path
            calls.append({
                "file": filename,
                "method": method,
                "path": full_path,
                "relative_path": path,
            })
    
    return calls


print("=" * 80)
print("BACKEND API ROUTES")
print("=" * 80)

backend_routes = extract_backend_routes()
for r in sorted(backend_routes, key=lambda x: (x['path'], x['method'])):
    print(f"  {r['method']:6s} {r['path']}")
    print(f"         src: {r['file']} | mount={r['mount_prefix']} router={r['router_prefix']} ep={r['endpoint_path']}")

print(f"\nTotal backend routes: {len(backend_routes)}")

print("\n" + "=" * 80)
print("ADMIN FRONTEND API CALLS")
print("=" * 80)

admin_calls = extract_frontend_api_calls(
    os.path.join(PROJECT, "admin"),
    "/api/v1"  # admin client.ts baseURL
)
for c in sorted(admin_calls, key=lambda x: (x['path'], x['method'])):
    print(f"  {c['method']:6s} {c['path']}")
    print(f"         src: {c['file']} | relative={c['relative_path']}")

print(f"\nTotal admin API calls: {len(admin_calls)}")

print("\n" + "=" * 80)
print("STUDENT APP FRONTEND API CALLS")
print("=" * 80)

app_calls = extract_frontend_api_calls(
    os.path.join(PROJECT, "app"),
    "/api/v1"  # app client.ts baseURL
)
for c in sorted(app_calls, key=lambda x: (x['path'], x['method'])):
    print(f"  {c['method']:6s} {c['path']}")
    print(f"         src: {c['file']} | relative={c['relative_path']}")

print(f"\nTotal student API calls: {len(app_calls)}")

# ─── Cross-reference ───
print("\n" + "=" * 80)
print("MISMATCH ANALYSIS")
print("=" * 80)

# Build a set of backend paths (method, path_pattern)
backend_set = set()
for r in backend_routes:
    # Normalize path params: {textbook_id} -> :param
    normalized = re.sub(r'\{[^}]+\}', ':param', r['path'])
    backend_set.add((r['method'], normalized))

def check_frontend(label, calls):
    print(f"\n--- {label} ---")
    missing = []
    matched = []
    for c in calls:
        normalized = c['path']
        key = (c['method'], normalized)
        if key in backend_set:
            matched.append(c)
        else:
            missing.append(c)
    
    if missing:
        print(f"  ❌ {len(missing)} frontend calls with NO matching backend route:")
        for m in missing:
            print(f"     {m['method']:6s} {m['path']}  (from {m['file']})")
    else:
        print(f"  ✅ All {len(matched)} frontend calls match backend routes")
    
    if matched:
        print(f"  ✅ {len(matched)} matched:")
        for m in matched:
            print(f"     {m['method']:6s} {m['path']}")

check_frontend("Admin Frontend", admin_calls)
check_frontend("Student App Frontend", app_calls)

# Also check: backend routes that no frontend calls
print("\n--- Backend routes with no frontend caller ---")
all_frontend_paths = set()
for c in admin_calls + app_calls:
    all_frontend_paths.add((c['method'], c['path']))

uncalled = []
for r in backend_routes:
    normalized = re.sub(r'\{[^}]+\}', ':param', r['path'])
    if (r['method'], normalized) not in all_frontend_paths:
        uncalled.append(r)

if uncalled:
    print(f"  ⚠️  {len(uncalled)} backend routes not called by any frontend:")
    for u in uncalled:
        print(f"     {u['method']:6s} {u['path']}  (from {u['file']})")
else:
    print("  ✅ All backend routes have at least one frontend caller")
