"""Оркестратор GitHub Actions: обходит реестр из 42 рядов + бюджет, обновляет data/*.json.

Гарантии:
  * падение одного парсера не валит сборку — ряд получает status='stale';
  * ранее собранные значения (в т.ч. импортированные из Excel) никогда не теряются;
  * data/manual_overrides.csv (code,period,value) имеет высший приоритет.
"""
import csv, json, os, sys, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
from common import DATA, now_msk
from sources import te_investing, cbonds, cbr, rosstat, misc

HERE = os.path.dirname(os.path.abspath(__file__))

DISPATCH = {
    "te_investing":     te_investing.fetch,
    "cbonds":           cbonds.fetch,
    "cbr_ibk":          cbr.fetch_ibk,
    "cbr_infl_exp":     cbr.fetch_infl_exp,
    "cbr_pb":           cbr.fetch_pb,
    "rosstat_price":    rosstat.fetch_price,
    "fedstat":          rosstat.fetch_fedstat,
    "rosstat_zpl":      rosstat.fetch_zpl,
    "rosstat_opttorg":  rosstat.fetch_opttorg,
    "rosstat_shipment": rosstat.fetch_shipment,
    "hh_stats":         misc.fetch_hh,
    "autostat":         misc.fetch_cars,
}


def overrides():
    p = os.path.join(DATA, "manual_overrides.csv")
    out = {}
    if os.path.exists(p):
        for r in csv.DictReader(open(p, encoding="utf-8")):
            if not r.get("code") or str(r["code"]).startswith("#"): continue
            try:
                out.setdefault(r["code"], {})[r["period"]] = float(str(r["value"]).replace(",", "."))
            except Exception:
                pass
    return out


def import_excel(db, path):
    """Разовый импорт/досыпка из makro-dashbord.xlsx, если файл положен в data/."""
    if not os.path.exists(path): return 0
    df = pd.read_excel(path, header=None)
    hdr, cols = [], []
    for c in range(2, 24):
        p = None
        try:
            p = pd.to_datetime(df.iloc[1, c]).strftime("%Y-%m")
        except Exception:
            pass
        if p: hdr.append(p); cols.append(c)
    titles = {s["meta"]["title"].lower(): code for code, s in db["series"].items()}
    n = 0
    for i in range(len(df)):
        name = str(df.iloc[i, 1]).strip().lower()
        code = titles.get(name)
        if not code: continue
        ratio = db["series"][code]["meta"]["unit"] == "%"
        for c, p in zip(cols, hdr):
            v = df.iloc[i, c]
            if pd.isna(v) or not isinstance(v, (int, float)): continue
            db["series"][code]["values"][p] = round(float(v)*(100 if ratio else 1),
                                                    db["series"][code]["meta"]["decimals"])
            n += 1
    return n


def main():
    registry = json.load(open(os.path.join(HERE, "registry.json"), encoding="utf-8"))
    db = json.load(open(os.path.join(DATA, "dashboard.json"), encoding="utf-8"))
    months, errors = db["months"], {}

    for code, meta in registry.items():
        s = db["series"].setdefault(code, {"meta": meta, "values": {m: None for m in months}})
        for m in months: s["values"].setdefault(m, None)
        fn = DISPATCH.get(meta.get("source_id"))
        if fn is None:
            s["status"] = "manual"; continue
        try:
            fresh = fn(meta)
            if not fresh: raise RuntimeError("парсер вернул пустой результат")
            for p, v in fresh.items():
                if p in s["values"]:
                    s["values"][p] = round(float(v), meta.get("decimals", 1))
            s["status"] = "ok"
        except Exception as e:                                    # noqa: BLE001
            s["status"] = "stale"; errors[code] = f"{type(e).__name__}: {e}"
            traceback.print_exc()

    import_excel(db, os.path.join(DATA, "makro-dashbord.xlsx"))

    for code, vals in overrides().items():
        if code in db["series"]:
            for p, v in vals.items():
                if p in db["series"][code]["values"]:
                    db["series"][code]["values"][p] = v
                    db["series"][code]["status"] = "manual"

    bp = os.path.join(DATA, "budget.json")
    if os.path.exists(bp):
        db["budget"] = json.load(open(bp, encoding="utf-8"))

    db["generated_at"] = now_msk()
    db["errors"] = errors
    json.dump(db, open(os.path.join(DATA, "dashboard.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    print(json.dumps({"errors": errors,
                      "filled": {k: sum(v is not None for v in s["values"].values())
                                 for k, s in db["series"].items()}}, ensure_ascii=False, indent=1))
    if len(errors) == len(registry):
        sys.exit(1)


if __name__ == "__main__":
    main()
