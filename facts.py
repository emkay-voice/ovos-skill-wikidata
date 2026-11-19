"""The questions this skill answers, and how each is looked up.

Each kind of question has a template file per language,
`locale/<lang>/<kind>.intent` ("who is the prime minister of {entity}"),
and an answer, `locale/<lang>/<kind>.dialog`. Here each kind says which
Wikidata property answers it and how the value is put into words.
"""
import datetime
from typing import Callable, Dict, Optional, Tuple

from . import wikidata as wd

#: A finished answer: (dialog name, data for the dialog, item it is about).
Answer = Tuple[str, Dict[str, str], str]


def _names(lang_and: Callable[[list], str], names: list) -> Optional[str]:
    return lang_and(names) if names else None


def head_of(prop: str, office_prop: str):
    """Who holds an office now (P6 head of government, P35 head of state).
    Names the office when Wikidata knows it ("Danmarks statsminister")."""
    def look(qid, ctx):
        who = _names(ctx.join, wd.item_values(qid, prop, ctx.lang))
        if not who:
            return None
        office = wd.item_values(qid, office_prop, ctx.lang)
        if office:
            return "office_holder", {"office": office[0], "value": who}
        return ctx.kind, {"value": who}
    return look


def items(prop: str):
    def look(qid, ctx):
        names = _names(ctx.join, wd.item_values(qid, prop, ctx.lang))
        return names and (ctx.kind, {"value": names})
    return look


def date(prop: str):
    def look(qid, ctx):
        when = wd.time_value(qid, prop)
        if not when:
            return None
        return ctx.kind, {"value": ctx.say_date(*when)}
    return look


def age(qid, ctx):
    born = wd.time_value(qid, "P569")
    if not born or born[1] < 11 or wd.current(qid, "P570"):
        return None   # no exact birth date, or no longer alive
    b, today = born[0], datetime.date.today()
    years = today.year - b.year - ((today.month, today.day) < (b.month, b.day))
    return ctx.kind, {"value": ctx.say_number(years)}


def population(qid, ctx):
    n = wd.quantity(qid, "P1082")
    if not n:
        return None
    # a census figure is never exact to the person; three digits are plenty
    rounded = int(float(f"{n:.3g}")) if n >= 1000 else n
    return ctx.kind, {"value": ctx.say_number(rounded)}


def height(qid, ctx):
    # buildings and people have a height (P2048), mountains an elevation (P2044)
    for prop in ("P2048", "P2044"):
        m = wd.quantity(qid, prop, unit=wd.METRE)
        if m:
            return ctx.kind, {"value": ctx.say_number(round(m, 2))}
    return None


def location(qid, ctx):
    """Where something is: the town and country around its coordinates
    (OpenStreetMap), or for a country, its continent."""
    if wd.is_country(qid):
        continent = wd.item_values(qid, "P30", ctx.lang)
        return continent and ("location_continent", {"value": ctx.join(continent)})
    where = wd.coordinates(qid)
    found = wd.place(*where, ctx.lang) if where else {}
    city, country = found.get("city"), found.get("country")
    if not country:
        country = (wd.item_values(qid, "P17", ctx.lang) or [None])[0]
    if city and city.casefold() != (ctx.entity or "").casefold():
        return ctx.kind, {"value": f"{city}, {country}" if country else city}
    return country and ("location_country", {"value": country})


#: kind of question -> how to answer it, and the property an item needs to
#: be the one meant (to pick between items with the same name)
KINDS: Dict[str, Tuple[Callable, str]] = {
    "head_of_government": (head_of("P6", "P1313"), "P6"),
    "head_of_state": (head_of("P35", "P1906"), "P35"),
    "capital": (items("P36"), "P36"),
    "population": (population, "P1082"),
    "birth_date": (date("P569"), "P569"),
    "birthplace": (items("P19"), "P19"),
    "age": (age, "P569"),
    "death_date": (date("P570"), "P570"),
    "location": (location, "P625"),
    "currency": (items("P38"), "P38"),
    "official_language": (items("P37"), "P37"),
    "height": (height, ""),
    "inception": (date("P571"), "P571"),
    "author": (items("P50"), "P50"),
}


class Context:
    """What a lookup needs from the skill: the language and how to say
    numbers, dates and lists in it."""
    def __init__(self, kind: str, lang: str, entity: str, join, say_number, say_date):
        self.kind, self.lang, self.entity = kind, lang, entity
        self.join, self.say_number, self.say_date = join, say_number, say_date


def answer(kind: str, text: str, ctx: Context) -> Optional[Answer]:
    """Look `text` ("danmark") up as the item a `kind` question is about,
    and answer it. Tries the first few items of that name, preferring one
    that has the property the question asks about."""
    look, needs = KINDS[kind]
    for qid in wd.search(text, ctx.lang):
        if needs and not wd.current(qid, needs):
            continue
        ctx.entity = wd.label(qid, ctx.lang) or text
        found = look(qid, ctx)
        if found:
            name, data = found
            return name, {"entity": ctx.entity, **data}, qid
    return None
