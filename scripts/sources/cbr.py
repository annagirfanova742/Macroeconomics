"""Банк России: ИБК, инфляционные ожидания, платёжный баланс."""
import re
from bs4 import BeautifulSoup
from common import get, num, to_period, excel_sheets, pairs

BASE = "https://cbr.ru"


def _files(page, exts=(".xlsx", ".xls", ".csv")):
    soup = BeautifulSoup(get(page).decode("utf-8","ignore"), "lxml")
    out = []
    for a in soup.select("a[href]"):
        h = a["href"]
        if h.lower().split("?")[0].endswith(exts):
            out.append(((BASE+h) if h.startswith("/") else h, a.get_text(" ", strip=True)))
    return out


def fetch_ibk(meta=None):
    """Индикатор бизнес-климата: файл с динамикой на странице «Мониторинг предприятий»."""
    for url, name in _files(BASE+"/analytics/dkp/monitoring/"):
        if not re.search(r"ибк|бизнес|climate|мониторинг|monitoring", (name+url).lower()): continue
        try:
            for df in excel_sheets(get(url)):
                d = {k: v for k, v in pairs(df, -30, 30).items() if k >= "2024-01"}
                if len(d) > 6: return d
        except Exception:
            continue
    return {}


def fetch_infl_exp(meta):
    """Ожидаемая/наблюдаемая инфляция населения и ценовые ожидания предприятий (инФОМ)."""
    key = meta["key"]
    pat = {"expected": r"ожидаем", "observed": r"наблюда", "business": r"предприят|ценов"}[key]
    page = BASE+"/analytics/dkp/inflationary_expectations/"
    for url, name in _files(page):
        try: sheets = excel_sheets(get(url))
        except Exception: continue
        for df in sheets:
            head = " ".join(str(x).lower() for x in df.head(25).values.ravel())
            if re.search(pat, head):
                d = {k: v for k, v in pairs(df, 0, 40).items() if k >= "2024-01"}
                if len(d) > 6: return d
    return {}


PB = {"export": r"экспорт", "import": r"импорт",
      "trade_balance": r"торгов\w* баланс|сальдо торгового",
      "current_account": r"текущ\w* операц|current account"}


def fetch_pb(meta):
    """Платёжный баланс: экспорт/импорт/сальдо/счёт текущих операций, $ млрд."""
    pat = PB[meta["pb_key"]]
    for url, name in _files(BASE+"/statistics/macro_itm/external_sector/pb/"):
        try: sheets = excel_sheets(get(url))
        except Exception: continue
        for df in sheets:
            for i, row in df.iterrows():
                label = " ".join(str(x).lower() for x in row.values[:3])
                if not re.search(pat, label): continue
                hdr = None
                for j in range(max(0, i-6), i):
                    if sum(1 for c in df.iloc[j].values if to_period(c)) >= 4:
                        hdr = df.iloc[j].values; break
                if hdr is None: continue
                d = {}
                for c, h in enumerate(hdr):
                    p, v = to_period(h), num(row.values[c]) if c < len(row.values) else None
                    if p and v is not None and abs(v) < 200:
                        d.setdefault(p, round(v, 1))
                if len(d) > 6: return d
    return {}
