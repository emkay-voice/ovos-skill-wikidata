"""Answers from a small, fake Wikidata: picking the current value, the right
item, and putting it into words."""
import datetime

import pytest

from ovos_skill_wikidata import load_locale, say_date, say_number, wikidata
from ovos_skill_wikidata.facts import Context, answer
from test_questions import ROOT

REAL_API = wikidata._api


def item(qid):
    return {"datavalue": {"value": {"id": qid}}, "snaktype": "value"}


def claim(snak, rank="normal", ended=False, when=None):
    q = {}
    if ended:
        q["P582"] = [{}]
    if when:
        q["P585"] = [{"datavalue": {"value": {"time": when}}}]
    return {"mainsnak": {**snak, "snaktype": "value"}, "rank": rank, "qualifiers": q}


def time(t, precision=11):
    return {"datavalue": {"value": {"time": t, "precision": precision}}}


def amount(a, unit="1"):
    return {"datavalue": {"value": {"amount": a, "unit": unit}}}


WIKIDATA = {
    "search": {"danmark": ["Q35"], "denmark": ["Q35"], "eiffeltårnet": ["Q243"],
               "frankrig": ["Q142"], "mette frederiksen": ["Q57652"],
               # a ship called Danmark comes first; it has no government
               "skibet": ["Q286428", "Q35"]},
    "claims": {
        "Q35": {
            "P6": [claim(item("Q182397"), ended=True), claim(item("Q5015"), rank="preferred")],
            "P1313": [claim(item("Q795477"))],
            "P36": [claim(item("Q1748"))],
            "P1082": [claim(amount("+5800000"), when="+2019-01-01T00:00:00Z"),
                      claim(amount("+5961249"), when="+2024-01-01T00:00:00Z")],
            "P37": [claim(item("Q9035"))],
            "P31": [claim(item("Q3624078"))],
            "P30": [claim(item("Q46"))],
            "P625": [claim({"datavalue": {"value": {"latitude": 56.0, "longitude": 10.0}}})],
        },
        "Q142": {"P36": [claim(item("Q90"))]},
        "Q243": {
            "P625": [claim({"datavalue": {"value": {"latitude": 48.858, "longitude": 2.294}}})],
            "P17": [claim(item("Q142"))],
            "P2048": [claim(amount("+330", wikidata.METRE))],
            "P571": [claim(time("+1887-01-28T00:00:00Z"))],
            "P18": [claim({"datavalue": {"value": "Tour Eiffel.jpg"}})],
        },
        "Q57652": {"P569": [claim(time("+1977-11-19T00:00:00Z"))]},
        "Q286428": {},
    },
    "labels": {"Q35": "Danmark", "Q5015": "Mette Frederiksen", "Q182397": "Lars Løkke Rasmussen",
               "Q795477": "Danmarks statsminister", "Q1748": "København", "Q9035": "dansk",
               "Q46": "Europa", "Q243": "Eiffeltårnet", "Q142": "Frankrig", "Q90": "Paris",
               "Q57652": "Mette Frederiksen", "Q286428": "Danmark"},
}


@pytest.fixture(autouse=True)
def fake_wikidata(monkeypatch):
    calls = []

    def api(**p):
        calls.append(p)
        if p["action"] == "wbsearchentities":
            return {"search": [{"id": q} for q in WIKIDATA["search"].get(p["search"], [])]}
        if p["action"] == "wbgetclaims":
            c = WIKIDATA["claims"].get(p["entity"], {}).get(p["property"])
            return {"claims": {p["property"]: c} if c else {}}
        if p["action"] == "wbgetentities":
            return {"entities": {q: {"labels": {"da": {"value": WIKIDATA["labels"][q]}}}
                                 for q in p["ids"].split("|") if q in WIKIDATA["labels"]}}
        return {}

    def get(url, params):
        calls.append(params)
        if url == wikidata.NOMINATIM:
            return {"address": {"city": "Paris", "country": "Frankrig"}}
        return None

    for f in (wikidata.search, wikidata._claims, wikidata.labels, wikidata.place):
        f.cache_clear()
    monkeypatch.setattr(wikidata, "_api", api)
    monkeypatch.setattr(wikidata, "_get", get)
    return calls


def ask(kind, text, lang="da-dk"):
    loc = load_locale(ROOT, lang)
    ctx = Context(kind, lang, text, loc.join, lambda n: say_number(n, lang),
                  lambda d, p: say_date(d, p, lang))
    found = answer(kind, text, ctx)
    return found and loc.render(found[0], found[1])


def test_current_prime_minister_and_the_office_by_name():
    assert ask("head_of_government", "danmark") == "Danmarks statsminister er Mette Frederiksen."


def test_an_item_without_the_property_is_skipped():
    assert ask("head_of_government", "skibet") == "Danmarks statsminister er Mette Frederiksen."


def test_capital():
    assert ask("capital", "frankrig") == "Hovedstaden i Frankrig er Paris."


def test_population_is_the_latest_figure_rounded():
    assert ask("population", "danmark") == \
        f"Der bor omkring {say_number(5960000, 'da-dk')} mennesker i Danmark."


def test_where_a_place_is():
    assert ask("location", "eiffeltårnet") == "Eiffeltårnet ligger i Paris, Frankrig."


def test_where_a_country_is():
    assert ask("location", "danmark") == "Danmark er et land i Europa."


def test_height_in_metres():
    assert ask("height", "eiffeltårnet") == f"Eiffeltårnet er {say_number(330, 'da-dk')} meter høj."


def test_age_from_the_birth_date():
    b = datetime.date(1977, 11, 19)
    t = datetime.date.today()
    years = t.year - b.year - ((t.month, t.day) < (b.month, b.day))
    assert ask("age", "mette frederiksen") == f"Mette Frederiksen er {say_number(years, 'da-dk')} år."


def test_dates_are_spoken():
    assert ask("inception", "eiffeltårnet") == \
        f"Eiffeltårnet er fra {say_date(datetime.date(1887, 1, 28), 11, 'da-dk')}."


def test_unknown_things_get_no_answer():
    assert ask("capital", "atlantis") is None
    assert ask("death_date", "mette frederiksen") is None


def test_a_picture_for_the_screen():
    assert wikidata.image("Q243").endswith("Tour_Eiffel.jpg?width=800")


def test_wikidata_requests_may_be_read_by_a_browser(monkeypatch):
    seen = []
    monkeypatch.setattr(wikidata, "_get", lambda url, params: seen.append(params) or {})
    REAL_API(action="wbgetclaims", entity="Q35", property="P6")
    assert seen[0]["origin"] == "*"


def test_wikidata_language_codes():
    assert wikidata.wd_lang("da-DK") == "da"
    assert wikidata.wd_lang("pt-BR") == "pt-br"
    assert wikidata.wd_lang("pt-PT") == "pt"
