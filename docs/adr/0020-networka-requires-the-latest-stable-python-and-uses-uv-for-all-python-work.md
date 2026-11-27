# Networka requires the latest stable Python and uses uv for all Python work

Networka requires Python 3.15 or later, and development pins Python 3.15.2.
Every project command, check, test and Python subprocess runs through `uv`, with one locked workflow for development and CI.

## Why

On 2026-11-25 the operator asked during the repository cleanup: "why don't we go with the latest stable Python?"
Networka has a small user base, so one current interpreter and one tool keep development and verification simple.
Until then the README, the contributing guide and a CI matrix of five versions promised Python 3.11 and later.

## Considered options

- **Keep Python 3.11 and later.** Rejected: it keeps five interpreters in CI for users who have not asked for them.

## Consequences

Users on an older Python cannot install Networka.
Lab repositories run Networka through `uv` too.
