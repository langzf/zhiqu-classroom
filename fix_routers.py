import pathlib

# Fix content_engine/router_admin.py
p = pathlib.Path(r"C:\Users\18513\.openclaw\workspace\zhiqu-classroom\services\content_engine\router_admin.py")
txt = p.read_text(encoding="utf-8")
replacements = {
    "service.list_textbooks()": "service.get_textbooks()",
    "service.list_knowledge_points(": "service.get_knowledge_points(",
    "service.list_exercises(": "service.get_exercises(",
}
for old, new in replacements.items():
    if old in txt:
        txt = txt.replace(old, new)
        print(f"  Replaced: {old} -> {new}")
    else:
        print(f"  NOT FOUND: {old}")
p.write_text(txt, encoding="utf-8")
print("Done: content_engine/router_admin.py\n")

# Fix ai_tutor/router_admin.py
p2 = pathlib.Path(r"C:\Users\18513\.openclaw\workspace\zhiqu-classroom\services\ai_tutor\router_admin.py")
txt2 = p2.read_text(encoding="utf-8")
old2 = "service.list_conversations("
new2 = "service.get_conversations("
if old2 in txt2:
    txt2 = txt2.replace(old2, new2)
    print(f"  Replaced: {old2} -> {new2}")
else:
    print(f"  NOT FOUND: {old2}")
p2.write_text(txt2, encoding="utf-8")
print("Done: ai_tutor/router_admin.py")
