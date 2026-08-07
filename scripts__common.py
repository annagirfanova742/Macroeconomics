"""Общие утилиты парсеров: HTTP с кэшем, разбор дат и чисел, чтение Excel."""
import hashlib, io, json, os, re, time, datetime as dt
import pandas as pd
import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
CACHE = os.path.join(ROOT, ".cache")
os.makedirs(CACHE, exist_ok=True)

HEADERS = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/127.0 Safari/537.36"),
           "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8"}

MONTHS = {"январ":1,"феврал":2,"март":3,"апрел":4,"ма":5,"июн":6,"июл":7,
          "август":8,"сентябр":9,"октябр":10,"ноябр":11,"декабр":12}


def get(url, ttl=6*3600, method="GET", **kw):
    key = hashlib.md5((method+url+json.dumps(kw, sort_keys=True, default=str)).encode()).hexdigest()
    p = os.path.join(CACHE, key)
    if os.path.exists(p) and time.time()-os.path.getmtime(p) < ttl:
        return open(p, "rb").read()
    err = None
    for i in range(3):
        try:
            r = requests.request(method, url, headers=HEADERS, timeout=60, **kw)
            r.raise_for_status()
            open(p, "wb").write(r.content)
            return r.content
        except Exception as e:                                  # noqa: BLE001
            err = e; time.sleep(2**i*2)
    raise RuntimeError(f"{method} {url}: {err}")


def period(y, m):
    return f"{int(y):04d}-{int(m):02d}"


def to_period(x):
    """Любую дату/подпись приводим к 'YYYY-MM'."""
    if isinstance(x, (dt.date, dt.datetime, pd.Timestamp)):
        return period(x.year, x.month)
    s = str(x).lower().replace("\xa0", " ").strip()
    m = re.search(r"(20\d{2})[-./](\d{1,2})(?!\d)", s)
    if m: return period(m.group(1), m.group(2))
    m = re.search(r"(\d{1,2})[./](20\d{2})", s)
    if m: return period(m.group(2), m.group(1))
    m = re.search(r"(\d{1,2})[./](\d{1,2})[./](20\d{2})", s)
    if m: return period(m.group(3), m.group(2))
    y = re.search(r"(20\d{2})", s)
    if y:
        for stem, num in MONTHS.items():
            if stem in s: return period(y.group(1), num)
    return None


def num(x):
    if x is None: return None
    if isinstance(x, (int, float)) and not isinstance(x, bool):
        return float(x)
    s = str(x).replace("\xa0","").replace(" ","").replace("%","")
    s = s.replace("−","-").replace("–","-").replace(",",".")
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    return float(m.group()) if m else None


def excel_sheets(raw):
    xl = pd.ExcelFile(io.BytesIO(raw))
    return [xl.parse(s, header=None) for s in xl.sheet_names]


def pairs(df, lo=-1e9, hi=1e9):
    """Ищем пары (период, число) построчно и постолбцово — устойчиво к ориентации."""
    out = {}
    for frame in (df, df.T):
        for _, row in frame.iterrows():
            cells = list(row.values)
            for i, c in enumerate(cells):
                p = to_period(c)
                if not p: continue
                for c2 in cells[i+1:]:
                    v = num(c2)
                    if v is not None and lo < v < hi:
                        out.setdefault(p, v); break
    return out


def to_pct(d, ratio=False):
    """ratio=True -> доли (0.06) превращаем в проценты."""
    return {k: (v*100 if ratio else v) for k, v in d.items()}


def now_msk():
    return (dt.datetime.utcnow()+dt.timedelta(hours=3)).strftime("%d.%m.%Y %H:%M МСК")
