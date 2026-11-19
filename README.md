# <img src='icon.png' card_color='#2A6EBB' width='50' height='50' style='vertical-align:bottom'/> Wikidata

Short, current facts from [Wikidata](https://www.wikidata.org): who leads a
country, capitals, population, birthdays and ages, where places are. One
sentence per answer, through OpenVoiceOS' common query pipeline, next to
Wikipedia and the other knowledge skills.

```
"who is the prime minister of denmark"  -> "The Prime Minister of Denmark is …" (whoever it is today)
"where is the eiffel tower"             -> "Eiffel Tower is in Paris, France."
"hvad er hovedstaden i frankrig"        -> "Hovedstaden i Frankrig er Paris."
```

I made it for [Emkay](https://github.com/emkay-voice/emkay), OpenVoiceOS in the
browser, where DuckDuckGo and Wolfram Alpha can't be used (their servers don't
let a web page read the answers). It works on any
[OpenVoiceOS](https://openvoiceos.org), and the plan is to offer it to
OpenVoiceOS once it has proven itself.

[![Build](https://github.com/emkay-voice/ovos-skill-wikidata/actions/workflows/publish.yml/badge.svg)](https://github.com/emkay-voice/ovos-skill-wikidata/actions/workflows/publish.yml)
[![PyPI version](https://img.shields.io/pypi/v/ovos-skill-wikidata.svg)](https://pypi.org/project/ovos-skill-wikidata/)

## Why Wikidata

Wikipedia is good for "tell me about …", but a question like "who is the
prime minister of Denmark" lands on an article about the office, not the
person holding it now. Wikidata stores the fact itself, marks which value is
current, and has labels in nearly every language, so the answer is short,
up to date and in the language you asked in.

## What it answers

| Question | From |
|---|---|
| who is the prime minister / mayor / chancellor of … | head of government (P6), named by its office (P1313) |
| who is the president / king / queen of … | head of state (P35), named by its office (P1906) |
| what is the capital of … | P36 |
| how many people live in … | the latest population figure (P1082), rounded |
| when was … born · how old is … · when did … die | P569, P570 |
| where was … born | P19 |
| where is … | the town and country around its coordinates (P625), from OpenStreetMap; a country's continent |
| what is the currency of … · what language is spoken in … | P38, P37 |
| how tall / high is … | height (P2048) or elevation (P2044), in metres |
| when was … founded / built | P571 |
| who wrote … | P50 |

If several things share a name, it takes the first one Wikidata finds that
actually has the fact asked for (the country Denmark, not a ship called
Danmark). When an answer is picked, a picture of what it is about (P18) is
shown on the screen.

Questions it doesn't recognise are left to the other skills.

## Languages

English, Danish, German, French, Spanish, Italian, Dutch, Portuguese
(Portugal and Brazil), Catalan, Galician and Basque, the languages Emkay
supports. Each language has a template per kind of question
(`locale/<lang>/<kind>.intent`, `{entity}` is what's asked about) and an
answer (`<kind>.dialog`). English and Danish are the tested ones; the others
would benefit from a native speaker's eye, especially Basque.

## Privacy and network

It asks only two places, both without keys or accounts:

- `www.wikidata.org` (MediaWiki's API, with `origin=*` so a browser may read it)
- `nominatim.openstreetmap.org`, for "where is …" (one lookup per question,
  well within its [usage policy](https://operations.osmfoundation.org/policies/nominatim/))

Pictures come from `commons.wikimedia.org`.

## Install
```bash
pip install ovos-skill-wikidata
```

## Development

See [DEVELOPMENT.md](DEVELOPMENT.md).

## Category
**Information**

## Tags
#wikidata #knowledge #facts #common-query #openstreetmap
