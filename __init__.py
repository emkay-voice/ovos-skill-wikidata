"""Wikidata skill: short, current facts for common questions.

"Who is the prime minister of Denmark?", "What is the capital of France?",
"Where is the Eiffel Tower?" - answered from Wikidata's structured data
(and OpenStreetMap for places), as one sentence, through OVOS' common query
pipeline. Made for Emkay (OVOS in a browser): everything it fetches may be
read by a web page, so it needs no keys and no servers of its own.
"""
import os
import random
import re
from functools import lru_cache
from typing import Dict, List, Optional, Tuple

from ovos_utils import classproperty
from ovos_utils.process_utils import RuntimeRequirements
from ovos_workshop.decorators import common_query
from ovos_workshop.skills.ovos import OVOSSkill

from . import wikidata
from .facts import KINDS, Context, answer

#: how sure a matched question with a found fact is. Above Wikipedia's
#: answers on purpose: a question this skill knows how to ask is better
#: answered by the one fact than by an article's first lines
CONFIDENCE = 0.9
#: how long the picture of what an answer is about stays on the screen
PICTURE_SECONDS = 20

_PUNCTUATION = re.compile(r"[?!.,;:¿¡\"“”«»]")


def normalize(text: str) -> str:
    """Lower case, no punctuation, one space between words, and a space
    after an apostrophe, so "d'Italie" and "d' {entity}" line up."""
    text = text.casefold().replace("\u2019", "'")
    text = re.sub(r"'\s*", "' ", text)
    return " ".join(_PUNCTUATION.sub(" ", text).split())


class Locale:
    """One language's templates and answers, read from locale/<lang>/."""

    def __init__(self, folder: str):
        self.folder = folder
        self.templates = self._templates()
        self.articles = self._lines("articles.voc")
        self.and_word = (self._lines("and.dialog") or ["and"])[0]

    def _lines(self, name: str) -> List[str]:
        path = os.path.join(self.folder, name)
        if not os.path.isfile(path):
            return []
        with open(path, encoding="utf-8") as f:
            return [line.strip() for line in f
                    if line.strip() and not line.startswith("#")]

    def _templates(self) -> List[Tuple[re.Pattern, str]]:
        """(regex, kind) for every phrasing, the longest phrasings first, so
        "who is the prime minister of {entity}" wins over "who is {entity}"."""
        from ovos_spec_tools import expand
        out = []
        for kind in KINDS:
            for line in self._lines(f"{kind}.intent"):
                for phrasing in expand(line):
                    phrasing = normalize(phrasing.replace("{entity}", "ENTITY"))
                    if "entity" not in phrasing:
                        continue
                    pattern = re.escape(phrasing).replace("entity", r"(?P<entity>.+?)")
                    out.append((len(phrasing), re.compile(f"^{pattern}$"), kind))
        return [(p, k) for _, p, k in sorted(out, key=lambda t: -t[0])]

    def match(self, utterance: str) -> Optional[Tuple[str, str]]:
        """(kind, entity text) for an utterance this language's templates
        cover, else None."""
        text = normalize(utterance)
        for pattern, kind in self.templates:
            m = pattern.match(text)
            if m:
                return kind, m.group("entity").strip()
        return None

    def without_article(self, text: str) -> Optional[str]:
        words = text.split()
        if len(words) > 1 and words[0] in self.articles:
            return " ".join(words[1:])
        return None

    def render(self, name: str, data: Dict[str, str]) -> Optional[str]:
        lines = self._lines(f"{name}.dialog")
        if not lines:
            return None
        text = random.choice(lines)
        for key, val in data.items():
            text = text.replace("{" + key + "}", str(val))
        return text[0].upper() + text[1:]

    def join(self, names: List[str]) -> str:
        if len(names) == 1:
            return names[0]
        return f"{', '.join(names[:-1])} {self.and_word} {names[-1]}"


@lru_cache(maxsize=16)
def load_locale(root: str, lang: str) -> Optional[Locale]:
    """The locale folder for an OVOS language ("da-DK"): the exact one, else
    one of the same language ("pt-BR" -> pt-br, "de-AT" -> de-de)."""
    lang = lang.lower()
    if not os.path.isdir(root):
        return None
    folders = sorted(os.listdir(root))
    exact = [f for f in folders if f.lower() == lang]
    same = [f for f in folders if f.lower().split("-")[0] == lang.split("-")[0]]
    pick = (exact or same or [None])[0]
    return Locale(os.path.join(root, pick)) if pick else None


def say_number(number, lang: str) -> str:
    try:
        from ovos_number_parser import pronounce_number
        return pronounce_number(number, lang)
    except Exception:  # noqa: BLE001 - a language it has no words for
        return str(number)


def say_date(date, precision: int, lang: str) -> str:
    import datetime
    dt = datetime.datetime(date.year, date.month, date.day)
    try:
        from ovos_date_parser import nice_date, nice_year
        if precision >= 11:
            return nice_date(dt, lang, include_weekday=False)
        return nice_year(dt, lang)
    except Exception:  # noqa: BLE001
        return date.isoformat() if precision >= 11 else str(date.year)


class WikidataSkill(OVOSSkill):

    @classproperty
    def runtime_requirements(self):
        return RuntimeRequirements(internet_before_load=False,
                                   network_before_load=False,
                                   requires_internet=True,
                                   requires_network=True,
                                   no_internet_fallback=True,
                                   no_network_fallback=True)

    def initialize(self):
        #: answer text -> picture of what it is about, for cq_callback
        self._pictures: Dict[str, str] = {}

    def locale(self, lang: str) -> Optional[Locale]:
        return load_locale(os.path.join(self.res_dir, "locale"), lang)

    def ask(self, utterance: str, lang: str) -> Optional[Tuple[str, str]]:
        """(spoken answer, item id) for a question this skill covers."""
        loc = self.locale(lang)
        matched = loc and loc.match(utterance)
        if not matched:
            return None
        kind, text = matched
        ctx = Context(kind, lang, text, loc.join,
                      lambda n: say_number(n, lang),
                      lambda d, p: say_date(d, p, lang))
        found = answer(kind, text, ctx)
        if not found and loc.without_article(text):
            found = answer(kind, loc.without_article(text), ctx)
        if not found:
            return None
        name, data, qid = found
        spoken = loc.render(name, data)
        return (spoken, qid) if spoken else None

    def show_picture(self, utterance: str, spoken: str, lang: str):
        """Our answer was chosen: show a picture of what it is about."""
        picture = self._pictures.pop(spoken, None)
        if picture:
            try:
                # long enough to look at once the answer has been said
                self.gui.show_image(picture, caption=spoken, fill="PreserveAspectFit",
                                    override_idle=PICTURE_SECONDS)
            except Exception as e:  # noqa: BLE001 - no screen is fine
                self.log.debug(f"no picture shown: {e}")

    @common_query(callback=show_picture)
    def match_common_query(self, phrase: str, lang: str):
        found = self.ask(phrase, lang)
        if not found:
            return None
        spoken, qid = found
        self.log.info(f"Wikidata answer ({qid}): {spoken}")
        picture = wikidata.image(qid)
        if picture:
            self._pictures[spoken] = picture
        return spoken, CONFIDENCE
