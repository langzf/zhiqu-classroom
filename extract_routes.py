import re
import os

os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "services"))

# main.py mount config:
# user_router -> no prefix (router itself has /api/v1/user)
# content_admin -> prefix=/api/v1/admin
# tutor_admin -> prefix=/api/v1/admin
# learning_admin -> prefix=/api/v1/admin
# content_student -> prefix=/api/v1
# tutor_student -> prefix=/api/v1
# learning_student -> prefix=/api/v1

mount_prefixes = {
    "user_profile/router.py": "",
    "content_engine/router_admin.py": "/api/v1/admin",
    "content_engine/router_student.py": "/api/v1",
    "ai_tutor/router_admin.py": "/api/v1/admin",
    "ai_tutor/router_student.py": "/api/v1",
    "learning_orchestrator/router_admin.py": "/api/v1/admin",
    "learning_orchestrator/router_student.py": "/api/v1",
}

print("=" * 90)
print("PART 1: ALL BACKEND ROUTES (mount_prefix + router_prefix + endpoint)")
print("=" * 90)

all_backend = []

for filepath, mount_prefix in mount_prefixes.items():
    with open(filepath, "r", encoding="utf-8") as fh:
        content = fh.read()

    m = re.search(r"APIRouter\([^)]*prefix\s*=\s*[\"']([^\"']*)[\"']", content)
    router_prefix = m.group(1) if m else ""

    routes = re.findall(
        r"@\w+\.(get|post|put|delete|patch)\(\s*[\"']([^\"']*)[\"']", content
    )

    for method, endpoint_path in routes:
        full = mount_prefix + router_prefix + endpoint_path
        method_upper = method.upper()
        all_backend.append((method_upper, full, filepath, router_prefix, endpoint_path))
        print(f"  {method_upper:6s} {full:60s}  <- {filepath} (router:{router_prefix})")

# ─── Frontend routes ───
print()
print("=" * 90)
print("PART 2: FRONTEND API CALLS")
print("=" * 90)

frontend_base = "/api/v1"

frontend_dirs = {
    "Student App": os.path.join(os.path.dirname(os.path.abspath(__file__)), "app", "src", "api"),
    "Admin": os.path.join(os.path.dirname(os.path.abspath(__file__)), "admin", "src", "api"),
}

all_frontend = {}

for label, api_dir in frontend_dirs.items():
    all_frontend[label] = []
    print(f"\n--- {label} ({api_dir}) ---")
    if not os.path.exists(api_dir):
        print("  DIRECTORY NOT FOUND!")
        continue
    for fname in sorted(os.listdir(api_dir)):
        if fname == "client.ts" or not fname.endswith(".ts"):
            continue
        fpath = os.path.join(api_dir, fname)
        with open(fpath, "r", encoding="utf-8") as fh:
            content = fh.read()

        # Match: client.get<Type>('/path') or client.get<Type>(`/path`)
        # Also match: client.get('/path'), client.post(`/path`)
        pattern = re.compile(r"client\.(get|post|put|delete|patch)\s*(?:<[^>]*>)?\s*\(\s*[`\"']([^`\"']+)[`\"']")
        for m in pattern.finditer(content):
            method = m.group(1).upper()
            raw_path = m.group(2)
            # Normalize template literals: ${xxx} -> {xxx}
            norm_path = re.sub(r"\$\{(\w+)\}", r"{\1}", raw_path)
            full_path = frontend_base + norm_path
            line_no = content[: m.start()].count("\n") + 1
            all_frontend[label].append((method, full_path, fname, line_no, raw_path))
            print(f"  {method:6s} {full_path:60s}  <- {fname}:{line_no}")

# Also check for fetch() calls (SSE endpoints)
for label, api_dir in frontend_dirs.items():
    for fname in sorted(os.listdir(api_dir)):
        if fname == "client.ts" or not fname.endswith(".ts"):
            continue
        fpath = os.path.join(api_dir, fname)
        with open(fpath, "r", encoding="utf-8") as fh:
            content = fh.read()
        # fetch(`${baseURL}/admin/tutor/...`)
        fetch_pattern = re.compile(r"fetch\(\s*`\$\{[^}]+\}([^`]+)`")
        for m in fetch_pattern.finditer(content):
            raw_path = m.group(1)
            full_path = frontend_base + raw_path.split("${")[0]  # handle any remaining template vars
            norm_path = re.sub(r"\$\{(\w+)\}", r"{\1}", raw_path)
            full_path = frontend_base + norm_path
            line_no = content[: m.start()].count("\n") + 1
            all_frontend[label].append(("POST(SSE)", full_path, fname, line_no, raw_path))
            print(f"  {'SSE':6s} {full_path:60s}  <- {fname}:{line_no} (fetch/SSE)")


# ─── Comparison ───
print()
print("=" * 90)
print("PART 3: ROUTE COMPARISON")
print("=" * 90)

def normalize(path):
    """Replace path params with {*} for fuzzy matching."""
    return re.sub(r"\{[^}]+\}", "{*}", path)

backend_set = {}
for method, full, fpath, rprefix, epath in all_backend:
    norm = normalize(full)
    key = f"{method} {norm}"
    backend_set[key] = (method, full, fpath)

for label, fe_routes in all_frontend.items():
    print(f"\n--- {label} ---")
    matched = []
    mismatched = []

    for method, full, fname, line, raw in fe_routes:
        norm = normalize(full)
        # For SSE, match as POST
        check_method = "POST" if method == "POST(SSE)" else method
        key = f"{check_method} {norm}"
        if key in backend_set:
            be = backend_set[key]
            matched.append((method, full, fname, line, be))
        else:
            mismatched.append((method, full, fname, line, raw))

    print(f"\n  MATCHED ({len(matched)}):")
    for method, full, fname, line, be in matched:
        print(f"    {method:6s} {full}")
        print(f"           FE: {fname}:{line}  ->  BE: {be[2]}")

    print(f"\n  MISMATCHED ({len(mismatched)}):")
    if mismatched:
        for method, full, fname, line, raw in mismatched:
            print(f"    {method:6s} {full}")
            print(f"           FE: {fname}:{line} (raw: {raw})")
            # Try to find closest backend route
            norm = normalize(full)
            candidates = []
            for bk, bv in backend_set.items():
                bmethod, bfull, bfile = bv
                bnorm = normalize(bfull)
                # Check if same method and similar path
                check_method = "POST" if method == "POST(SSE)" else method
                if bmethod == check_method:
                    # Count common segments
                    fe_segs = norm.strip("/").split("/")
                    be_segs = bnorm.strip("/").split("/")
                    common = sum(1 for a, b in zip(fe_segs, be_segs) if a == b)
                    if common >= 3:
                        candidates.append((bfull, bfile, common))
            candidates.sort(key=lambda x: -x[2])
            if candidates:
                print(f"           Closest BE: {candidates[0][0]} ({candidates[0][1]})")
            else:
                print(f"           NO CLOSE MATCH FOUND")
    else:
        print("    (none - all matched!)")

# Backend routes not called by any frontend
print(f"\n--- Backend routes not called by any frontend ---")
all_fe_keys = set()
for label, fe_routes in all_frontend.items():
    for method, full, fname, line, raw in fe_routes:
        check_method = "POST" if method == "POST(SSE)" else method
        norm = normalize(full)
        all_fe_keys.add(f"{check_method} {norm}")

for key, (method, full, fpath) in sorted(backend_set.items()):
    if key not in all_fe_keys:
        print(f"  {method:6s} {full:60s}  ({fpath})")

print()
print("=" * 90)
print("DONE")
print("=" * 90)
