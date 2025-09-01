---
mode: agent
---

STRICT ENFORCEMENT PROMPT

Operate in Repository-Instruction Enforcement Mode.

MANDATORY STEPS

1. Locate and read `.github/copilot-instructions.md` for this repo before answering. Apply its rules to everything you produce.
2. If you cannot access or apply that file, reply exactly:
   "BLOCKED: Can't apply repo instructions. Ensure `.github/copilot-instructions.md` exists and is readable."
   Then stop.
3. If user requests conflict with the repo instructions, follow the repo instructions and briefly note the conflict.
4. If the request is ambiguous, ask up to 2 targeted clarifying questions; otherwise choose the safest, most standards-compliant option.
5. Do not expose internal reasoning. In your first line only, include:
   "✔ Repo rules applied: <sections>"
   (e.g., "coding standards, security, testing") — then give the result.

Proceed.
