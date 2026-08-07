"""PMI обрабатывающих отраслей (cbonds.ru/indexes/51339), резерв — TradingEconomics."""
from bs4 import BeautifulSoup
from common import get, num, to_period


def fetch(meta):
    out = {}
    try:
        soup = BeautifulSoup(get(f"https://cbonds.ru/indexes/{meta['cbonds_id']}/").decode("utf-8","ignore"), "lxml")
        for tr in soup.select("table tr"):
            tds = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
            if len(tds) < 2: continue
            p, v = to_period(tds[0]), num(tds[1])
            if p and v is not None and 20 < v < 80: out.setdefault(p, v)
    except Exception:
        pass
    if not out and meta.get("te_slug"):
        from sources.te_investing import _te
        out = {k: v for k, v in _te(meta["te_slug"]).items() if 20 < v < 80}
    return out
