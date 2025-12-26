---
description: 'Create a detailed plan from the current session and craft a handoff prompt for a new agent session'
mode: agent
---

# Session Handoff Creator

Create a comprehensive plan and handoff prompt from the current session for continuation in a new agent session.

## Your Task

1. **Analyze the current session** - Review all context, decisions, code changes, and work completed
2. **Create a detailed plan** - Write to `llm-plans/<feature-name>-plan.md` with all implementation details
3. **Create a handoff prompt** - Write to `llm-plans/<feature-name>-handoff.md` with the session prompt

## Plan File Structure

Write the plan file with these sections:

```markdown
# <Feature Name> - Implementation Plan

## Context

Brief background on what was discussed/decided in the session.

## Files to Modify

| File | Action |
|------|--------|
| `path/to/file.py` | CREATE/MODIFY/DELETE - Brief description |

## Implementation Details

### Phase 1: <Phase Name>

#### Task 1.1: <Task Name>

**File**: `path/to/file.py`

**Current** (if modifying):
```python
# existing code
```

**Target**:
```python
# new/modified code
```

**Rationale**: Why this change is needed.

### Phase 2: <Phase Name>
... continue for all phases ...

## Test Cases

List specific test cases to add/verify.

## Verification Steps

Commands to run after implementation.

## Standards Checklist

- [ ] Follows CLAUDE.md
- [ ] Run ruff check --fix --unsafe-fixes .
- [ ] Run pre-commit run --all-files
- [ ] NO AI attribution in commits
- [ ] Conventional commits format

## Out of Scope

List items discussed but deferred for future work.
```

## Handoff Prompt Structure

Write the handoff file with a copy-paste ready prompt:

```markdown
# <Feature Name> - Session Handoff

## Prompt for New Session

Copy this to start a new Claude Code session:

\```
<Complete prompt with all context needed>
\```

## Which Agents to Use

- During implementation: <agent recommendations>
- For code review: <agent recommendations>
- If issues arise: <agent recommendations>

## Pre-Implementation Checklist

1. Read `llm-plans/<feature-name>-plan.md`
2. Read `CLAUDE.md`
3. Check relevant existing patterns in codebase

## Expected Output

What the implementation should produce (commands, output examples).
```

## Critical Requirements

1. **Preserve all context** - Include every decision, requirement, and constraint
2. **Include code examples** - Show exact before/after for modifications
3. **Specify file paths** - Use absolute paths within the repo
4. **List dependencies** - Note any related files or patterns to reference
5. **Be explicit** - A new agent with no prior context must be able to execute
6. **Include validation** - How to verify the implementation is correct
7. **NO AI attribution** - Handoff prompts must remind NO AI attribution in commits

## Output

After creating both files, output the handoff prompt in a code block so the user can copy it directly:

```markdown
<the complete handoff prompt>
```
