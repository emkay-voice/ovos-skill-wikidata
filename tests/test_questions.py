"""Which questions each language's templates catch, and what they ask about."""
import os

import pytest

from ovos_skill_wikidata import load_locale, normalize
from ovos_skill_wikidata.facts import KINDS

ROOT = os.path.join(os.path.dirname(os.path.dirname(__file__)), "locale")
LANGS = sorted(os.listdir(ROOT))

CASES = {
    "en-us": [
        ("Who is the prime minister of Denmark?", "head_of_government", "denmark"),
        ("who's denmark's prime minister", "head_of_government", "denmark"),
        ("who is the mayor of copenhagen", "head_of_government", "copenhagen"),
        ("who is the king of sweden", "head_of_state", "sweden"),
        ("what is the capital of france", "capital", "france"),
        ("how many people live in tokyo", "population", "tokyo"),
        ("when was albert einstein born", "birth_date", "albert einstein"),
        ("where was mozart born", "birthplace", "mozart"),
        ("how old is mette frederiksen", "age", "mette frederiksen"),
        ("when did elvis presley die", "death_date", "elvis presley"),
        ("where is the eiffel tower", "location", "the eiffel tower"),
        ("what's the currency of japan", "currency", "japan"),
        ("what language is spoken in brazil", "official_language", "brazil"),
        ("how tall is mount everest", "height", "mount everest"),
        ("when was the eiffel tower built", "inception", "the eiffel tower"),
        ("who wrote the hobbit", "author", "the hobbit"),
    ],
    "da-dk": [
        ("hvem er statsminister i danmark", "head_of_government", "danmark"),
        ("Hvem er Danmarks statsminister?", "head_of_government", "danmark"),
        ("hvem er borgmester i københavn", "head_of_government", "københavn"),
        ("hvem er kongen af sverige", "head_of_state", "sverige"),
        ("hvad er hovedstaden i frankrig", "capital", "frankrig"),
        ("hvor mange mennesker bor der i tokyo", "population", "tokyo"),
        ("hvornår blev h c andersen født", "birth_date", "h c andersen"),
        ("hvor blev mozart født", "birthplace", "mozart"),
        ("hvor gammel er mette frederiksen", "age", "mette frederiksen"),
        ("hvornår døde elvis presley", "death_date", "elvis presley"),
        ("hvor er eiffeltårnet", "location", "eiffeltårnet"),
        ("hvor ligger eiffeltårnet", "location", "eiffeltårnet"),
        ("hvilken valuta bruger de i japan", "currency", "japan"),
        ("hvilket sprog taler de i brasilien", "official_language", "brasilien"),
        ("hvor høj er rundetårn", "height", "rundetårn"),
        ("hvornår blev rundetårn bygget", "inception", "rundetårn"),
        ("hvem skrev hobbitten", "author", "hobbitten"),
    ],
    "de-de": [
        ("wer ist der bundeskanzler von deutschland", "head_of_government", "deutschland"),
        ("was ist die hauptstadt von frankreich", "capital", "frankreich"),
        ("wo liegt der eiffelturm", "location", "der eiffelturm"),
        ("wie alt ist angela merkel", "age", "angela merkel"),
    ],
    "fr-fr": [
        ("qui est le premier ministre du danemark", "head_of_government", "danemark"),
        ("Quelle est la capitale de l'Italie ?", "capital", "l' italie"),
        ("où est la tour eiffel", "location", "la tour eiffel"),
        ("qui a écrit les misérables", "author", "les misérables"),
    ],
    "es-es": [
        ("¿quién es el presidente de francia?", "head_of_state", "francia"),
        ("cuál es la capital de dinamarca", "capital", "dinamarca"),
        ("dónde está la torre eiffel", "location", "la torre eiffel"),
    ],
    "it-it": [("qual è la capitale della francia", "capital", "francia"),
              ("dov'è la torre eiffel", "location", "la torre eiffel")],
    "nl-nl": [("wie is de premier van nederland", "head_of_government", "nederland"),
              ("waar ligt de eiffeltoren", "location", "de eiffeltoren")],
    "pt-pt": [("qual é a capital da dinamarca", "capital", "dinamarca"),
              ("onde fica a torre eiffel", "location", "a torre eiffel")],
    "pt-br": [("quem é o presidente do brasil", "head_of_state", "brasil")],
    "ca-es": [("quina és la capital de frança", "capital", "frança")],
    "gl-es": [("cal é a capital de francia", "capital", "francia")],
    "eu-es": [("non dago bilbo", "location", "bilbo")],
}


@pytest.mark.parametrize("lang,utterance,kind,entity",
                         [(lang, u, k, e) for lang, cases in CASES.items() for u, k, e in cases])
def test_question_is_understood(lang, utterance, kind, entity):
    assert load_locale(ROOT, lang).match(utterance) == (kind, entity)


@pytest.mark.parametrize("lang", LANGS)
def test_every_kind_has_templates_and_an_answer(lang):
    loc = load_locale(ROOT, lang)
    covered = {k for _, k in loc.templates}
    assert covered == set(KINDS), f"{lang} misses {set(KINDS) - covered}"
    for name in list(KINDS) + ["office_holder", "location_country", "location_continent"]:
        assert loc.render(name, {"entity": "X", "value": "Y", "office": "Z"}), f"{lang}: {name}.dialog"


@pytest.mark.parametrize("lang", LANGS)
def test_cases_cover_every_language(lang):
    assert lang in CASES


@pytest.mark.parametrize("utterance", [
    "what time is it", "tell me a joke", "who are you", "play some music",
    "hvad er klokken", "fortæl en vittighed",
])
def test_other_questions_are_left_alone(utterance):
    assert load_locale(ROOT, "en-us").match(utterance) is None
    assert load_locale(ROOT, "da-dk").match(utterance) is None


def test_language_falls_back_to_the_same_language():
    assert load_locale(ROOT, "de-AT").folder.endswith("de-de")
    assert load_locale(ROOT, "pt-BR").folder.endswith("pt-br")
    assert load_locale(ROOT, "sv-SE") is None


def test_lists_are_joined_in_the_language():
    assert load_locale(ROOT, "da-dk").join(["dansk", "tysk", "færøsk"]) == "dansk, tysk og færøsk"
    assert load_locale(ROOT, "en-us").join(["English"]) == "English"


def test_normalize():
    assert normalize("  Hvem er Danmarks  statsminister? ") == "hvem er danmarks statsminister"
    assert normalize("d’Italie") == "d' italie"
