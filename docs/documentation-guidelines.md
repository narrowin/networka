# Documentation Guidelines

We design every page around one goal: help a new user succeed quickly. If a step slows users down, we simplify it or remove it. Defaults should “just work,” commands must be copy‑pasteable, and examples should use real‑world scenarios.

## Maxims

- Onboarding first: lead with the shortest happy path
- One screen to success: first run should fit without scrolling
- Copy‑paste fidelity: commands and snippets run as‑is
- Tell then show: explanation follows working example
- Progressive disclosure: link to depth, keep pages focused
- Error‑first empathy: anticipate common failures and inline fixes

## Page structure

1. Outcome statement: what you’ll achieve in minutes
2. Prerequisites (brief, verified)
3. Minimal working example (MWE)
4. Validate results (what success looks like)
5. Next steps (2–3 clear paths)
6. Troubleshooting (top 3 issues)

## Style

- Use task‑based headings (Install, Run, Validate)
- Prefer concrete examples over abstract concepts
- Show OS‑specific notes only when needed
- Avoid decorative prose and jokes in docs
- Keep code blocks small and purposeful

## Verification

- Every command is tested via VS Code Test feature
- Outputs are captured and trimmed to essentials
- Links are checked by CI

## Templates

- Getting started pages include a 60‑second quickstart
- Feature pages start with a one‑liner MWE
- Reference pages link back to guides with examples

## Review checklist

- Does the first code block produce visible success?
- Can a user follow the page without prior context?
- Are errors anticipated with immediate remedies?
- Are copy‑paste commands safe and minimal?
- Is there a clear, opinionated next step?
