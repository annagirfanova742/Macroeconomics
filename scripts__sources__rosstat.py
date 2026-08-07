"""Росстат и ЕМИСС: цены, зарплаты, опт. торговля, отгрузка по видам деятельности."""
import re
import pandas as pd
from bs4 import BeautifulSoup
from common import get, num, to_period, excel_sheets, pairs

BASE = "https://rosstat.gov.ru"
PRICE = BASE + "/statistics/price"
ZPL = BASE + "/labor_market_employment_salaries"
OPT = BASE + "/statistics/opttorg"
SHIP = BASE + "/enterprise_industrial"


def _files(page, pat):
    soup = BeautifulSoup(get(page).decode("utf-8","ignore"), "lxml")
    out = []
    for a in soup.select("a[href]"):
        h, t = a["href"], a.get_text(" ", strip=True).lower()
        if h.lower().split("?")[0].endswith((".xlsx", ".xls")) and re.search(pat, t+" "+h.lower()):
            out.append((h if h.startswith("http") else BASE+h, t))
    return out


PRICE_PAT = {
    "ipc_yoy":      (r"к соответствующему периоду|к соответствующему месяцу", 90, 130),
    "ipc_mom":      (r"к предыдущему месяцу", 95, 106),
    "food_mom":     (r"продовольствен", 95, 106),
    "nonfood_mom":  (r"непродовольствен", 95, 106),
    "services_mom": (r"услуг", 95, 106),
}


def fetch_price(meta):
    """ИПЦ и его компоненты. Росстат публикует индексы (100 = база) -> переводим в %."""
    pat, lo, hi = PRICE_PAT[meta["key"]]
    for url, title in _files(PRICE, r"ипц|потребительск|цен"):
        try: sheets = excel_sheets(get(url))
        except Exception: continue
        for df in sheets:
            head = " ".join(str(x).lower() for x in df.head(30).values.ravel())
            if not re.search(pat, head): continue
            d = pairs(df, lo, hi)
            d = {k: round(v-100, 2) for k, v in d.items() if k >= "2024-01"}
            if len(d) > 6: return d
    return {}


def fetch_fedstat(meta):
    """Базовый ИПЦ — ЕМИСС, показатель 31074 (SDMX-выгрузка)."""
    url = f"https://www.fedstat.ru/indicator/dataGrid.do?id={meta['fedstat_id']}"
    try:
        raw = get(url)
        tables = pd.read_html(raw)
    except Exception:
        return {}
    for df in tables:
        d = pairs(df, 95, 130)
        if len(d) > 6:
            base = 100 if max(d.values()) > 50 else 0
            return {k: round(v-base, 2) for k, v in d.items()}
    return {}


def fetch_zpl(meta=None):
    """Номинальная начисленная зарплата, % г/г."""
    for url, _ in _files(ZPL, r"зараб|начислен|zpl|wage"):
        try:
            for df in excel_sheets(get(url)):
                d = {k: round(v, 1) for k, v in pairs(df, 90, 160).items() if k >= "2024-01"}
                if len(d) > 6:
                    return {k: round(v-100, 1) for k, v in d.items()}
        except Exception:
            continue
    return {}


def fetch_opttorg(meta=None):
    for url, _ in _files(OPT, r"опт|torg|динамик"):
        try:
            for df in excel_sheets(get(url)):
                d = {k: v for k, v in pairs(df, 60, 150).items() if k >= "2024-01"}
                if len(d) > 6:
                    return {k: round(v-100, 1) for k, v in d.items()}
        except Exception:
            continue
    return {}


def fetch_shipment(meta):
    """Отгрузка по видам деятельности: ищем строку по названию показателя/ОКВЭД."""
    title = meta["title"].lower().split(",")[0].strip()
    words = [w for w in re.split(r"[\s()]+", title) if len(w) > 4][:3]
    if not words: return {}
    for url, _ in _files(SHIP, r"отгруж|производств|индекс"):
        try: sheets = excel_sheets(get(url))
        except Exception: continue
        for df in sheets:
            for i, row in df.iterrows():
                label = " ".join(str(x).lower() for x in row.values[:3])
                if not all(w in label for w in words): continue
                hdr = None
                for j in range(max(0, i-8), i):
                    if sum(1 for c in df.iloc[j].values if to_period(c)) >= 3:
                        hdr = df.iloc[j].values; break
                if hdr is None: continue
                d = {}
                for c, h in enumerate(hdr):
                    p = to_period(h); v = num(row.values[c]) if c < len(row.values) else None
                    if p and v is not None:
                        d.setdefault(p, round(v-100, 1) if v > 40 else round(v, 1))
                if len(d) > 3: return d
    return {}
