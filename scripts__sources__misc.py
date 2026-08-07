"""hh.ru и Автостат."""
import re
from bs4 import BeautifulSoup
from common import get, num, to_period, period


def fetch_hh(meta=None):
    html = get("https://stats.hh.ru/").decode("utf-8", "ignore")
    out = {}
    for m in re.finditer(r'"(20\d{2})-(\d{2})[^"]*"\s*[,:]\s*([\d.,]+)', html):
        v = num(m.group(3))
        if v and 0.5 < v < 30:
            out.setdefault(period(m.group(1), m.group(2)), round(v, 1))
    if out: return out
    for tr in BeautifulSoup(html, "lxml").select("table tr"):
        tds = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
        if len(tds) >= 2:
            p, v = to_period(tds[0]), num(tds[1])
            if p and v: out.setdefault(p, round(v, 1))
    return out


def fetch_cars(meta=None):
    soup = BeautifulSoup(get("https://www.autostat.ru/press-releases/").decode("utf-8","ignore"), "lxml")
    out = {}
    for a in soup.select("a[href]"):
        t = a.get_text(" ", strip=True)
        if "Продажи новых легковых автомобилей в России" not in t: continue
        p = to_period(t)
        if not p: continue
        url = a["href"] if a["href"].startswith("http") else "https://www.autostat.ru"+a["href"]
        try:
            body = BeautifulSoup(get(url), "lxml").get_text(" ", strip=True)
        except Exception:
            continue
        m = re.search(r"(меньше|больше|снизил\w*|упал\w*|вырос\w*|сократил\w*|увеличил\w*)[^.%]{0,80}?(\d+[,.]?\d*)\s*%", body)
        if m:
            v = num(m.group(2))
            if re.match(r"меньше|снизил|упал|сократил", m.group(1)): v = -v
            out.setdefault(p, round(v, 1))
    return out
