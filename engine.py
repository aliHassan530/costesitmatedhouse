"""engine.py - real-data cost engine: rates, trend forecast, item catalog, estimate."""
import csv, io, math
from pathlib import Path
from functools import lru_cache

import numpy as np

from market_data import *

OVERRIDE = {}   # (city, item, year) -> (low, high) from data/city_rates.csv
CSV_PATH = Path(__file__).parent / "data" / "city_rates.csv"


def load_csv(text):
    """CSV columns: city,item,year,low,high  (item = market_data ka key, e.g. cement, steel)."""
    OVERRIDE.clear()
    rows = [l for l in text.splitlines() if l.strip() and not l.lstrip().startswith("#")]
    for r in csv.DictReader(rows):
        try:
            c, i, y = r["city"].strip(), r["item"].strip(), int(r["year"])
            if c in CITY and (i in DATA or i in ASSUMED):
                OVERRIDE[(c, i, y)] = (float(r["low"]), float(r["high"]))
        except (KeyError, ValueError, TypeError):
            continue
    return len(OVERRIDE)


LEVELS = {"economy": 0.2, "market": 0.5, "premium": 0.8}   # range ke andar position
STAGES = ["grey", "semi", "finished"]


def mid(lo, hi, p=0.5):
    return lo + (hi - lo) * p


@lru_cache(None)
def growth(name):
    """Recent saalon ko zyada wazan de kar log-linear trend (annual growth)."""
    s = DATA[name]
    y = np.arange(len(s))
    m = np.log([mid(*x) for x in s])
    w = 0.5 ** ((len(s) - 1 - y) / 1.5)
    return float(min(max(np.polyfit(y, m, 1, w=w)[0], 0), MAX_G))


def rate(name, year):
    if name in DATA:
        s = DATA[name]
        if year <= LAST:
            return s[year - FIRST]
        n = year - LAST
        f, w = math.exp(growth(name) * n), WIDEN * n
        return s[-1][0] * f * (1 - w), s[-1][1] * f * (1 + w)
    lo, hi, idx = ASSUMED[name]
    k = index(idx, year)
    return lo * k, hi * k


def index(idx, year):
    names = ("cement", "bricks", "steel") if idx == "mat" else (idx,)
    return sum(mid(*rate(n, year)) / mid(*rate(n, LAST)) for n in names) / len(names)


def M(id, g, en, ur, q, unit, rates, kind="mat", req=False, st=(1, 1, 1), semi=1, div=1, plus=None):
    return dict(id=id, g=g, en=en, ur=ur, q=q, unit=unit, rates=rates, kind=kind,
                req=req, st=st, semi=semi, div=div, plus=plus)


V3 = {"std": ("Standard MDF", "cab_std"), "pre": ("Premium UV/Acrylic", "cab_pre"), "lux": ("Luxury Wood/Veneer", "cab_lux")}
ITEMS = [
 M("foundation", "grey", "Foundation", "بنیاد", lambda c: c["marla"] * (1 + .3 * (c["floors"] - 1)), "marla", {"-": ("", "foundation")}, req=True),
 M("bricks", "grey", "Bricks (Eent)", "اینٹیں", lambda c: 8500 * c["marla"] * c["fu"], "bricks", {"-": ("", "bricks")}, req=True, div=1000),
 M("cement", "grey", "Cement", "سیمنٹ", lambda c: 100 * c["marla"] * c["fu"], "bags", {"-": ("", "cement")}, req=True),
 M("sand", "grey", "Sand (Reta)", "ریت", lambda c: 120 * c["marla"] * c["fu"], "cft", {"-": ("", "sand")}, req=True),
 M("crush", "grey", "Crush (Bajri)", "بجری", lambda c: 90 * c["marla"] * c["fu"], "cft",
   {"s": ("Sargodha", "crush_s"), "m": ("Margalla", "crush_m")}, req=True),
 M("steel", "grey", "Steel (Sariya)", "سریا", lambda c: 800 * c["marla"] * c["fu"], "kg", {"-": ("", "steel")}, req=True),
 M("labour", "grey", "Grey Labour", "مزدوری", lambda c: c["area"] * c["fu"] * max(.9, 1 - .004 * (c["marla"] - 1)), "sqft", {"-": ("", "labour")}, kind="lab", req=True),
 M("wall", "outer", "Boundary Wall", "چار دیواری", lambda c: 6 * math.sqrt(c["area"] / 2), "rft", {"-": ("", "wall")}, st=(1, 1, 1)),
 M("gate", "outer", "Main Gate", "مین گیٹ", lambda c: 1, "gate", {"-": ("", "gate")}, st=(0, 1, 1)),
 M("plaster", "finish", "Plaster", "پلستر", lambda c: c["cov"], "sqft", {"-": ("", "plaster")}, st=(0, 1, 1)),
 M("windows", "finish", "Windows", "کھڑکیاں", lambda c: c["cov"] * .11, "sqft",
   {"alu": ("Aluminium", "alu"), "upvc": ("uPVC", "upvc")}, st=(0, 1, 1)),
 M("doors", "finish", "Wood Doors", "لکڑی کے دروازے", lambda c: c["beds"] + c["kitchens"] + c["floors"] + .4 * c["baths"] + 2.2,
   "door-units", {"-": ("", "door")}, st=(0, 1, 1), semi=.35),
 M("electrical", "finish", "Electrical", "بجلی کا کام", lambda c: c["cov"] / REF_AREA, "x ref house", {"-": ("", "elec")}, st=(0, 1, 1), semi=.5),
 M("plumbing", "finish", "Plumbing", "پلمبنگ", lambda c: .5 * c["cov"] / REF_AREA + .5 * c["baths"] / REF_BATHS, "x ref house", {"-": ("", "plumb")}, st=(0, 1, 1), semi=.6),
 M("tiles", "finish", "Tiles + Fixing", "ٹائلز", lambda c: c["cov"] * 1.15, "sqft",
   {"cer": ("Ceramic", "ceramic"), "por": ("Porcelain", "porcelain")}, st=(0, 0, 1), plus="tile_fix"),
 M("paint", "finish", "Paint", "رنگ", lambda c: c["cov"], "sqft", {"-": ("", "paint")}, st=(0, 0, 1)),
 M("kitchen", "finish", "Kitchen Cabinets", "کچن کیبنٹ", lambda c: 45 * c["kitchens"], "sqft", V3, st=(0, 0, 1)),
 M("wardrobes", "finish", "Wardrobes", "الماریاں", lambda c: 40 * c["beds"], "sqft", V3, st=(0, 0, 1)),
]


def catalog():
    return {
        "cities": list(CITY), "years": {"min": FIRST, "last_actual": LAST, "max": MAX_YEAR},
        "stages": STAGES, "levels": list(LEVELS), "notes": NOTES,
        "items": [dict(id=i["id"], group=i["g"], en=i["en"], ur=i["ur"], required=i["req"],
                       stage=dict(zip(STAGES, map(bool, i["st"]))), semi=i["semi"],
                       variants=[{"key": k, "label": v[0]} for k, v in i["rates"].items()] if len(i["rates"]) > 1 else [],
                       assumed=list(i["rates"].values())[0][1] in ASSUMED) for i in ITEMS],
    }


def _unit(it, var, year, city):
    name = it["rates"][var][1]
    f = CITY[city][0 if it["kind"] == "mat" else 1]
    base = OVERRIDE.get((city, name, LAST))
    if (city, name, year) in OVERRIDE:                      # is city+saal ka real rate
        lo, hi = OVERRIDE[(city, name, year)]; f = 1
    elif base and year > LAST:                               # city ka last rate + national trend
        a, b, c0, d0 = *rate(name, year), *rate(name, LAST)
        lo, hi = base[0] * a / c0, base[1] * b / d0; f = 1
    else:
        lo, hi = rate(name, year)
    lo, hi = lo * f / it["div"], hi * f / it["div"]
    if it["plus"]:
        a, b = rate(it["plus"], year)
        lo, hi = lo + a * CITY[city][1], hi + b * CITY[city][1]
    return lo, hi


def compute(r, year):
    area = r["marla"] * 225
    c = dict(marla=r["marla"], floors=r["floors"], area=area, fu=1 + .95 * (r["floors"] - 1),
             cov=area * r["floors"], beds=r["beds"], baths=r["baths"], kitchens=r["kitchens"])
    p = LEVELS[r["level"]]
    plo, phi = max(p - .25, 0), min(p + .25, 1)
    lines, tot = [], [0, 0, 0]
    for it in ITEMS:
        sel = r["items"].get(it["id"], {})
        if not (it["req"] or sel.get("enabled")):
            continue
        var = sel.get("variant") if sel.get("variant") in it["rates"] else next(iter(it["rates"]))
        lo, hi = _unit(it, var, year, r["city"])
        sf = it["semi"] if r["stage"] == "semi" else 1
        q = it["q"](c)
        cost = [q * mid(lo, hi, x) * sf for x in (p, plo, phi)]
        tot = [a + b for a, b in zip(tot, cost)]
        lines.append(dict(id=it["id"], group=it["g"], en=it["en"], ur=it["ur"], variant=it["rates"][var][0],
                          qty=round(q, 2), unit=it["unit"], unit_rate=round(mid(lo, hi, p), 1), scope=sf,
                          cost=round(cost[0]), assumed=it["rates"][var][1] in ASSUMED or bool(it["plus"] and it["plus"] in ASSUMED)))
    return lines, tot, c


def estimate(r):
    lines, tot, c = compute(r, r["year"])
    for l in lines:
        l["share"] = round(l["cost"] / tot[0] * 100, 1)
    timeline = [dict(year=y, total=round(compute(r, y)[1][0]), forecast=y > LAST) for y in range(FIRST, MAX_YEAR + 1)]
    groups = {}
    for l in lines:
        groups[l["group"]] = groups.get(l["group"], 0) + l["cost"]
    return dict(total=round(tot[0]), low=round(tot[1]), high=round(tot[2]), per_sqft=round(tot[0] / c["cov"]),
                covered_sqft=c["cov"], is_forecast=r["year"] > LAST, lines=lines, groups=groups, timeline=timeline)


if CSV_PATH.exists():
    load_csv(CSV_PATH.read_text(encoding="utf-8-sig"))
