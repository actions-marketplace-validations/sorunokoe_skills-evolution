<div align="center">

# skills-evolution

<img src="skills-evolution.png" alt="skills-evolution logo: a growing plant from seed to flourishing bush" width="400">

**Keep your AI skill files accurate, up to date, and evolving — automatically.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org)

[What it does](#what-it-does) · [Evolution badge](#evolution-badge) · [Quick start](#quick-start) · [Standalone skill repos](#setup-for-standalone-skill-repos) · [Showcase](#showcase)

</div>

---

## What it does

**skills-evolution** runs on a monthly schedule and keeps your AI skill files fresh:

- **Finds stale versions** — reads `package.json`, `go.mod`, `Cargo.lock`, etc. and spots version drift
- **Patches them** — calls an AI model once per skill, applies safe inline updates, opens a PR for your review
- **Audits structure** — validates frontmatter, checks for contradictions across skill files, flags skills that are too long or missing routing hints
- **Reviews skill PRs** — posts an AI-powered review on every PR that touches a skill file

No local setup needed. Everything runs in GitHub Actions.

---

## Evolution badge

Every time the workflow runs and opens a PR, it adds an **evolution badge** to the PR description. After merge, the badge is committed to the skill's `README.md` — so you can see how far it's come.

[![Skill evolved 7×](https://img.shields.io/badge/evolved-7%C3%97_thriving-yellow?style=flat-square&logo=dna&logoColor=white)](#)

### Stage progression

| Range | Emoji | Stage |
|-------|-------|-------|
| 1 | 🦠 | **newborn** |
| 2–5 | 🐛 | **evolving** |
| 6–15 | 🦎 | **thriving** |
| 16–30 | 🧠 | **sentient** |
| 31+ | 🤖 | **legendary** |

---

## Quick start

Add two workflow files to your repo — that's it.

### 1. PR skill review

Reviews any PR that touches a skill file.

```yaml
# .github/workflows/skills-pr-check.yml
name: Skills PR Review
on:
  pull_request:
    paths: [".github/skills/**", ".claude/skills/**"]
permissions:
  contents: read
  pull-requests: write
jobs:
  review:
    uses: sorunokoe/skills-evolution/.github/workflows/skills_pr_check.yml@latest
    with:
      tech_stack: ""   # optional: e.g. "Swift, KMP, SwiftUI"
    secrets:
      copilot_token: ${{ secrets.COPILOT_TOKEN }}
```

### 2. Monthly health check

Detects version drift and opens a PR with updates once a month.

```yaml
# .github/workflows/skills-health.yml
name: Monthly Skill Update
on:
  schedule:
    - cron: "0 3 1 * *"   # 1st of each month, 3am UTC
  workflow_dispatch:
permissions:
  contents: write
  pull-requests: write
  models: read
jobs:
  health:
    uses: sorunokoe/skills-evolution/.github/workflows/skills-health.yml@latest
    with:
      enable_ai_skill_update: true
    secrets:
      token: ${{ secrets.GITHUB_TOKEN }}
```

Commit both files and you're done. Trigger manually anytime with `workflow_dispatch`.

---

## Setup for standalone skill repos

Publishing a standalone skill repo (like [swift-kmp-skill](https://github.com/sorunokoe/swift-kmp-skill))? Use the `--oss` mode where `SKILL.md` lives at the repo root.

> **One-time setting:** go to **Settings → Actions → General → Workflow permissions** and check  
> **"Allow GitHub Actions to create and approve pull requests"**

```yaml
# .github/workflows/skill-pr-review.yml
name: Skill Review
on:
  pull_request:
    paths: ["SKILL.md", "references/**", "examples/**"]
permissions:
  contents: read
  pull-requests: write
jobs:
  review:
    uses: sorunokoe/skills-evolution/.github/workflows/oss_skill_pr_check.yml@latest
    secrets:
      copilot_token: ${{ secrets.COPILOT_TOKEN }}
```

```yaml
# .github/workflows/skill-health.yml
name: Monthly Skill Health Check
on:
  schedule:
    - cron: "0 3 1 * *"
  workflow_dispatch:
permissions:
  contents: write
  pull-requests: write
  models: read
jobs:
  health:
    uses: sorunokoe/skills-evolution/.github/workflows/oss-skill-health.yml@latest
    with:
      enable_ai_skill_update: true
    secrets:
      token: ${{ secrets.GITHUB_TOKEN }}
```

---

## Reference

### CLI

```bash
# Audit skill structure
skills-evolution-health audit --repo-root . --output-dir outputs [--oss]

# Collect PR feedback signals
skills-evolution-health collect-feedback \
  --repo owner/repo --token "$GH_TOKEN" --output outputs/raw.json

# Analyze feedback into proposals
skills-evolution-health feedback \
  --repo-root . --raw outputs/raw.json --output-dir outputs

# Combine into a PR-ready summary with evolution badge
skills-evolution-health combine --output-dir outputs --evolution-num 7

# Update the README badge after merge
skills-evolution-health update-badge --repo-root . --evolution-num 7 --repo-url https://github.com/owner/repo/pulls?q=is%3Amerged

# Read current evolution number from README
skills-evolution-health read-evolution-num --repo-root .
```

### Python package

```bash
pip install skills-evolution
PYTHONPATH=src python3 -m skills_evolution.health --help
```

---

## Showcase

| Skill | What it covers | Repo |
|-------|---------------|------|
| **swift-kmp** | KMP ↔ Swift bridge patterns, `SkieSwiftFlow` → `AsyncStream`, type mapping | [sorunokoe/swift-kmp-skill](https://github.com/sorunokoe/swift-kmp-skill) |
| **swiftui-compose** | Compose Multiplatform ↔ SwiftUI interop, `UIViewControllerRepresentable`, coordinator | [sorunokoe/swiftui-compose-skill](https://github.com/sorunokoe/swiftui-compose-skill) |

---

## Contributing

Open an issue or PR. Tests: `python3 -m pytest tests/`.

## License

[MIT](LICENSE)
