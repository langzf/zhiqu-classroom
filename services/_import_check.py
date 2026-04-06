"""Quick import check for all backend modules."""
import sys, importlib, traceback

sys.path.insert(0, r"C:\Users\18513\.openclaw\workspace\zhiqu-classroom\services")

modules = [
    "config",
    "shared.response",
    "shared.exceptions",
    "infrastructure.persistence.models.base",
    "infrastructure.persistence.models.user",
    "infrastructure.persistence.models.content",
    "infrastructure.persistence.models.learning",
    "infrastructure.persistence.models.tutor",
    "interfaces.schemas.content",
    "interfaces.schemas.learning",
    "interfaces.schemas.user",
    "interfaces.schemas.tutor",
    "interfaces.api.deps",
    "application.services.user_service",
    "application.services.content_service",
    "application.services.learning_service",
    "application.services.learning_core_service",
    "application.services.tutor_service",
    "interfaces.api.auth.router",
    "interfaces.api.app.user",
    "interfaces.api.app.content",
    "interfaces.api.app.learning",
    "interfaces.api.app.tutor",
    "interfaces.api.admin.user",
    "interfaces.api.admin.content",
    "interfaces.api.admin.learning",
    "interfaces.api",
    "main",
]

ok = 0
fail = 0
for m in modules:
    try:
        importlib.import_module(m)
        print(f"  OK  {m}")
        ok += 1
    except Exception as e:
        print(f"FAIL  {m}")
        traceback.print_exc()
        print()
        fail += 1

print(f"\n--- {ok} OK, {fail} FAIL ---")
