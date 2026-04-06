"""
Route mapping checker: compares backend FastAPI routes with frontend API calls.
Outputs a detailed report of mismatches.
"""
import re
import os

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
SERVICES_DIR = os.path.join(PROJECT_ROOT, "services")
APP_API_DIR = os.path.join(PROJECT_ROOT, "app", "src", "api")
ADMIN_API_DIR = os.path.join(PROJECT_ROOT, "admin", "src", "api")


def extract_backend_routes():
    """Extract all routes from backend router files and main.py."""
    # First, read main.py to get router mount prefixes
    main_py = os.path.join(SERVICES_DIR, "main.py")
    with open(main_py, "r", encoding="utf-8") as f:
        main_content = f.read()

    # Find all include_router calls with prefix
    # Pattern: app.include_router(xxx_router, prefix="/api/v1/xxx")
    mount_pattern = re.compile(
        r'app\.include_router\(\s*(\w+)\s*,\s*prefix\s*=\s*["\']([^"\']+)["\']',
        re.MULTILINE,
    )
    mounts = {}
    for match in mount_pattern.finditer(main_content):
        var_name = match.group(1)
        prefix = match.group(2)
        mounts[var_name] = prefix

    print("=" * 80)
    print("BACKEND ROUTER MOUNTS (from main.py)")
    print("=" * 80)
    for var, prefix in mounts.items():
        print(f"  {var} -> {prefix}")

    # Now find which router file each variable comes from
    # Pattern: from xxx import router as yyy
    import_pattern = re.compile(
        r'from\s+[\w.]+\s+import\s+(\w+)\s+as\s+(\w+)', re.MULTILINE
    )
    import_pattern2 = re.compile(
        r'from\s+([\w.]+)\s+import\s+(\w+)', re.MULTILINE
    )

    # Now extract routes from each router file
    router_files = []
    for root, dirs, files in os.walk(SERVICES_DIR):
        for f in files:
            if f.startswith("router") and f.endswith(".py"):
                router_files.append(os.path.join(root, f))

    all_backend_routes = {}  # full_path -> {method, file, line}

    for rf in router_files:
        with open(rf, "r", encoding="utf-8") as f:
            content = f.read()

        # Find the router prefix (APIRouter(prefix=...))
        router_prefix_match = re.search(
            r'APIRouter\([^)]*prefix\s*=\s*["\']([^"\']*)["\']', content
        )
        router_prefix = router_prefix_match.group(1) if router_prefix_match else ""

        # Find the router variable name
        router_var_match = re.search(r'(\w+)\s*=\s*APIRouter\(', content)
        router_var = router_var_match.group(1) if router_var_match else "router"

        # Find all route decorators
        route_pattern = re.compile(
            r'@\w+\.(get|post|put|delete|patch)\(\s*["\']([^"\']*)["\']',
            re.MULTILINE,
        )

        rel_path = os.path.relpath(rf, SERVICES_DIR)

        for match in route_pattern.finditer(content):
            method = match.group(1).upper()
            path = match.group(2)
            # The full path depends on how main.py mounts this router
            # We need to figure out the mount prefix for this file
            full_route_path = router_prefix + path
            line_no = content[: match.start()].count("\n") + 1
            key = f"{method} {full_route_path}"
            all_backend_routes[key] = {
                "method": method,
                "path": full_route_path,
                "router_prefix": router_prefix,
                "endpoint_path": path,
                "file": rel_path,
                "line": line_no,
            }

    # Now figure out the full mounted paths by matching router files to mount prefixes
    # Read main.py imports
    with open(main_py, "r", encoding="utf-8") as f:
        main_lines = f.readlines()

    # Build a map: variable_name -> module_path
    var_to_module = {}
    for line in main_lines:
        m = re.match(
            r'\s*from\s+([\w.]+)\s+import\s+(\w+)(?:\s+as\s+(\w+))?', line
        )
        if m:
            module = m.group(1)
            imported = m.group(2)
            alias = m.group(3) if m.group(3) else imported
            var_to_module[alias] = module

    print("\n" + "=" * 80)
    print("IMPORT MAP")
    print("=" * 80)
    for var, mod in var_to_module.items():
        prefix = mounts.get(var, "NOT MOUNTED")
        print(f"  {var} <- {mod} -> mounted at: {prefix}")

    # Now compute the real full paths
    # For each router file, find which mount prefix applies
    real_backend_routes = {}
    
    # Map module paths to router files
    module_to_file = {}
    for rf in router_files:
        rel = os.path.relpath(rf, SERVICES_DIR).replace(os.sep, "/")
        # Convert file path to module path: user_profile/router.py -> user_profile.router
        mod_path = rel.replace("/", ".").replace(".py", "")
        module_to_file[mod_path] = rf

    # For each mounted variable, find its router file and compute full paths
    for var_name, mount_prefix in mounts.items():
        if var_name not in var_to_module:
            print(f"  WARNING: {var_name} not found in imports")
            continue
        module_path = var_to_module[var_name]
        
        # Find the corresponding router file
        target_file = None
        for rf in router_files:
            rel = os.path.relpath(rf, SERVICES_DIR).replace(os.sep, "/")
            mod_path = rel.replace("/", ".").replace(".py", "")
            if mod_path == module_path:
                target_file = rf
                break

        if not target_file:
            print(f"  WARNING: No file found for module {module_path}")
            continue

        with open(target_file, "r", encoding="utf-8") as f:
            content = f.read()

        router_prefix_match = re.search(
            r'APIRouter\([^)]*prefix\s*=\s*["\']([^"\']*)["\']', content
        )
        router_prefix = router_prefix_match.group(1) if router_prefix_match else ""

        route_pattern = re.compile(
            r'@\w+\.(get|post|put|delete|patch)\(\s*["\']([^"\']*)["\']',
            re.MULTILINE,
        )

        rel_path = os.path.relpath(target_file, SERVICES_DIR)

        for match in route_pattern.finditer(content):
            method = match.group(1).upper()
            endpoint_path = match.group(2)
            full_path = mount_prefix + router_prefix + endpoint_path
            line_no = content[: match.start()].count("\n") + 1
            key = f"{method} {full_path}"
            real_backend_routes[key] = {
                "method": method,
                "full_path": full_path,
                "mount_prefix": mount_prefix,
                "router_prefix": router_prefix,
                "endpoint_path": endpoint_path,
                "file": rel_path,
                "line": line_no,
                "var_name": var_name,
            }

    print("\n" + "=" * 80)
    print("ALL BACKEND ROUTES (fully resolved)")
    print("=" * 80)
    for key in sorted(real_backend_routes.keys()):
        r = real_backend_routes[key]
        print(f"  {key}")
        print(f"    File: {r['file']}:{r['line']}")
        print(f"    Mount: {r['mount_prefix']} + Router: {r['router_prefix']} + Endpoint: {r['endpoint_path']}")

    return real_backend_routes


def extract_frontend_routes(api_dir, label):
    """Extract all API calls from frontend TypeScript files."""
    routes = {}

    if not os.path.exists(api_dir):
        print(f"  WARNING: {api_dir} does not exist")
        return routes

    for f in os.listdir(api_dir):
        if not f.endswith(".ts") and not f.endswith(".tsx"):
            continue
        if f == "client.ts":
            continue

        filepath = os.path.join(api_dir, f)
        with open(filepath, "r", encoding="utf-8") as fh:
            content = fh.read()

        # Match patterns like:
        # client.get('/path/...')
        # client.post('/path/...')
        # client.get(`/path/${var}`)
        # Also handle template literals
        api_pattern = re.compile(
            r'client\.(get|post|put|delete|patch)\s*[<(]\s*[`"\']([^`"\']+)[`"\']',
            re.MULTILINE,
        )

        for match in api_pattern.finditer(content):
            method = match.group(1).upper()
            path = match.group(2)
            line_no = content[: match.start()].count("\n") + 1

            # Normalize template literal variables: ${xxx} -> {xxx}
            normalized_path = re.sub(r'\$\{(\w+)\}', r'{\1}', path)
            # The frontend baseURL is /api/v1, so full path = /api/v1 + path
            full_path = "/api/v1" + normalized_path

            key = f"{method} {full_path}"
            routes[key] = {
                "method": method,
                "path": path,
                "full_path": full_path,
                "file": f,
                "line": line_no,
            }

    print(f"\n{'=' * 80}")
    print(f"FRONTEND ROUTES ({label})")
    print(f"{'=' * 80}")
    for key in sorted(routes.keys()):
        r = routes[key]
        print(f"  {key}")
        print(f"    File: {r['file']}:{r['line']}")
        print(f"    Raw path: {r['path']}")

    return routes


def normalize_path_for_comparison(path):
    """Normalize a path for comparison by replacing path params with placeholders."""
    # Backend uses {param_name}, frontend uses {param_name} (after normalization)
    return re.sub(r'\{[^}]+\}', '{*}', path)


def compare_routes(backend_routes, frontend_routes, label):
    """Compare frontend routes against backend routes."""
    print(f"\n{'=' * 80}")
    print(f"ROUTE COMPARISON: {label}")
    print(f"{'=' * 80}")

    # Normalize all backend routes for fuzzy matching
    normalized_backend = {}
    for key, val in backend_routes.items():
        method = val["method"]
        norm_path = normalize_path_for_comparison(val["full_path"])
        norm_key = f"{method} {norm_path}"
        normalized_backend[norm_key] = val

    # Also keep exact backend paths for exact matching
    exact_backend = {k: v for k, v in backend_routes.items()}

    mismatches = []
    matches = []
    
    for fe_key, fe_val in sorted(frontend_routes.items()):
        method = fe_val["method"]
        fe_full = fe_val["full_path"]
        fe_norm = normalize_path_for_comparison(fe_full)
        fe_norm_key = f"{method} {fe_norm}"

        # Try exact match first
        if fe_key in exact_backend:
            matches.append((fe_key, fe_val, exact_backend[fe_key]))
        # Try normalized match
        elif fe_norm_key in normalized_backend:
            matches.append((fe_key, fe_val, normalized_backend[fe_norm_key]))
        else:
            mismatches.append((fe_key, fe_val))

    print(f"\n✅ MATCHED ({len(matches)}):")
    for key, fe, be in matches:
        print(f"  {key}")
        print(f"    Frontend: {fe['file']}:{fe['line']} -> {fe['path']}")
        print(f"    Backend:  {be['file']}:{be['line']} -> {be['full_path']}")

    print(f"\n❌ FRONTEND CALLS WITH NO BACKEND MATCH ({len(mismatches)}):")
    if mismatches:
        for key, fe in mismatches:
            print(f"  {key}")
            print(f"    Frontend: {fe['file']}:{fe['line']} -> {fe['path']}")
            print(f"    Full resolved path: {fe['full_path']}")
            
            # Try to find closest backend match
            fe_norm = normalize_path_for_comparison(fe['full_path'])
            closest = []
            for be_key, be_val in backend_routes.items():
                be_norm = normalize_path_for_comparison(be_val['full_path'])
                # Simple similarity: check if paths share segments
                fe_segments = fe_norm.split("/")
                be_segments = be_norm.split("/")
                common = len(set(fe_segments) & set(be_segments))
                if common >= 3:
                    closest.append((be_key, be_val, common))
            closest.sort(key=lambda x: -x[2])
            if closest:
                print(f"    Closest backend match: {closest[0][0]} ({closest[0][1]['file']})")
    else:
        print("  (none)")

    # Also check backend routes not called by frontend
    print(f"\n⚠️  BACKEND ROUTES NOT CALLED BY {label.upper()} FRONTEND:")
    be_norm_set = set()
    for key, val in backend_routes.items():
        norm = normalize_path_for_comparison(val["full_path"])
        be_norm_set.add(f"{val['method']} {norm}")

    fe_norm_set = set()
    for key, val in frontend_routes.items():
        norm = normalize_path_for_comparison(val["full_path"])
        fe_norm_set.add(f"{val['method']} {norm}")

    uncalled = be_norm_set - fe_norm_set
    for u in sorted(uncalled):
        # Find the original backend route
        for key, val in backend_routes.items():
            norm = normalize_path_for_comparison(val["full_path"])
            if f"{val['method']} {norm}" == u:
                print(f"  {key} ({val['file']}:{val['line']})")
                break

    return mismatches


def main():
    print("ZHIQU CLASSROOM - ROUTE MAPPING CHECK")
    print("=" * 80)

    # Extract backend routes
    backend_routes = extract_backend_routes()

    # Extract student app frontend routes
    app_routes = extract_frontend_routes(APP_API_DIR, "Student App")

    # Extract admin frontend routes
    admin_routes = extract_frontend_routes(ADMIN_API_DIR, "Admin")

    # Filter backend routes for student vs admin
    student_backend = {}
    admin_backend = {}
    shared_backend = {}

    for key, val in backend_routes.items():
        fp = val["full_path"]
        fname = val["file"]
        if "student" in fname.lower() or "student" in fp.lower():
            student_backend[key] = val
        elif "admin" in fname.lower() or "admin" in fp.lower():
            admin_backend[key] = val
        else:
            # Shared routes (e.g., user_profile)
            shared_backend[key] = val
            student_backend[key] = val
            admin_backend[key] = val

    # Compare student app frontend vs student backend
    print("\n\n")
    app_mismatches = compare_routes(
        {**student_backend, **shared_backend}, app_routes, "Student App"
    )

    # Compare admin frontend vs admin backend
    print("\n\n")
    admin_mismatches = compare_routes(
        {**admin_backend, **shared_backend}, admin_routes, "Admin"
    )

    # Summary
    print("\n\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total backend routes: {len(backend_routes)}")
    print(f"Student app frontend calls: {len(app_routes)}")
    print(f"Admin frontend calls: {len(admin_routes)}")
    print(f"Student app mismatches: {len(app_mismatches)}")
    print(f"Admin mismatches: {len(admin_mismatches)}")

    if app_mismatches or admin_mismatches:
        print("\n⚠️  THERE ARE ROUTE MISMATCHES - SEE DETAILS ABOVE")
    else:
        print("\n✅ ALL FRONTEND ROUTES MATCH BACKEND ROUTES")


if __name__ == "__main__":
    main()