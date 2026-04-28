---
on:
  pull_request:
    types: [opened, edited, reopened, synchronize]
    paths:
      - ".github/skills/**"
      - ".claude/skills/**"

skip-bots: true
description: "Reviews changed skill guidance files in pull requests"
source: "sorunokoe/skills-evolution/workflows/skills-pr-check.md@main"
labels: ["skills"]

tools:
  github:
    toolsets: [pull-requests]
  bash: ["git", "cat", "head", "find"]

safe-outputs:
  add-comment:
---

# Skill File Reviewer

Find all `SKILL.md` files changed in this pull request:

```bash
git diff --name-only origin/${{ github.event.pull_request.base.ref }}...HEAD -- '.github/skills/*/SKILL.md' '.claude/skills/*/SKILL.md'
```

Read each changed file and review it for:

1. **Accuracy** — does the guidance reflect current best practices for the libraries or patterns mentioned?
2. **Clarity** — are the instructions actionable and unambiguous?
3. **Scope** — is the "When to use" section precise (not too broad, not too narrow)?
4. **Anti-patterns** — are the most common mistakes clearly listed?

Add a concise comment to this pull request with your findings.
If all files look good, say so briefly. Only flag genuine issues.
