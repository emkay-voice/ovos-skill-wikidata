# Development

## Setup
```bash
git clone https://github.com/emkay-voice/ovos-skill-wikidata.git
cd ovos-skill-wikidata
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[test]"
```

## Running tests
```bash
pytest tests/ -v
```
The tests need no network: `test_facts.py` answers from a small fake
Wikidata (current vs. ended statements, the latest population figure, an item
without the property being skipped), and `test_questions.py` checks every
language's templates against example questions.

## How it fits together

- `wikidata.py` – the lookups (Wikidata's action API and Nominatim), plain
  `requests`, no OVOS. Every Wikidata request carries `origin=*`, so a web page
  may read the answer.
- `facts.py` – the kinds of question: which property answers each, and how the
  value becomes words.
- `__init__.py` – the skill: matches the question against the language's
  templates, looks it up and renders the answer for common query.

## Adding a kind of question

1. Add it to `KINDS` in `facts.py`: a lookup and the property an item must
   have to be the one meant.
2. Add `locale/<lang>/<kind>.intent` and `<kind>.dialog` for every language.
3. Add example questions to `CASES` in `tests/test_questions.py` and a lookup
   test in `tests/test_facts.py`.

## Adding a language

Copy `locale/en-us/` to `locale/<lang>/` and translate the templates and
answers (`{entity}` and `{value}` stay as they are; `articles.voc` lists the
articles that may come before a name, `and.dialog` the word for "and").
Add a few example questions for it to `CASES`.

## Versioning

The version is `version` in `pyproject.toml`: `X.Y.Z`, or `X.Y.ZaN` for an
alpha (Emkay follows OpenVoiceOS' alpha channel).

## Releasing

Releases are tag-triggered (`v*`), the same way as in the other Emkay repos:
```bash
# bump version in pyproject.toml
git commit -am "vX.Y.ZaN"
git tag vX.Y.ZaN
git push && git push --tags
```
`.github/workflows/publish.yml` runs the tests and builds the wheel on every
push; on a tag it publishes to PyPI (trusted publishing, environment `pypi`)
and makes a GitHub release with the commits since the previous tag as notes.
Alpha tags become pre-releases.

## Style / conventions

- License: Apache-2.0.
- `locale/<lang-code>/` layout, `skill.json` inside each locale folder.
