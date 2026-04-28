---
on:
  schedule: monthly

skip-bots: true
description: "Monthly review and update of AI skill files against current library versions"
source: "sorunokoe/skills-evolution/workflows/skills-monthly-update.md@main"
labels: ["skills", "maintenance"]

tools:
  github:
    toolsets: [pull-requests, files]
  bash: ["find", "cat", "head", "gh", "git", "sed", "python3"]

safe-outputs:
  create-pull-request:
---

# Monthly Skills Update

Review and update all AI skill guidance files in `.github/skills/` and `.claude/skills/`.

## 1 — Discover dependencies

Find package manager files that declare GitHub-hosted libraries:

```bash
find . \( -name "Package.resolved" -o -name "go.mod" -o -name "Cargo.lock" -o -name "pubspec.yaml" \) \
  -not -path "*/.build/*" -not -path "*/vendor/*" -not -path "*/node_modules/*"
```

Also check `package.json` files for `github:owner/repo` references. Read each file and extract
the GitHub repository slug and pinned version for every dependency.

## 2 — Check latest releases

For each GitHub-hosted dependency found, look up the latest published release:

```bash
gh api repos/{owner}/{repo}/releases/latest --jq '.tag_name'
```

## 3 — Review and update skill files

Find all skill files:

```bash
find .github/skills .claude/skills -name "SKILL.md" 2>/dev/null
```

For each skill file, check whether it references outdated library versions or deprecated APIs
based on the version data above. Apply conservative inline edits only where you can confirm
the change from actual release data — do not guess.

## 4 — Create pull request

If any files were changed, create a pull request:

- **Title**: `chore(skills): monthly skill update`
- **Body**: a concise summary of what was updated and which dependency version data drove the change

If nothing needed updating, do nothing.
