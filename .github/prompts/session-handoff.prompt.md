---
description: 'Write a Networka plan and handoff prompt for a new session'
mode: agent
---

Read [`.agents/AGENTS.md`](../../.agents/AGENTS.md). Create
`llm-plans/<feature-name>-plan.md` and
`llm-plans/<feature-name>-handoff.md` from the current session.

In the plan, record the desired outcome, scope, decisions, changed and pending
paths, and any local edits that need preservation. List verification commands
and actual observations separately from checks still needed. For a meaningful
pending decision, carry over the known alternatives and the evidence for them.
Preserve approval boundaries, including any named lab target and its authorized
operations.

In the handoff prompt, point the next agent to `.agents/AGENTS.md` and the plan. Give
the workspace and starting revision, summarize the current state, and specify
the next concrete action and completion condition. Use repository-relative paths
for files in the project. Return links to both files and the handoff prompt in a
code block for copying.
