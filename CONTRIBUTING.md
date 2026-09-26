# Contributing

Changes are welcome while Staffcode is experimental. A language change should
update `SPEC.md`, the reference interpreter, at least one semantic fixture and
an example when the feature is useful to programmers.

Set up a development environment and run the complete suite with:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e '.[dev]'
pytest
```

Keep score files as UTF-8 with LF line endings. Avoid formatting tools that
normalize spaces or replace Musical Symbols code points.
