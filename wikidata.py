"""Short facts from Wikidata (and places from OpenStreetMap's Nominatim).

Everything here goes through MediaWiki's action API and Nominatim, both of
which a web page may read (anonymous CORS, `origin=*`), so it works the same
on a device and in a browser. No keys, no servers of our own.

Only `requests` is used, so this module can be tested and reused without
OVOS.
"""
import datetime
from functools import lru_cache
from typing import Dict, List, Optional, Tuple

import requests

API = "https://www.wikidata.org/w/api.php"
NOMINATIM = "https://nominatim.openstreetmap.org/reverse"
COMMONS_FILE = "https://commons.wikimedia.org/wiki/Special:FilePath/{name}?width=800"
USER_AGENT = "ovos-skill-wikidata (https://github.com/emkay-voice/ovos-skill-wikidata)"
TIMEOUT = 5

METRE = "http://www.wikidata.org/entity/Q11573"
COUNTRY = "Q6256"
SOVEREIGN_STATE = "Q3624078"


def wd_lang(lang: str) -> str:
    """Wikidata's language code for an OVOS one: "da-DK" -> "da", but
    "pt-BR" -> "pt-br" (Wikidata keeps Brazilian labels apart)."""
    lang = (lang or "en").lower()
    return lang if lang == "pt-br" else lang.split("-")[0]


def _get(url: str, params: dict) -> Optional[dict]:
    try:
        r = requests.get(url, params=params, timeout=TIMEOUT,
                         headers={"User-Agent": USER_AGENT})
        return r.json()
    except Exception:  # noqa: BLE001 - no answer is an answer here
        return None


def _api(**params) -> dict:
    # origin=*: anonymous CORS, so a browser may read the reply too
    return _get(API, {"format": "json", "origin": "*", **params}) or {}


@lru_cache(maxsize=256)
def search(text: str, lang: str, limit: int = 3) -> Tuple[str, ...]:
    """Item ids whose label or alias matches `text`, best first."""
    code = wd_lang(lang)
    data = _api(action="wbsearchentities", search=text, language=code.split("-")[0],
                uselang=code, type="item", limit=limit)
    return tuple(hit["id"] for hit in data.get("search", []))


@lru_cache(maxsize=512)
def _claims(qid: str, prop: str) -> Tuple[dict, ...]:
    data = _api(action="wbgetclaims", entity=qid, property=prop)
    return tuple(data.get("claims", {}).get(prop, []))


def current(qid: str, prop: str) -> List[dict]:
    """The statements of `prop` that hold now: the preferred ones if any are
    marked so, else the normal ones without an end time. Deprecated ones
    never count."""
    claims = [c for c in _claims(qid, prop) if c.get("rank") != "deprecated"
              and c.get("mainsnak", {}).get("snaktype") == "value"]
    preferred = [c for c in claims if c.get("rank") == "preferred"]
    if preferred:
        return preferred
    return [c for c in claims if "P582" not in c.get("qualifiers", {})]


def latest(qid: str, prop: str) -> Optional[dict]:
    """One statement for a measured value (population): the preferred one,
    else the one with the latest point in time (P585)."""
    claims = current(qid, prop)
    if not claims:
        return None

    def when(c):
        q = c.get("qualifiers", {}).get("P585") or [{}]
        return q[0].get("datavalue", {}).get("value", {}).get("time", "")
    return max(claims, key=when)


def value(claim: dict):
    return claim["mainsnak"]["datavalue"]["value"]


@lru_cache(maxsize=512)
def labels(qids: Tuple[str, ...], lang: str) -> Dict[str, str]:
    """Labels in `lang`, falling back the way Wikidata does (e.g. to English)."""
    if not qids:
        return {}
    code = wd_lang(lang)
    data = _api(action="wbgetentities", ids="|".join(qids), props="labels",
                languages=code, languagefallback=1)
    out = {}
    for qid, ent in data.get("entities", {}).items():
        lab = ent.get("labels", {})
        if lab:
            out[qid] = next(iter(lab.values()))["value"]
    return out


def label(qid: str, lang: str) -> Optional[str]:
    return labels((qid,), lang).get(qid)


def item_values(qid: str, prop: str, lang: str) -> List[str]:
    """Labels of the items `prop` points to now, in `lang`."""
    ids = tuple(value(c)["id"] for c in current(qid, prop))
    names = labels(ids, lang)
    return [names[i] for i in ids if i in names]


def time_value(qid: str, prop: str) -> Optional[Tuple[datetime.date, int]]:
    """(date, precision) of a time statement; precision 11 = day,
    10 = month, 9 = year. None for dates before year 1."""
    claims = current(qid, prop)
    if not claims:
        return None
    v = value(claims[0])
    t = v["time"]
    if t.startswith("-"):
        return None
    year, month, day = t[1:11].split("-")
    precision = v.get("precision", 11)
    date = datetime.date(int(year), max(int(month), 1), max(int(day), 1))
    return date, precision


def quantity(qid: str, prop: str, unit: Optional[str] = None) -> Optional[float]:
    claim = latest(qid, prop)
    if not claim:
        return None
    v = value(claim)
    if unit and v.get("unit") != unit:
        return None
    amount = float(v["amount"])
    return int(amount) if amount.is_integer() else amount


def image(qid: str) -> Optional[str]:
    """A picture of the item (P18), as a Wikimedia Commons URL."""
    claims = current(qid, "P18")
    if not claims:
        return None
    from urllib.parse import quote
    return COMMONS_FILE.format(name=quote(value(claims[0]).replace(" ", "_")))


def is_country(qid: str) -> bool:
    kinds = {value(c)["id"] for c in current(qid, "P31")}
    return bool(kinds & {COUNTRY, SOVEREIGN_STATE})


def coordinates(qid: str) -> Optional[Tuple[float, float]]:
    claims = current(qid, "P625")
    if not claims:
        return None
    v = value(claims[0])
    return v["latitude"], v["longitude"]


@lru_cache(maxsize=128)
def place(lat: float, lon: float, lang: str) -> Dict[str, str]:
    """What OpenStreetMap calls the place at (lat, lon), at town level:
    {"city": ..., "country": ...} in `lang` where OSM has the names."""
    data = _get(NOMINATIM, {"lat": lat, "lon": lon, "zoom": 10, "format": "jsonv2",
                            "addressdetails": 1, "accept-language": wd_lang(lang)}) or {}
    addr = data.get("address", {})
    city = (addr.get("city") or addr.get("town") or addr.get("village")
            or addr.get("municipality") or addr.get("county"))
    out = {}
    if city:
        out["city"] = city
    if addr.get("country"):
        out["country"] = addr["country"]
    return out
