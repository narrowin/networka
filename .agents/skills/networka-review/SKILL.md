---
name: networka-review
description: Review Networka changes against a fixed Git reference using Matt Pocock's independent Standards and Spec reviews plus a separate correctness review of callers, contracts, and existing verification coverage.
---

# Review Networka changes

Use this for a local code review. Examples:

```text
$networka-review since main
$networka-review since HEAD~3 using .scratch/<feature>/spec.md
```

Read the repository [instructions](../../AGENTS.md), [glossary](../../../GLOSSARY.md),
and [issue tracker](../../../docs/agents/issue-tracker.md). Load the installed
`code-review` skill by Matt Pocock. Use its Standards and Spec process and
aggregation unchanged; this skill adds an independent Correctness review.
If `code-review` is unavailable, identify the missing dependency rather than
silently substituting a different workflow.

## Fix the scope

Resolve the user's comparison reference and `HEAD` to commit SHAs. Ask for the
reference when it is missing. Record the merge base, commit list, and changed
paths, including renames and deletions. Use the recorded SHAs for every reviewer:
`git diff <base-sha>...<head-sha>`. Stop on an invalid reference.

Inspect Git status. A committed review excludes staged, unstaged, and untracked
changes; disclose any exclusions. If the user requests those changes, capture
their diff and relevant file contents in a temporary directory and give every
reviewer that same captured scope in addition to the committed diff. Record
which files were captured. Keep the checkout intact.
Build the requested scope from the committed diff and any explicitly requested
working changes. Stop only when that combined scope is empty; a review since
`HEAD` can consist entirely of requested working changes.

Identify the originating requirements using Matt's skill and the local issue
tracker. Discover repository standards, matching ADRs, and applicable existing
checks. Requirements that cannot be located remain an explicit coverage
limitation, following the Spec skill's missing-requirements procedure.

## Independent reviews

Coordinate Matt's Standards and Spec reviewers and one additional Correctness
reviewer. Use fresh subagent contexts (`fork_turns="none"` when supported),
without the author's implementation narrative, suspected defects, or other
reviewers' conclusions. Supply each reviewer with the repository path, fixed
scope, applicable instructions, and the source documents its assignment needs.

- **Standards and Spec:** use Matt's respective briefs and reporting rules.
- **Correctness:** supply [the correctness brief](references/correctness.md).
  Include the requirements when available so intended behavior is distinguishable
  from accidental behavior. Require every changed path to be accounted for.

These three assignments can run concurrently. If independent agents are
unavailable, disclose that limitation and perform the reviews sequentially;
do not claim independent review.

Review is read-only. Existing local checks may run when they are within the
user's request and repository permissions. Source inspection is sufficient for
a source-only review; record what was and was not executed. New automated test
artifacts require the user's explicit request. Live access and publication
follow the repository's authorization rules.

## Present the result

Keep Matt's **Standards** and **Spec** results separate and retain his per-axis
summary. Add **Correctness** with its findings and coverage. Cross-reference
overlap rather than combining the axes into one ranking.

For correctness findings, give priority, file/line, trigger, code evidence,
impact, and a proportionate correction. Separate current defects from optional
improvements such as missing regression coverage. P0 is catastrophic impact;
P1 is a high-impact blocker; P2 is a correctness or reliability defect; P3 is a
minor defect; P4 is an optional actionable improvement. Zero findings is valid.

Include a compact coverage record: reviewed SHAs and working-tree capture if
any, changed paths investigated or skipped per axis, checks executed, and
unresolved uncertainty. A coverage claim comes from reviewer evidence; an
instruction to inspect every file is not evidence that it happened.

If the scope changed during review, label the reviewed version explicitly and
identify the newer changes. Review findings are advisory; this skill does not
fix, commit, or publish them. Use the existing `networka-verify` skill for a
separately requested verification of code or package changes.
