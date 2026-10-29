# Contributing

The original source license decision is deferred. Public availability does not
grant a general software license. Discuss proposed contributions and licensing
with the maintainer before submitting code; do not assume an inbound MIT grant.

Use Python 3.12 x64 on Windows and the README's virtual-environment commands.
Create a focused branch, preserve filesystem safety and avoid unrelated UI
redesign. Run `python -m pytest -q --tb=short` from the activated environment.
Use isolated temporary folders for every moving/monitoring test; never real
Downloads/Documents. Keep dependencies small and pinned. Add tests for meaningful
behavior changes. Explain the problem, solution, validation and limits in a PR.

Report reproducible bugs with Windows/Python versions and synthetic examples.
Do not attach settings, History, private paths or credentials. Propose larger
features in an issue before implementing them. Follow CODE_OF_CONDUCT.md.
