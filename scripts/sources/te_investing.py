"""TradingEconomics + Investing.com: ВВП, промпроизводство, безработица, з/п, розница."""
from bs4 import BeautifulSoup
from common import get, num, to_period, HEADERS


def _te(slug):
    soup = BeautifulSoup(get(f"https://ru.tradingeconomics.com/{slug}").decode("utf-8","ignore"), "lxml")
    out = {}
    for tr in soup.select("table tr"):
        tds = [td.get_text(" ", strip=True) for td in tr.find_all(["td","th"])]
        if len(tds) < 2: continue
        p, v = to_period(tds[0]), num(tds[1])
        if p and v is not None: out.setdefault(p, v)
    return out


def _investing(event_id):
    import requests
    try:
        r = requests.post("https://ru.investing.com/economic-calendar/more-history",
                          data={"eventID": event_id, "last_time_scope": 0, "limit_from": 0},
                          headers={**HEADERS, "X-Requested-With": "XMLHttpRequest",
                                   "Referer": "https://ru.investing.com/economic-calendar/"},
                          timeout=60)
        r.raise_for_status()
        body = r.json().get("historyRows", "")
    except Exception:
        return {}
    out = {}
    for tr in BeautifulSoup(body, "lxml").select("tr"):
        tds = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
        if len(tds) < 3: continue
        p, v = to_period(" ".join(tds[:2])), num(tds[2])
        if p and v is not None: out.setdefault(p, v)
    return out


def fetch(meta):
    out = {}
    if meta.get("te_slug"):
        try: out.update(_te(meta["te_slug"]))
        except Exception: pass
    if meta.get("investing_id"):
        for k, v in _investing(meta["investing_id"]).items(): out.setdefault(k, v)
    return out
