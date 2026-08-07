"""Собирает index.html: шаблон templates/dashboard.html + встроенный JSON."""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

db = json.load(open(os.path.join(ROOT, "data", "dashboard.json"), encoding="utf-8"))
tpl = open(os.path.join(ROOT, "templates", "dashboard.html"), encoding="utf-8").read()
html = tpl.replace("__PAYLOAD__", json.dumps(db, ensure_ascii=False, separators=(",", ":")))
open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8").write(html)
print("index.html:", len(html), "bytes;", len(db["series"]), "рядов")
